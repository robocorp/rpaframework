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

from RPA.Desktop.keywords.screen import get_displays, region_from_mss_monitor

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

    def find_templates(self, locator: ImageTemplate) -> List[Union[Point, Region]]:
        """Internal helper method for getting image template matches in all displays
        and returning them as Points or Regions, scaled to accomodate macOS HiDPI
        """

        def get_scaled_matches(screenshot, locator, display):
            """ Internal helper function for finding matches on a single screen """
            try:
                matches: List[Region] = templates.find(
                    image=screenshot,
                    template=locator.path,
                    confidence=confidence,
                )

            except templates.ImageNotFoundError:
                return []

            # Calculate scaling factor
            # (only relevant on macOS which uses virtual pixels for HiDPI)
            # Should always be 1.0 on all other platforms
            scale_factor = screenshot.height / display["height"]

            # Virtual screen top-left might not be (0,0)
            left, top, _, _ = display.values()
            for region in matches:
                # Scale by reverse of scale factor
                region.scale(1 / scale_factor)
                region.move(left, top)

            return matches

        regions: List[Region] = []
        confidence = locator.confidence or self.confidence
        self.logger.info("Matching with confidence of %.1f", confidence)
        displays = get_displays()
        for display in displays:
            screenshot = self.ctx.take_screenshot(
                locator=region_from_mss_monitor(display)
            )
            matches = get_scaled_matches(screenshot, locator, display)
            regions.extend(matches)

        return regions

    def find(self, locator: str) -> List[Union[Point, Region]]:
        """Internal method for resolving and searching locators."""
        if isinstance(locator, (Region, Point)):
            return [locator]

        locator = parse_locator(locator)
        self.logger.info("Using locator: %s", locator)

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

            return self.find_templates(locator)

        else:
            raise NotImplementedError(f"Unsupported locator: {locator}")

    @keyword
    def find_elements(self, locator: str) -> List[Union[Point, Region]]:
        """Find all elements defined by locator, and return their positions.

        :param locator: Locator string

        Example:

        .. code-block:: robotframework

            ${matches}=    Find elements    image:icon.png
            FOR    ${match}  IN  @{matches}
                Log    Found icon at ${match.x}, ${match.y}
            END
        """
        matches = []

        for match in self.find(locator):
            if isinstance(match, Region):
                matches.append(match)
            elif isinstance(match, Point):
                matches.append(match)
            else:
                raise TypeError(f"Unknown location type: {match}")

        display: Region = self.ctx.get_display_dimensions()
        for match in matches:
            if not display.contains(match):
                self.logger.warning("Match outside display bounds: %s", match)

        return matches

    @keyword
    def find_element(self, locator: str) -> Union[Point, Region]:
        """Find an element defined by locator, and return its position.

        :param locator: Locator string

        Example:

        .. code-block:: robotframework

            ${match}=    Find element    image:logo.png
            Log    Found logo at ${match.x}, ${match.y}
        """
        matches = self.find_elements(locator)

        if not matches:
            raise ValueError(f"No matches found for: {locator}")

        if len(matches) > 1:
            # TODO: Add run-on-error support and maybe screenshotting matches?
            raise ValueError(
                "Found {count} matches for: {locator} at locations {matches}".format(
                    count=len(matches), locator=locator, matches=matches
                )
            )

        return matches[0]

    @keyword
    def wait_for_element(
        self, locator: str, timeout: float = 10.0, interval: float = 0.5
    ) -> Point:
        """Wait for an element defined by locator to exist or
        until timeout is reached.

        :param locator: Locator string

        Example:

        .. code-block:: robotframework

            Wait for element    alias:CookieConsent    timeout=30
            Click    image:%{ROBOT_ROOT}/accept.png
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

        :param confidence: Value from 1 to 100
        """
        confidence = float(confidence)
        confidence = min(confidence, 100.0)
        confidence = max(confidence, 1.0)
        self.confidence = confidence
