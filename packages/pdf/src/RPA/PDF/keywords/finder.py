import math
import re

from typing import (
    List,
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

    @keyword
    def find_text(
        self,
        locator: str,
        pagenum: int = 1,
        direction: str = "right",
        strict: bool = False,
        regexp: str = None,
        only_closest: bool = True,
    ) -> Union[Union[List[TextBox], List[None]], TextBox]:
        """Get closest text (value) to the anchor element.

        PDF needs to be parsed before elements can be found.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                ${value}=  Find Text    text:Invoice Number

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                value = pdf.find_text("text:Invoice Number")

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
        :return: all possible values, only the closest value, or an empty list.
        """
        self.logger.debug(
            "Get Value From Anchor: ('locator=%s', 'direction=%s', 'regexp=%s')",
            locator,
            direction,
            regexp,
        )
        self.set_anchor_to_element(locator)
        possibles = []

        if self.anchor_element:
            self.logger.debug("Current anchor: %s", self.anchor_element.bbox)
            page = self.ctx.active_pdf_document.get_page(int(pagenum))
            for _, item in page.get_textboxes().items():
                possible = None
                # Skip anchor element from matching
                if item.boxid == self.anchor_element.boxid:
                    continue
                if direction in ["left", "right"]:
                    possible = self._is_match_on_horizontal(direction, item, regexp)
                elif direction in ["top", "bottom", "up", "down"]:
                    possible = self._is_match_on_vertical(
                        direction, item, strict, regexp
                    )
                elif direction == "box":
                    possible = self._is_match_in_box(item)
                if possible:
                    possibles.append(possible)
            if only_closest:
                return self._get_closest_from_possibles(direction, possibles)
            else:
                return possibles
        self.logger.info("No anchor.")

        return possibles

    @keyword
    def set_anchor_to_element(self, locator: str) -> bool:
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

        :param locator: element to search for.
        :return: True if element was found.
        """
        self.logger.info("Set anchor to element: ('locator=%s')", locator)
        if not self.ctx.active_pdf_document.is_converted:
            self.ctx.convert()
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

    def _find_matching_textbox(self, criteria: str, locator: str) -> str:
        self.logger.info(
            "find_matching_textbox: ('criteria=%s', 'locator=%s')", criteria, locator
        )
        matches = []
        for _, page in self.active_pdf_document.get_pages().items():
            content = page.get_textboxes()
            for _, item in content.items():
                # Only text matching at the moment
                if item.text.lower() == locator.lower():
                    matches.append(item)
        match_count = len(matches)
        if match_count == 1:
            self.logger.debug("Found 1 match for locator '%s'", locator)
            return matches[0]
        elif match_count == 0:
            self.logger.info("Did not find any matches")
        else:
            self.logger.info("Found %d matches for locator '%s'", match_count, locator)
            for m in matches:
                self.logger.debug("box %d bbox %s text '%s'", m.boxid, m.bbox, m.text)
        return False

    def _is_within_tolerance(self, base: int, target: int) -> bool:
        max_target = target + self.PIXEL_TOLERANCE
        min_target = max(target - self.PIXEL_TOLERANCE, 0)
        return min_target <= base <= max_target

    def _is_match_on_horizontal(
        self, direction: str, item: TextBox, regexp: str
    ) -> Union[TextBox, None]:
        (left, _, right, top) = self.anchor_element.bbox
        match = False
        direction_ok = False
        if (
            direction == "right"
            and self._is_within_tolerance(item.top, top)
            and item.left >= right
        ):
            direction_ok = True
        elif (
            direction == "left"
            and self._is_within_tolerance(item.top, top)
            and item.right <= left
        ):
            direction_ok = True
        if regexp and direction_ok and item and re.match(regexp, item.text):
            match = True
        elif regexp is None and direction_ok and item:
            match = True

        return item if match else None

    def _is_match_on_vertical(
        self, direction: str, item: TextBox, strict: bool, regexp: str
    ) -> Union[TextBox, None]:
        (left, bottom, right, top) = self.anchor_element.bbox
        text = None
        direction_down = direction in ["bottom", "down"]
        direction_up = direction in ["top", "up"]
        if (direction_down and item.top <= bottom) or (
            direction_up and item.bottom >= top
        ):
            if not strict and (item.right <= right or item.left >= left):
                text = item
            elif strict and (item.right == right or item.left == left):
                text = item
            if regexp and text and re.match(regexp, item.text):
                self.logger.debug(
                    "POSSIBLE MATCH %s %s %s", item.boxid, item.text, item.bbox
                )
                return item
            elif regexp is None and text:
                self.logger.debug(
                    "POSSIBLE MATCH %s %s %s", item.boxid, item.text, item.bbox
                )
                return item
        return None

    def _is_match_in_box(self, item: TextBox) -> Union[TextBox, None]:
        (left, bottom, right, top) = self.anchor_element.bbox
        if (
            left <= item.left
            and right >= item.right
            and bottom <= item.bottom
            and top >= item.top
        ):
            return item
        return None

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
