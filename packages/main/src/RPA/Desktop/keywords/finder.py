import time
from typing import List, Union

from RPA.Desktop.keywords import LibraryContext, keyword
from RPA.core.geometry import Point, Region
from RPA.core.locators import (
    Coordinates,
    Offset,
    ImageTemplate,
    parse_locator,
)

try:
    from RPA.recognition import templates

    HAS_RECOGNITION = True
except ImportError:
    HAS_RECOGNITION = False


class TimeoutException(ValueError):
    """Timeout reached while waiting for condition."""


class FinderKeywords(LibraryContext):
    """Keywords for locating elements."""

    def __init__(self, ctx):
        super().__init__(ctx)

        if HAS_RECOGNITION:
            self.confidence = templates.DEFAULT_CONFIDENCE
        else:
            self.confidence = None

    def find(self, locator: str) -> List[Union[Point, Region]]:
        """Internal method for resolving and searching locators."""
        if isinstance(locator, (Region, Point)):
            return [locator]

        locator = parse_locator(locator)

        if isinstance(locator, Coordinates):
            position = Point(locator.x, locator.y)
            return [position]
        elif isinstance(locator, Offset):
            position = self.ctx.get_mouse_position()
            position.offset(locator.x, locator.y)
            return [position]
        elif isinstance(locator, ImageTemplate):
            if not HAS_RECOGNITION:
                raise ValueError(
                    "Image templates not supported, please install "
                    "rpaframework-recognition module"
                )
            # TODO: Add built-in offset support
            confidence = locator.confidence or self.confidence
            try:
                regions = templates.find(
                    image=self.ctx.take_screenshot(),
                    template=locator.path,
                    confidence=confidence,
                )

                left, top, _, _ = self.ctx.get_display_dimensions()
                for region in regions:
                    region.move(left, top)
            except templates.ImageNotFoundError:
                return []

            return regions
        else:
            raise NotImplementedError(f"Unsupported locator: {locator}")

    @keyword
    def find_elements(self, locator: str) -> List[Point]:
        """Find all elements defined by locator, and return their positions.

        Example:

        .. code-block:: robotframework

            ${matches}=    Find elements    image:icon.png
            FOR    ${match}  IN  @{matches}
                Log    Found icon at ${match.x}, ${match.y}
            END

        :param locator: Locator string
        """
        matches = []

        for match in self.find(locator):
            if isinstance(match, Region):
                matches.append(match.center)
            elif isinstance(match, Point):
                matches.append(match)
            else:
                raise TypeError(f"Unknown location type: {match}")

        display = self.ctx.get_display_dimensions()
        for match in matches:
            # TODO: Add as contains() method in region class
            if not (
                (display.left <= match.x <= display.right)
                and (display.top <= match.y <= display.bottom)
            ):
                self.logger.warning("Match outside display bounds: %s", match)

        return matches

    @keyword
    def find_element(self, locator: str) -> Point:
        """Find an element defined by locator, and return its position.

        Example:

        .. code-block:: robotframework

            ${match}=    Find element    image:logo.png
            Log    Found logo at ${match.x}, ${match.y}

        :param locator: Locator string
        """
        matches = self.find_elements(locator)

        if not matches:
            raise ValueError(f"No matches found for: {locator}")

        if len(matches) > 1:
            # TODO: Add run-on-error support and maybe screenshotting matches?
            raise ValueError(
                "Found {count} matches for: {locator}".format(
                    count=len(matches), locator=locator
                )
            )

        return matches[0]

    @keyword
    def wait_for_element(
        self, locator: str, timeout: float = 10.0, interval: float = 0.5
    ) -> Point:
        """Wait for an element defined by locator to exist or
        until timeout is reached.

        Example:

        .. code-block:: robotframework

            Wait for element    alias:CookieConsent    timeout=30
            Click    image:%{ROBOT_ROOT}/accept.png

        :param locator: Locator string
        """
        interval = float(interval)
        end_time = time.time() + float(timeout)

        while time.time() <= end_time:
            try:
                return self.find_element(locator)
            except ValueError:
                time.sleep(interval)

        raise TimeoutException(f"No element found within timeout: {locator}")

    @keyword
    def set_default_confidence(self, confidence: float):
        """Set the default template matching confidence.

        :param confidence: Value from 0 to 100
        """
        confidence = min(confidence, 100.0)
        confidence = max(confidence, 0.0)
        self.confidence = confidence
