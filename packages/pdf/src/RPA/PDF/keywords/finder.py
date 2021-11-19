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
    neighbours: List[str]


class FinderKeywords(LibraryContext):
    """Keywords for locating elements."""

    PIXEL_TOLERANCE = 5

    def __init__(self, ctx):
        super().__init__(ctx)

        # Text locator might lead to multiple valid found anchors.
        self._anchors = []
        # The others usually have just one. (if multiple are found, set to it the
        #   first one)
        self.anchor_element = None

    def _get_candidate_search_function(
        self, direction: str, regexp: Optional[re.Pattern], strict: bool
    ) -> Callable[[TextBox], bool]:
        if direction in ["left", "right"]:
            return functools.partial(
                self._is_match_on_horizontal, direction=direction, regexp=regexp
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
        pagenum: int = 1,
        direction: str = "right",
        closest_neighbours: int = 1,
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
        self.logger.info(
            "Searching for the closest %d neighbour(s) to the %s of %r on page %d using regular expression: %s",
            closest_neighbours,
            direction,
            locator,
            pagenum,
            regexp,
        )
        self.set_anchor_to_element(locator, trim=trim)
        if not self.anchor_element:
            self.logger.warning("No anchor(s) set for locator: %s", locator)
            return []

        page = self.ctx.active_pdf_document.get_page(int(pagenum))
        regexp_compiled = re.compile(regexp) if regexp else None
        search_for_candidate = self._get_candidate_search_function(
            direction, regexp_compiled, strict
        )

        candidates_dict = {}
        for candidate in page.get_textboxes().values():
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
            self._sort_candidates_by_anchor(
                candidates, anchor=anchor, direction=direction
            )
            if closest_neighbours:
                # Keep the first N closest neighbours from the entire set of candidates.
                candidates[closest_neighbours:] = []
            match = Match(
                anchor=anchor.text,
                neighbours=[candidate.text for candidate in candidates],
            )
            matches.append(match)

        return matches

    @keyword
    def set_anchor_to_element(self, locator: str, trim: bool = True) -> bool:
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
        self.logger.info("Set anchor to element: ('locator=%s')", locator)
        self.ctx.convert(trim=trim)
        self._anchors.clear()
        self.anchor_element = None

        pure_locator = locator
        criteria = "text"
        parts = locator.split(":", 1)
        if len(parts) == 2 and parts[0] in ("coords", "text"):
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
            matches = self._find_matching_textboxes(criteria, pure_locator)
            self._anchors.extend(matches)

        if self._anchors:
            self.anchor_element = self._anchors[0]
            return True

        return False

    def _find_matching_textboxes(self, criteria: str, locator: str) -> List[str]:
        self.logger.info(
            "find_matching_textbox: ('criteria=%s', 'locator=%s')", criteria, locator
        )

        lower_locator = locator.lower()
        matches = []
        # FIXME(cmin764): Search in the current page only.
        for page in self.active_pdf_document.get_pages().values():
            content = page.get_textboxes()
            for item in content.values():
                if item.text.lower() == lower_locator:
                    matches.append(item)

        if matches:
            self.logger.debug("Found %d matches for locator %r:", len(matches), locator)
            for match in matches:
                self._log_element(match)
        else:
            self.logger.info("Did not find any matches")

        return matches

    @classmethod
    def _is_within_tolerance(cls, base: int, target: int) -> bool:
        max_target = target + cls.PIXEL_TOLERANCE
        min_target = max(target - cls.PIXEL_TOLERANCE, 0)
        return min_target <= base <= max_target

    def _is_match_on_horizontal(
        self,
        item: TextBox,
        *,
        direction: str,
        regexp: Optional[re.Pattern],
        anchor: TextBox,
    ) -> bool:
        if not item:
            return False

        (left, _, right, top) = anchor.bbox
        direction_ok = False
        if self._is_within_tolerance(item.top, top):
            if direction == "right" and item.left >= right:
                direction_ok = True
            elif direction == "left" and item.right <= left:
                direction_ok = True
        if not direction_ok:
            return False

        regex_matched = regexp and regexp.match(item.text)
        no_regex = regexp is None
        return any([regex_matched, no_regex])

    def _is_match_on_vertical(
        self,
        item: TextBox,
        *,
        direction: str,
        regexp: Optional[re.Pattern],
        strict: bool,
        anchor: TextBox,
    ) -> bool:
        (left, bottom, right, top) = anchor.bbox
        direction_down = direction in ["bottom", "down"]
        direction_up = direction in ["top", "up"]

        if (direction_down and item.top <= bottom) or (
            direction_up and item.bottom >= top
        ):
            non_strict_match = not strict and (item.right <= right or item.left >= left)
            strict_match = strict and (item.right == right or item.left == left)
            if not any([non_strict_match, strict_match]):
                return False  # item not in range

            if regexp and regexp.match(item.text):
                self.logger.debug(
                    "EXACT MATCH %s %r %s", item.boxid, item.text, item.bbox
                )
                return True
            if regexp is None:
                self.logger.debug(
                    "POTENTIAL MATCH %s %r %s", item.boxid, item.text, item.bbox
                )
                return True

        return False

    def _is_match_in_box(self, item: TextBox, *, anchor: TextBox) -> bool:
        (left, bottom, right, top) = anchor.bbox
        return (
            left <= item.left
            and right >= item.right
            and bottom <= item.bottom
            and top >= item.top
        )

    @staticmethod
    def _sort_candidates_by_anchor(
        candidates: List[TextBox], *, anchor: TextBox, direction: str
    ) -> None:
        (_, bottom, right, top) = anchor.bbox
        direction_down = direction in ["bottom", "down"]

        def get_distance(candidate):
            if direction_down:
                vertical_distance = bottom - candidate.top
            else:
                vertical_distance = top - candidate.bottom
            abs_dist_from_right = abs(right - candidate.right)
            abs_dist_from_left = abs(right - candidate.left)
            horizontal_distance = min(abs_dist_from_left, abs_dist_from_right)
            calc_distance = math.sqrt(
                math.pow(horizontal_distance, 2) + math.pow(vertical_distance, 2)
            )
            return calc_distance

        candidates.sort(key=get_distance)
