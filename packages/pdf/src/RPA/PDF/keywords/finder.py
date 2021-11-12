import functools
import math
import re
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


class TargetObject:
    """Container for Target text box"""

    boxid: int
    bbox: tuple
    text: str


class FinderKeywords(LibraryContext):
    """Keywords for locating elements."""

    PIXEL_TOLERANCE = 5

    def __init__(self, ctx):
        super().__init__(ctx)
        self.anchor_element = None

    def _get_candidate_search_function(self, direction: str, regexp: str, strict: bool) -> Callable[[TextBox], bool]:
        if direction in ["left", "right"]:
            return functools.partial(self._is_match_on_horizontal, direction=direction, regexp=regexp)
        if direction in ["top", "bottom", "up", "down"]:
            return functools.partial(self._is_match_on_vertical, direction=direction, regexp=regexp, strict=strict)
        if direction == "box":
            return self._is_match_in_box

        raise ValueError(f"Not recognized direction search {direction!r}")

    @keyword
    def find_text(
        self,
        locator: str,
        pagenum: int = 1,
        direction: str = "right",
        strict: bool = False,
        regexp: str = None,
        only_closest: bool = True,
        trim: bool = True,
    ) -> Union[List[str], str]:
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
        :param only_closest: return all possible values or only the closest.
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
        self.logger.debug(
            "Get Value From Anchor: ('locator=%s', 'direction=%s', 'regexp=%s')",
            locator,
            direction,
            regexp,
        )
        self.set_anchor_to_element(locator, trim=trim)
        if not self.anchor_element:
            self.logger.info("No anchor.")
            return []

        self.logger.debug("Current anchor: %s", self.anchor_element.bbox)
        page = self.ctx.active_pdf_document.get_page(int(pagenum))
        search_for_candidate = self._get_candidate_search_function(direction, regexp, strict)
        candidates = []
        for candidate in page.get_textboxes().values():
            # Skip anchor element itself from matching.
            if candidate.boxid != self.anchor_element.boxid and search_for_candidate(candidate):
                candidates.append(candidate)

        if only_closest:
            closest_candidate = self._get_closest_from_possibles(direction, candidates)
            return closest_candidate.text

        return [candidate.text for candidate in candidates]

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

        if locator.startswith("text:"):
            criteria = "text"
            _, locator = locator.split(":", 1)
            match = self._find_matching_textbox(criteria, locator)
            if match:
                self.anchor_element = match
                return True

        elif locator.startswith("coords:"):
            _, locator = locator.split(":", 1)
            coords = locator.split(",")
            if len(coords) == 2:
                left, bottom = coords
                top = bottom
                right = left
            elif len(coords) == 4:
                left, bottom, right, top = coords
            else:
                raise ValueError("Give 2 coordinates for point, or 4 for area")

            self.anchor_element = TargetObject()
            self.anchor_element.boxid = -1
            self.anchor_element.bbox = (
                int(left),
                int(bottom),
                int(right),
                int(top),
            )
            self.anchor_element.text = None
            return True

        else:
            # use "text" criteria by default
            criteria = "text"
            match = self._find_matching_textbox(criteria, locator)
            if match:
                self.anchor_element = match
                return True

        self.anchor_element = None
        return False

    def _find_matching_textbox(self, criteria: str, locator: str) -> Optional[str]:
        self.logger.info(
            "find_matching_textbox: ('criteria=%s', 'locator=%s')", criteria, locator
        )

        lower_locator = locator.lower()
        matches = []
        for page in self.active_pdf_document.get_pages().values():
            content = page.get_textboxes()
            for item in content.values():
                # Only text matching at the moment.
                if item.text.lower() == lower_locator:
                    matches.append(item)

        match_count = len(matches)
        if match_count == 1:
            self.logger.debug("Found 1 match for locator '%s'", locator)
            return matches[0]

        if match_count:
            self.logger.info("Found %d matches for locator %r, using the first one", match_count, locator)
            for match in matches:
                self.logger.debug("box %d bbox %s text '%s'", match.boxid, match.bbox, match.text)
            return matches[0]

        self.logger.info("Did not find any matches")
        return None

    @classmethod
    def _is_within_tolerance(cls, base: int, target: int) -> bool:
        max_target = target + cls.PIXEL_TOLERANCE
        min_target = max(target - cls.PIXEL_TOLERANCE, 0)
        return min_target <= base <= max_target

    def _is_match_on_horizontal(
        self, item: TextBox, *, direction: str, regexp: str
    ) -> bool:
        if not item:
            return False

        (left, _, right, top) = self.anchor_element.bbox
        direction_ok = False
        if self._is_within_tolerance(item.top, top):
            if (
                direction == "right"
                and item.left >= right
            ):
                direction_ok = True
            elif (
                direction == "left"
                and item.right <= left
            ):
                direction_ok = True
        if not direction_ok:
            return False

        regex_matched = regexp and re.match(regexp, item.text)
        no_regex = regexp is None
        return any([regex_matched, no_regex])

    def _is_match_on_vertical(
        self, item: TextBox, *, direction: str, regexp: str, strict: bool
    ) -> bool:
        (left, bottom, right, top) = self.anchor_element.bbox
        direction_down = direction in ["bottom", "down"]
        direction_up = direction in ["top", "up"]

        if (direction_down and item.top <= bottom) or (
            direction_up and item.bottom >= top
        ):
            non_strict_match = not strict and (item.right <= right or item.left >= left)
            strict_match = strict and (item.right == right or item.left == left)
            if not any([non_strict_match, strict_match]):
                return False  # item not in range

            if regexp and re.match(regexp, item.text):
                self.logger.debug(
                    "REGEX MATCH %s %s %s", item.boxid, item.text, item.bbox
                )
                return True
            if regexp is None:
                self.logger.debug(
                    "POSSIBLE MATCH %s %s %s", item.boxid, item.text, item.bbox
                )
                return True

        return False

    def _is_match_in_box(self, item: TextBox) -> bool:
        (left, bottom, right, top) = self.anchor_element.bbox
        return (
            left <= item.left
            and right >= item.right
            and bottom <= item.bottom
            and top >= item.top
        )

    def _get_closest_from_possibles(
        self, direction: str, possibles: List[TextBox]
    ) -> TextBox:
        distance = 500000
        closest = None
        (_, bottom, right, top) = self.anchor_element.bbox
        direction_down = direction in ["bottom", "down"]
        for p in possibles:
            if direction_down:
                vertical_distance = bottom - p.top
            else:
                vertical_distance = top - p.bottom
            h_distance_to_right = abs(right - p.right)
            h_distance_to_left = abs(right - p.left)
            horizontal_distance = min(h_distance_to_left, h_distance_to_right)
            calc_distance = math.sqrt(
                math.pow(horizontal_distance, 2) + math.pow(vertical_distance, 2)
            )
            if calc_distance < distance:
                distance = calc_distance
                closest = p

        return closest
