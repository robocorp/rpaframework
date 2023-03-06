import time
from typing import Callable, List, Optional, Union

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

from RPA.core.geometry import Point, Region, Undefined
from RPA.core.locators import (
    Locator,
    LocatorType,
    PointLocator,
    OffsetLocator,
    RegionLocator,
    SizeLocator,
    ImageLocator,
    OcrLocator,
    syntax,
)

if HAS_RECOGNITION:
    from RPA.recognition import templates, ocr  # pylint: disable=no-name-in-module

Geometry = Union[Point, Region, Undefined]


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
        self._resolver = syntax.Resolver(self._find, self.locators_path)

        self.timeout = 3.0
        if HAS_RECOGNITION:
            self.confidence = templates.DEFAULT_CONFIDENCE
        else:
            self.confidence = 80.0

    def _find(self, base: Geometry, locator: LocatorType) -> List:
        """Internal method for resolving and searching locators."""
        if isinstance(locator, (Region, Point)):
            return [locator]

        self.logger.debug("Finding locator: %s", locator)

        finders = {
            PointLocator: self._find_point,
            OffsetLocator: self._find_offset,
            RegionLocator: self._find_region,
            SizeLocator: self._find_size,
            ImageLocator: self._find_templates,
            OcrLocator: self._find_ocr,
        }

        for klass, finder in finders.items():
            if isinstance(locator, klass):
                return finder(base, locator)

        raise NotImplementedError(f"Unsupported locator: {locator}")

    def _find_point(self, base: Geometry, point: PointLocator):
        """Find absolute point on screen. CAn not be based on existing value."""
        if not isinstance(base, Undefined):
            self.logger.warning("Using absolute point coordinates")

        result = Point(point.x, point.y)
        return [result]

    def _find_offset(self, base: Geometry, offset: OffsetLocator):
        """Find pixel offset from given base value, or if no base,
        offset from current mouse position.
        """
        if isinstance(base, Undefined):
            position = self.ctx.get_mouse_position()
        elif isinstance(base, Region):
            position = base.center
        else:
            position = base

        result = position.move(offset.x, offset.y)
        return [result]

    def _find_region(self, base: Geometry, region: RegionLocator):
        """Find absolute region on screen. Can not be based on existing value."""
        if not isinstance(base, Undefined):
            self.logger.warning("Using absolute region coordinates")

        position = Region(region.left, region.top, region.right, region.bottom)
        return [position]

    def _find_size(self, base: Geometry, size: SizeLocator):
        """Find region of fixed size around base, or origin if no base defined."""
        if isinstance(base, Undefined):
            return Region.from_size(0, 0, size.width, size.height)

        if isinstance(base, Region):
            center = base.center
        else:
            center = base

        left = center.x - size.width // 2
        top = center.y - size.height // 2

        result = Region.from_size(left, top, size.width, size.height)
        return [result]

    def _find_templates(self, base: Geometry, locator: ImageLocator) -> List[Region]:
        """Find all regions that match given image template,
        inside the combined virtual display.
        """
        ensure_recognition()

        if isinstance(base, Undefined):
            region = None
        elif isinstance(base, Region):
            region = base
        else:
            raise ValueError(f"Unsupported search specifier for template: {base}")

        confidence = locator.confidence or self.confidence
        self.logger.info(
            "Searching for image '%s' (region: %s, confidence: %.1f)",
            locator.path,
            region or "display",
            confidence,
        )

        def finder(image: Image.Image) -> List[Region]:
            try:
                return templates.find(
                    image=image,
                    template=locator.path,
                    confidence=confidence,
                    region=region,
                )

            except templates.ImageNotFoundError:
                return []

        return self._find_from_displays(finder)

    def _find_ocr(self, base: Geometry, locator: OcrLocator) -> List[Region]:
        """Find the position of all blocks of text that match the given string,
        inside the combined virtual display.
        """
        ensure_recognition()

        if isinstance(base, Undefined):
            region = None
        elif isinstance(base, Region):
            region = base
        else:
            raise ValueError(f"Unsupported search specifier for OCR: {base}")

        confidence = locator.confidence or self.confidence
        language = locator.language
        self.logger.info(
            "Searching for text '%s' (region: %s, confidence: %.1f, language: %s)",
            locator.text,
            region or "display",
            confidence,
            language or "Not set",
        )

        def finder(image: Image.Image) -> List[Region]:
            matches = ocr.find(
                image=image,
                text=locator.text,
                confidence=confidence,
                region=region,
                language=language,
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

        self.logger.debug("Searched in %.2f seconds", duration)
        self.logger.info("Found %d match%s", len(matches), plural)

        for match, screenshot in zip(matches, screenshots):
            screen.log_image(screenshot, size=400)
            self.logger.info(match)

        return matches

    @keyword
    def find_elements(self, locator: LocatorType) -> List[Geometry]:
        """Find all elements defined by locator, and return their positions.

        :param locator: Locator string

        Example:

        .. code-block:: robotframework

            ${matches}=    Find elements    image:icon.png
            FOR    ${match}  IN  @{matches}
                Log    Found icon at ${match.right}, ${match.top}
            END
        """
        self.logger.info("Resolving locator: %s", locator)

        if isinstance(locator, (Locator, Region, Point)):
            return self._find(Undefined(), locator)
        else:
            return self._resolver.dispatch(str(locator))

    @keyword
    def find_element(self, locator: LocatorType) -> Geometry:
        """Find an element defined by locator, and return its position.
        Raises ``ElementNotFound`` if` no matches were found, or
        ``MultipleElementsFound`` if there were multiple matches.

        :param locator: Locator string

        Example:

        .. code-block:: robotframework

            ${match}=    Find element    image:logo.png
            Log    Found logo at ${match.right}, ${match.top}
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
        self,
        locator: LocatorType,
        timeout: Optional[float] = None,
        interval: float = 0.5,
    ) -> Geometry:
        """Wait for an element defined by locator to exist, or
        raise a TimeoutException if none were found within timeout.

        :param locator: Locator string

        Example:

        .. code-block:: robotframework

            Wait for element    alias:CookieConsent    timeout=30
            Click    image:%{ROBOT_ROOT}/accept.png
        """
        if timeout is None:
            timeout = self.timeout

        interval = float(interval)
        end_time = time.time() + float(timeout)

        error = "Operation timed out"
        while time.time() <= end_time:
            start = time.time()
            try:
                return self.find_element(locator)
            except (ElementNotFound, MultipleElementsFound) as err:
                error = err

            duration = time.time() - start
            if duration < interval:
                time.sleep(interval - duration)

        raise TimeoutException(error)

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
