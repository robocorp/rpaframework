import time
from typing import Any, Callable, List, Optional, Union, Tuple

from PIL import Image
from RPA.Desktop.keywords import (
    LibraryContext,
    keyword,
    screen,
    ElementNotFound,
    MultipleElementsFound,
    TimeoutException,
    HAS_RECOGNITION,
)

from RPA.core.geometry import Point, Region
from RPA.core.locators import (
    Locator,
    PointLocator,
    OffsetLocator,
    RegionLocator,
    ImageLocator,
    OcrLocator,
    parse_locator,
)

if HAS_RECOGNITION:
    from RPA.recognition import templates, ocr  # pylint: disable=no-name-in-module

Geometry = Union[Point, Region]


def ensure_recognition():
    if not HAS_RECOGNITION:
        raise ValueError(
            "Locator type not supported, please install the "
            "rpaframework-recognition package"
        )


def transform(
    regions: List[Region], source: Region, destination: Region
) -> List[Region]:
    """Transform given regions from a local coordinate system to a
    global coordinate system.

    Takes into account location and scaling of the regions.
    Assumes that the aspect ratio does not change.

    :param regions: List of regions to transform
    :param source: Dimensions of local coordinate system
    :param destination: Position/scale of local coordinates in the global scope
    """
    scale = float(destination.height) / float(source.height)

    transformed = []
    for region in regions:
        region = region.scale(scale)
        region = region.move(destination.left, destination.top)
        transformed.append(region)

    return transformed


def clamp(minimum: float, value: float, maximum: float) -> float:
    """Clamp value between given minimum and maximum."""
    return max(minimum, min(value, maximum))


