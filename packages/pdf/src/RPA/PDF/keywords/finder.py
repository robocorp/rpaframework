import functools
import math
import re
from dataclasses import dataclass

try:
    # Python >=3.7
    from re import Pattern
except ImportError:
    # Python =3.6
    from re import _pattern_type as Pattern

from typing import Callable, Dict, List, Optional, Union

from RPA.PDF.keywords import LibraryContext, keyword
from RPA.PDF.keywords.model import BaseElement, TextBox


class TargetObject(BaseElement):
    """Container for Target text boxes with coordinates."""

    # Class level constants.
    boxid: int = -1
    text: str = ""


Element = Union[TextBox, TargetObject]


@dataclass
class Match:
    """Match object returned by the `Find Text` keyword.

    It contains the anchor point and its relative found elements in text format.
    """

    anchor: str
    direction: str
    neighbours: List[str]


class FinderKeywords(LibraryContext):
    """Keywords for locating elements."""

    RE_FLAGS = re.MULTILINE | re.DOTALL  # default regexp flags

    def __init__(self, ctx):
        super().__init__(ctx)

        # Text locator might lead to multiple valid found anchors.
        self._anchors: List[Element] = []
        # The others usually have just one. (if multiple are found, set to it the
        #   first one)
        self.anchor_element = None

    def _get_candidate_search_function(
        self, direction: str, regexp: Optional[Pattern], strict: bool
    ) -> Callable[[TextBox], bool]:
        if direction in ["left", "right"]:
            return functools.partial(
                self._is_match_on_horizontal,
                direction=direction,
                regexp=regexp,
                strict=strict,
            )
        if direction in ["top", "bottom", "up", "down"]:
            return functools.partial(
                self._is_match_on_vertical,
                direction=direction,
                regexp=regexp,
                strict=strict,
            )
        if direction == "box":
            return self._is_match_in_box

        raise ValueError(f"Not recognized direction search {direction!r}")

    def _log_element(self, elem: Element, prefix: str = ""):
        template = f"{prefix} box %d | bbox %s | text %r"
        self.logger.debug(template, elem.boxid, elem.bbox, elem.text)

    @classmethod
    def _re_flags(cls, ignore_case: bool) -> int:
        flags = cls.RE_FLAGS
        if ignore_case:
            flags |= re.IGNORECASE
        return flags

    @keyword
    def find_text(
        self,
        locator: str,
        pagenum: Union[int, str] = 1,
        direction: str = "right",
        closest_neighbours: Optional[Union[int, str]] = 1,
        strict: bool = False,
        regexp: Optional[str] = None,
        trim: bool = True,
        ignore_case: bool = False,
    ) -> List[Match]:
        """Find the closest text elements near the set anchor(s) through `locator`.

        The PDF will be parsed automatically before elements can be searched.

        :param locator: Element to set anchor to. This can be prefixed with either
            "text:", "subtext:", "regex:" or "coords:" to find the anchor by text or
            coordinates. The "text" strategy is assumed if no such prefix is specified.
            (text search is case-sensitive; use `ignore_case` param for controlling it)
        :param pagenum: Page number where search is performed on, defaults to 1 (first
            page).
        :param direction: In which direction to search for text elements. This can be
            any of 'top'/'up', 'bottom'/'down', 'left' or 'right'. (defaults to
            'right')
        :param closest_neighbours: How many neighbours to return at most, sorted by the
            distance from the current anchor.
        :param strict: If element's margins should be used for matching those which are
            aligned to the anchor. (turned off by default)
        :param regexp: Expected format of the searched text value. By default all the
            candidates in range are considered valid neighbours.
        :param trim: Automatically trim leading/trailing whitespace from the text
            elements. (switched on by default)
        :param ignore_case: Do a case-insensitive search when set to `True`. (affects
            the passed `locator` and `regexp` filtering)
        :returns: A list of `Match` objects where every match has the following
            attributes: `.anchor` - the matched text with the locator; `.neighbours` -
            a list of adjacent texts found on the specified direction

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            PDF Invoice Parsing
                Open Pdf    invoice.pdf
                ${matches} =  Find Text    Invoice Number
                Log List      ${matches}

        .. code-block::

            List has one item:
            Match(anchor='Invoice Number', direction='right', neighbours=['INV-3337'])

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def pdf_invoice_parsing():
                pdf.open_pdf("invoice.pdf")
                matches = pdf.find_text("Invoice Number")
                for match in matches:
                    print(match)

            pdf_invoice_parsing()

        .. code-block::

            Match(anchor='Invoice Number', direction='right', neighbours=['INV-3337'])
        """
        pagenum = int(pagenum)
        if closest_neighbours is not None:
            closest_neighbours = int(closest_neighbours)
        self.logger.info(
            "Searching for %s neighbour(s) to the %s of %r on page %d using regular "
            "expression: %s (case %s)",
            f"closest {closest_neighbours}"
            if closest_neighbours is not None
            else "all",
            direction,
            locator,
            pagenum,
            regexp,
            "insensitive" if ignore_case else "sensitive",
        )
        self.set_anchor_to_element(
            locator, trim=trim, pagenum=pagenum, ignore_case=ignore_case
        )
        if not self.anchor_element:
            self.logger.warning("No anchor(s) set for locator: %s", locator)
            return []

        regexp_compiled = None
        if regexp:
            regexp_compiled = re.compile(regexp, flags=self._re_flags(ignore_case))
        search_for_candidate = self._get_candidate_search_function(
            direction, regexp_compiled, strict
        )

        candidates_dict: Dict[int, List[Element]] = {}
        anchors_map: Dict[int, Element] = {}
        for anchor in self._anchors:
            candidates_dict[anchor.boxid] = []
            anchors_map[anchor.boxid] = anchor

        for candidate in self._get_textboxes_on_page(pagenum):
            self._log_element(candidate, prefix="Current candidate:")
            for anchor in self._anchors:
                self._log_element(anchor, prefix="Current anchor:")
                # Skip anchor element itself from matching and check if the candidate
                # matches the search criteria.
                if candidate.boxid != anchor.boxid and search_for_candidate(
                    candidate, anchor=anchor
                ):
                    candidates_dict[anchor.boxid].append(candidate)

        matches = []
        for anchor_id, candidates in candidates_dict.items():
            anchor = anchors_map[anchor_id]
            self._sort_candidates_by_anchor(candidates, anchor=anchor)
            if closest_neighbours is not None:
                # Keep the first N closest neighbours from the entire set of candidates.
                candidates[closest_neighbours:] = []
            match = Match(
                anchor=anchor.text,
                direction=direction,
                neighbours=[candidate.text for candidate in candidates],
            )
            matches.append(match)

        return matches

    @keyword
    def set_anchor_to_element(
        self,
        locator: str,
        trim: bool = True,
        pagenum: Union[int, str] = 1,
        ignore_case: bool = False,
    ) -> bool:
        """Sets main anchor point in the document for further searches.

        This is used internally in the library and can work with multiple anchors at
        the same time if such are found.

        :param locator: Element to set anchor to. This can be prefixed with either
            "text:", "subtext:", "regex:" or "coords:" to find the anchor by text or
            coordinates. The "text" strategy is assumed if no such prefix is specified.
            (text search is case-sensitive; use `ignore_case` param for controlling it)
        :param trim: Automatically trim leading/trailing whitespace from the text
            elements. (switched on by default)
        :param pagenum: Page number where search is performed on, defaults to 1 (first
            page).
        :param ignore_case: Do a case-insensitive search when set to `True`.
        :returns: True if at least one anchor was found.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            Example Keyword
                 ${success} =  Set Anchor To Element    Invoice Number

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                success = pdf.set_anchor_to_element("Invoice Number")
        """
        pagenum = int(pagenum)
        self.logger.info(
            "Trying to set anchor on page %d using locator: %r (case %s)",
            pagenum,
            locator,
            "insensitive" if ignore_case else "sensitive",
        )
        self.ctx.convert(trim=trim, pagenum=pagenum)
        self._anchors.clear()
        self.anchor_element = None

        pure_locator = locator
        criteria = "text"
        parts = locator.split(":", 1)
        if len(parts) == 2 and parts[0] in ("coords", "text", "regex", "subtext"):
            criteria = parts[0]
            pure_locator = parts[1]

        if criteria == "coords":
            coords = pure_locator.split(",")
            if len(coords) == 2:
                left, bottom = coords
                top = bottom
                right = left
            elif len(coords) == 4:
                left, bottom, right, top = coords
            else:
                raise ValueError("Give 2 coordinates for point, or 4 for area")

            bbox = (
                int(left),
                int(bottom),
                int(right),
                int(top),
            )
            anchor = TargetObject(bbox=bbox)
            self._anchors.append(anchor)
        else:  # text-based search
            if criteria == "regex":
                pure_locator = re.compile(
                    pure_locator, flags=self._re_flags(ignore_case)
                )
            anchors = self._find_matching_textboxes(
                pure_locator,
                pagenum=pagenum,
                is_subtext=criteria == "subtext",
                ignore_case=ignore_case,
            )
            self._anchors.extend(anchors)

        if self._anchors:
            self.anchor_element = self._anchors[0]
            return True

        return False

    def _get_textboxes_on_page(self, pagenum: int) -> List[TextBox]:
        page = self.active_pdf_document.get_page(pagenum)
        return list(page.textboxes.values())

    def _find_matching_textboxes(
        self,
        locator: Union[str, Pattern],
        *,
        pagenum: int,
        is_subtext: bool = False,
        ignore_case: bool = False,
    ) -> List[TextBox]:
        self.logger.info("Searching for matching text boxes with: %r", locator)

        if isinstance(locator, str):
            get_text = lambda string: (  # noqa: E731
                string.lower() if ignore_case else string
            )
            if is_subtext:
                matches_anchor = lambda _anchor: (  # noqa: E731
                    get_text(locator) in get_text(_anchor.text)
                )
            else:
                matches_anchor = lambda _anchor: (  # noqa: E731
                    get_text(_anchor.text) == get_text(locator)
                )
        else:
            matches_anchor = lambda _anchor: locator.match(_anchor.text)  # noqa: E731

        anchors = []
        for anchor in self._get_textboxes_on_page(pagenum):
            if matches_anchor(anchor):
                anchors.append(anchor)
        if anchors:
            self.logger.info("Found %d matches with locator %r", len(anchors), locator)
            for anchor in anchors:
                self._log_element(anchor)
        else:
            self.logger.warning("Did not find any matches with locator %r", locator)

        return anchors

    def _check_text_match(self, candidate: TextBox, regexp: Optional[Pattern]) -> bool:
        if regexp and regexp.match(candidate.text):
            self._log_element(candidate, prefix="Exact match:")
            return True
        if regexp is None:
            self._log_element(candidate, prefix="Potential match:")
            return True

        return False

    def _is_match_on_horizontal(
        self,
        candidate: TextBox,
        *,
        direction: str,
        regexp: Optional[Pattern],
        strict: bool,
        anchor: TextBox,
    ) -> bool:
        (left, bottom, right, top) = anchor.bbox
        direction_left = direction == "left"
        direction_right = direction == "right"

        if not any(
            [
                direction_left and candidate.right <= left,
                direction_right and candidate.left >= right,
            ]
        ):
            return False  # not in the seeked direction

        non_strict_match = not strict and (
            bottom <= candidate.bottom <= top
            or bottom <= candidate.top <= top
            or candidate.bottom <= bottom <= candidate.top
            or candidate.bottom <= top <= candidate.top
        )
        strict_match = strict and (candidate.bottom == bottom or candidate.top == top)
        if not any([non_strict_match, strict_match]):
            return False  # candidate not in boundaries

        return self._check_text_match(candidate, regexp)

    def _is_match_on_vertical(
        self,
        candidate: TextBox,
        *,
        direction: str,
        regexp: Optional[Pattern],
        strict: bool,
        anchor: TextBox,
    ) -> bool:
        (left, bottom, right, top) = anchor.bbox
        direction_down = direction in ["bottom", "down"]
        direction_up = direction in ["top", "up"]

        if not any(
            [
                direction_down and candidate.top <= bottom,
                direction_up and candidate.bottom >= top,
            ]
        ):
            return False  # not in the seeked direction

        non_strict_match = not strict and (
            left <= candidate.left <= right
            or left <= candidate.right <= right
            or candidate.left <= left <= candidate.right
            or candidate.left <= right <= candidate.right
        )
        strict_match = strict and (candidate.left == left or candidate.right == right)
        if not any([non_strict_match, strict_match]):
            return False  # candidate not in boundaries

        return self._check_text_match(candidate, regexp)

    def _is_match_in_box(self, candidate: TextBox, *, anchor: TextBox) -> bool:
        (left, bottom, right, top) = anchor.bbox
        return (
            left <= candidate.left
            and right >= candidate.right
            and bottom <= candidate.bottom
            and top >= candidate.top
        )

    @staticmethod
    def _sort_candidates_by_anchor(
        candidates: List[TextBox], *, anchor: TextBox
    ) -> None:
        get_center = lambda item: (  # noqa: E731
            (item.left + item.right) / 2,
            (item.bottom + item.top) / 2,
        )
        anchor_center = get_center(anchor)

        def get_distance(candidate):
            candidate_center = get_center(candidate)
            anchor_to_candidate_distance = math.sqrt(
                math.pow((candidate_center[0] - anchor_center[0]), 2)
                + math.pow((candidate_center[1] - anchor_center[1]), 2)
            )
            return anchor_to_candidate_distance

        candidates.sort(key=get_distance)
