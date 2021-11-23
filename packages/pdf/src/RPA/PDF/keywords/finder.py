import functools
import math
import re
from dataclasses import dataclass
from typing import (
    Callable,
    List,
    Optional,
    Union,
)

from RPA.PDF.keywords import (
    LibraryContext,
    keyword,
)
from RPA.PDF.keywords.model import TextBox


@dataclass
class TargetObject:
    """Container for Target text boxes with coordinates."""

    boxid: int
    bbox: tuple
    text: str


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

    def __init__(self, ctx):
        super().__init__(ctx)

        # Text locator might lead to multiple valid found anchors.
        self._anchors: List[Union[TargetObject, TextBox]] = []
        # The others usually have just one. (if multiple are found, set to it the
        #   first one)
        self.anchor_element = None

    def _get_candidate_search_function(
        self, direction: str, regexp: Optional[re.Pattern], strict: bool
    ) -> Callable[[TextBox], bool]:
        if direction in ["left", "right"]:
            return functools.partial(
                self._is_match_on_horizontal, direction=direction, regexp=regexp, strict=strict
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

    def _log_element(self, elem: Union[TextBox, TargetObject], prefix: str = ""):
        template = f"{prefix} box %d | bbox %s | text %r"
        self.logger.debug(template, elem.boxid, elem.bbox, elem.text)

    @keyword
    def find_text(
        self,
        locator: str,
        pagenum: Union[int, str] = 1,
        direction: str = "right",
        closest_neighbours: Optional[Union[int, str]] = 1,
        strict: bool = False,
        regexp: str = None,
        trim: bool = True,
    ) -> List[Match]:
        """Get the closest text as string value to the anchored element.

        PDF will be parsed automatically before elements can be searched.

        :param locator: element to set anchor to. This can be prefixed with either
            `text:` or `coords:` to find the anchor by text or coordinates.
            Default is `text`.
        :param pagenum: page number where search if performed on, default 1 (first).
        :param direction: in which direction to search for text,
            directions  'top'/'up', 'bottom'/'down', 'left' or 'right',
            defaults to 'right'.
        :param strict: if element margins should be used for matching points,
            used when direction is 'top' or 'bottom', default `False`.
        :param regexp: expected format of value to match, defaults to None.
        :param trim: set to `False` to match on raw texts, default `True`
            means whitespace is trimmed from the text
        :return: all possible values, only the closest value, or an empty list.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                ${value} =  Find Text    text:Invoice Number

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                value = pdf.find_text("text:Invoice Number")
        """
        pagenum = int(pagenum)
        if closest_neighbours is not None:
            closest_neighbours = int(closest_neighbours)
        self.logger.info(
            "Searching for %s neighbour(s) to the %s of %r on page %d using regular expression: %s",
            f"closest {closest_neighbours}"
            if closest_neighbours is not None
            else "all",
            direction,
            locator,
            pagenum,
            regexp,
        )
        self.set_anchor_to_element(locator, trim=trim, pagenum=pagenum)
        if not self.anchor_element:
            self.logger.warning("No anchor(s) set for locator: %s", locator)
            return []

        regexp_compiled = re.compile(regexp) if regexp else None
        search_for_candidate = self._get_candidate_search_function(
            direction, regexp_compiled, strict
        )

        candidates_dict = {}
        for candidate in self._get_textboxes_on_page(pagenum):
            self._log_element(candidate, prefix="Current candidate:")
            for anchor in self._anchors:
                self._log_element(anchor, prefix="Current anchor:")
                # Skip anchor element itself from matching and check if the candidate
                # matches the search criteria.
                if candidate.boxid != anchor.boxid and search_for_candidate(
                    candidate, anchor=anchor
                ):
                    candidates_dict.setdefault(anchor, []).append(candidate)

        matches = []
        for anchor, candidates in candidates_dict.items():
            self._sort_candidates_by_anchor(candidates, anchor=anchor)
            if closest_neighbours:
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
        self, locator: str, trim: bool = True, pagenum: Union[int, str] = 1
    ) -> bool:
        """Sets anchor point in the document for further searches.

        This is used internally in the library.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                 ${success}=  Set Anchor To Element    text:Invoice Number

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                success = pdf.set_anchor_to_element("text:Invoice Number")

        :param locator: element to search for
        :param trim: set to `False` to match on raw texts, default `True`
            means whitespace is trimmed from the text
        :return: True if element was found.
        """
        self.logger.info("Trying to set anchor using locator: %r", locator)
        self.ctx.convert(trim=trim)
        self._anchors.clear()
        self.anchor_element = None

        pure_locator = locator
        criteria = "text"
        parts = locator.split(":", 1)
        if len(parts) == 2 and parts[0] in ("coords", "text", "regex"):
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
            anchor = TargetObject(boxid=-1, bbox=bbox, text="")
            self._anchors.append(anchor)
        else:
            if criteria == "regex":
                pure_locator = re.compile(pure_locator)
            anchors = self._find_matching_textboxes(pure_locator, pagenum=int(pagenum))
            self._anchors.extend(anchors)

        if self._anchors:
            self.anchor_element = self._anchors[0]
            return True

        return False

    def _get_textboxes_on_page(self, pagenum: int) -> List[TextBox]:
        page = self.active_pdf_document.get_page(pagenum)
        return list(page.textboxes.values())

    def _find_matching_textboxes(
        self, locator: Union[str, re.Pattern], *, pagenum: int
    ) -> List[TextBox]:
        self.logger.info("Searching for matching text boxes with: %r", locator)

        if isinstance(locator, str):
            lower_locator = locator.lower()
            matches_anchor = lambda _anchor: _anchor.text.lower() == lower_locator
        else:
            matches_anchor = lambda _anchor: locator.match(_anchor.text)
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

    def _check_text_match(self, candidate: TextBox, regexp: Optional[re.Pattern]) -> bool:
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
        regexp: Optional[re.Pattern],
        strict: bool,
        anchor: TextBox,
    ) -> bool:
        (left, bottom, right, top) = anchor.bbox
        direction_left = direction == "left"
        direction_right = direction == "right"

        if not any([
            direction_left and candidate.right <= left,
            direction_right and candidate.left >= right
        ]):
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
        regexp: Optional[re.Pattern],
        strict: bool,
        anchor: TextBox,
    ) -> bool:
        (left, bottom, right, top) = anchor.bbox
        direction_down = direction in ["bottom", "down"]
        direction_up = direction in ["top", "up"]

        if not any([
            direction_down and candidate.top <= bottom,
            direction_up and candidate.bottom >= top
        ]):
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
        get_center = lambda item: (
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