class FinderKeywords(LibraryContext):
    """Keywords for locating elements."""

    def __init__(self, ctx):
        super().__init__(ctx)

        self.timeout = 3.0
        if HAS_RECOGNITION:
            self.confidence = templates.DEFAULT_CONFIDENCE
        else:
            self.confidence = 80.0

    def _find(self, locator: str) -> List[Geometry]:
        """Internal method for resolving and searching locators."""
        if isinstance(locator, (Region, Point)):
            return [locator]

        locator: Locator = parse_locator(locator)
        self.logger.info("Using locator: %s", locator)

        if isinstance(locator, PointLocator):
            position = Point(locator.x, locator.y)
            return [position]
        elif isinstance(locator, OffsetLocator):
            position = self.ctx.get_mouse_position()
            position = position.move(locator.x, locator.y)
            return [position]
        elif isinstance(locator, RegionLocator):
            region = Region(locator.left, locator.top, locator.right, locator.bottom)
            return [region]
        elif isinstance(locator, ImageLocator):
            ensure_recognition()
            return self._find_templates(locator)
        elif isinstance(locator, OcrLocator):
            ensure_recognition()
            return self._find_ocr(locator)
        else:
            raise NotImplementedError(f"Unsupported locator: {locator}")

    def _find_templates(self, locator: ImageLocator) -> List[Region]:
        """Find all regions that match given image template,
        inside the combined virtual display.
        """
        confidence = locator.confidence or self.confidence
        self.logger.info("Matching with confidence of %.1f", confidence)

        def finder(image: Image.Image) -> List[Region]:
            try:
                return templates.find(
                    image=image,
                    template=locator.path,
                    confidence=confidence,
                )
            except templates.ImageNotFoundError:
                return []

        return self._find_from_displays(finder)

    def _find_ocr(self, locator: OcrLocator) -> List[Region]:
        """Find the position of all blocks of text that match the given string,
        inside the combined virtual display.
        """
        confidence = locator.confidence or self.confidence
        self.logger.info("Matching with confidence of %.1f", confidence)

        def finder(image: Image.Image) -> List[Region]:
            matches = ocr.find(
                image=image,
                text=locator.text,
                confidence=confidence,
            )

            return [match["region"] for match in matches]

        return self._find_from_displays(finder)

    def _find_from_displays(
        self, finder: Callable[[Image.Image], List[Region]]
    ) -> List[Region]:
        """Call finder function for each display and return
        a list of found regions.

        :param finder: Callable that searches an image
        """
        matches = []
        screenshots = []

        # Search all displays, and map results to combined virtual display

        start_time = time.time()
        for display in screen.displays():
            image = screen.grab(display)
            regions = finder(image)

            for region in regions:
                region = region.resize(5)
                screenshot = image.crop(region.as_tuple())
                screenshots.append(screenshot)

            local = Region.from_size(0, 0, image.size[0], image.size[1])
            regions = transform(regions, local, display)
            matches.extend(regions)

        # Log matches and preview images

        duration = time.time() - start_time
        plural = "es" if len(matches) != 1 else ""

        self.logger.info("Searched in %.2f seconds", duration)
        self.logger.info("Found %d match%s", len(matches), plural)

        for match, screenshot in zip(matches, screenshots):
            screen.log_image(screenshot, size=400)
            self.logger.info(match)

        return matches

    def _wait_condition(
        self,
        condition: Callable[[], Tuple[bool, Any]],
        timeout: Optional[float] = None,
        interval: float = 0.5,
    ) -> Any:
        """Wait for condition to succeed, or raise a timeout.

        When the condition is successful it should return
        a tuple of (True, ReturnValue), and when it is not successful
        it should return a tuple of (False, ErrorMessage).

        :param condition: Condition function to check
        :param timeout: Time to wait in seconds
        :param interval: The minimum interval between checks
        """
        if timeout is None:
            timeout = self.timeout

        interval = float(interval)
        end_time = time.time() + float(timeout)

        error = "Operation timed out"
        while time.time() <= end_time:
            start = time.time()
            success, value = condition()

            if success:
                return value

            error = value
            duration = time.time() - start
            if duration < interval:
                time.sleep(interval - duration)

        raise TimeoutException(error)

    @keyword
    def find_elements(self, locator: str) -> List[Geometry]:
        """Find all elements defined by locator, and return their positions.

        :param locator: Locator string

        Example:

        .. code-block:: robotframework

            ${matches}=    Find elements    image:icon.png
            FOR    ${match}  IN  @{matches}
                Log    Found icon at ${match.x}, ${match.y}
            END
        """
        matches = self._find(locator)

        display = self.ctx.get_display_dimensions()
        for match in matches:
            if not display.contains(match):
                self.logger.warning("Match outside display bounds: %s", match)

        return matches

    @keyword
    def find_element(self, locator: str) -> Geometry:
        """Find an element defined by locator, and return its position.
        Raises ``ElementNotFound`` if` no matches were found, or
        ``MultipleElementsFound`` if there were multiple matches.

        :param locator: Locator string

        Example:

        .. code-block:: robotframework

            ${match}=    Find element    image:logo.png
            Log    Found logo at ${match.x}, ${match.y}
        """
        matches = self.find_elements(locator)

        if not matches:
            raise ElementNotFound(f"No matches found for: {locator}")

        if len(matches) > 1:
            # TODO: Add run-on-error support and maybe screenshotting matches?
            raise MultipleElementsFound(
                "Found {count} matches for: {locator} at locations {matches}".format(
                    count=len(matches), locator=locator, matches=matches
                )
            )

        return matches[0]

    @keyword
    def wait_for_element(
        self, locator: str, timeout: Optional[float] = None, interval: float = 0.5
    ) -> Geometry:
        """Wait for an element defined by locator to exist, or
        raise a TimeoutException if none were found within timeout.

        :param locator: Locator string

        Example:

        .. code-block:: robotframework

            Wait for element    alias:CookieConsent    timeout=30
            Click    image:%{ROBOT_ROOT}/accept.png
        """

        def condition():
            """Verify that a single match is found."""
            try:
                return True, self.find_element(locator)
            except (ElementNotFound, MultipleElementsFound) as err:
                return False, err

        return self._wait_condition(condition, timeout, interval)

    @keyword
    def wait_for_element_to_disappear(
        self, locator: str, timeout: float = 10.0, interval: float = 0.5
    ) -> None:
        """Wait for an element defined by locator to disappear.

        Example:

        .. code-block:: robotframework

            Wait for element to disappear    alias:LoadingScreen    timeout=30
            Click    image:%{ROBOT_ROOT}/main_menu.png
        """

        def condition():
            """Verify that no matches are found."""
            try:
                match = self.find_element(locator)
                return False, f"Element found at: {match}"
            except MultipleElementsFound as err:
                return False, err
            except ElementNotFound:
                return True, None

        return self._wait_condition(condition, timeout, interval)

    @keyword
    def set_default_timeout(self, timeout: float = 3.0):
        """Set the default time to wait for elements.

        :param timeout: Time in seconds
        """
        self.timeout = max(0.0, float(timeout))

    @keyword
    def set_default_confidence(self, confidence: float = None):
        """Set the default template matching confidence.

        :param confidence: Value from 1 to 100
        """
        if confidence is None:
            confidence = templates.DEFAULT_CONFIDENCE if HAS_RECOGNITION else 80.0

        self.confidence = clamp(1.0, float(confidence), 100.0)
