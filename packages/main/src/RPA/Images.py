import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List

import mss
from PIL import Image
from PIL import ImageDraw
from PIL import ImageOps

from RPA.core.geometry import Region, to_point, to_region
from RPA.core.notebook import notebook_image

try:
    # Check if opencv is available,
    # for improved template matching
    import cv2
    import numpy

    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


def to_image(obj):
    """Convert `obj` to instance of Pillow's Image class."""
    if obj is None or isinstance(obj, Image.Image):
        return obj
    return Image.open(obj)


def clamp(minimum, value, maximum):
    """Clamp value between given minimum and maximum."""
    return max(minimum, min(value, maximum))


def chunks(obj, size, start=0):
    """Convert `obj` container to list of chunks of `size`."""
    return [obj[i : i + size] for i in range(start, len(obj), size)]


@dataclass
class RGB:
    """Container for a single RGB value."""

    red: int
    green: int
    blue: int

    @classmethod
    def from_pixel(cls, value):
        """Create RGB value from pillow getpixel() return value."""
        # RGB(A), ignore possible alpha channel
        if isinstance(value, tuple):
            red, green, blue = value[:3]
        # Grayscale
        else:
            red, green, blue = [value] * 3

        return cls(red, green, blue)

    def luminance(self):
        """Approximate (perceived) luminance for RGB value."""
        return (self.red * 2 + self.green * 3 + self.blue) // 6


class ImageNotFoundError(Exception):
    """Raised when template matching fails."""


class Images:
    """*DEPRECATED* For image-based automation use `RPA.Desktop` instead.

    `Images` is a library for taking screenshots, matching templates, and
    generally manipulating images. It can also be used for GUI-based automation
    when traditional UI locators are not available.

    **Coordinates**

    The coordinates used in the library are pairs of x and y values that
    represent pixels. The upper left corner of the image or screen
    is (0, 0). The x-coordinate increases towards the right, and the y-coordinate
    increases towards the bottom.

    Regions are represented as tuples of (left, top, right, bottom). For example,
    a 400 by 200-pixel region in the upper left corner would be (0, 0, 400, 200).

    **Template matching**

    Template matching refers to an operation where the (potential) location of
    a smaller image is searched from a larger image. It can be used for verifying
    certain conditions or locating UI elements for desktop or web automation.

    **Requirements**

    The default installation depends on `Pillow <https://python-pillow.org/>`_
    library, which is used for general image manipulation operations.

    For more robust and faster template matching, the library can use a combination
    of `NumPy <https://numpy.org/>`_ and `OpenCV <https://opencv.org/>`_.
    They can be installed by opting in to the `cv` dependency:

    ``pip install rpaframework[cv]``

    **Examples**

    **Robot Framework**

    The `Images` library can be imported and used directly in Robot Framework,
    for instance, for capturing screenshots or verifying something on the screen.

    Desktop automation based on images should be done using the corresponding
    desktop library, i.e. ``RPA.Desktop``.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Images

        *** Keywords ***
        Should show success
            [Documentation]    Raises ImageNotFoundError if success image is not on screen
            Find template on screen    ${CURDIR}${/}success.png

        Save screenshot to results
            [Documentation]    Saves screenshot of desktop with unique name
            ${timestamp}=      Get current date    result_format=%H%M%S
            Take screenshot    filename=${OUTPUT_DIR}${/}desktop_${timestamp}.png

    **Python**

    .. code-block:: python

        from RPA.Images import Images

        def draw_matches_on_desktop(template):
            lib = Images()
            screenshot = lib.take_screenshot()

            matches = lib.find_template_in_image(screenshot, template)
            for match in matches:
                lib.show_region_in_image(screenshot, match)

            screenshot.save("matches.png")
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.matcher = TemplateMatcher(opencv=HAS_OPENCV)

    def take_screenshot(self, filename=None, region=None) -> Image:
        """*DEPRECATED* Use keyword `RPA.Desktop.Take Screenshot` instead
        Take a screenshot of the current desktop.

        :param filename:    Save screenshot to filename
        :param region:      Region to crop screenshot to
        """
        region = to_region(region)

        with mss.mss() as sct:
            if region is not None:
                image = sct.grab(region.as_tuple())
            else:
                # mss uses the first monitor on the array as an
                # alias for a combined virtual monitor
                image = sct.grab(sct.monitors[0])

        if filename is not None:
            filename = Path(filename).with_suffix(".png")
            mss.tools.to_png(image.rgb, image.size, output=filename)

            notebook_image(filename)
            self.logger.info("Saved screenshot as '%s'", filename)

        # Convert raw mss screenshot to Pillow Image. Might be a bit slow
        pillow_image = Image.frombytes("RGB", image.size, image.bgra, "raw", "BGRX")
        return pillow_image

    def crop_image(self, image, region, filename=None):
        """Crop an existing image.

        :param image:       Image to crop
        :param region:      Region to crop image to
        :param filename:    Save cropped image to filename
        """
        region = to_region(region)
        image = to_image(image)

        image = image.crop(region.as_tuple())
        image.load()

        if filename:
            # Suffix isn't created automatically here
            image.save(Path(filename).with_suffix(".png"), "PNG")
            notebook_image(filename)

    def find_template_in_image(
        self, image, template, region=None, limit=None, tolerance=None
    ) -> List[Region]:
        """*DEPRECATED* Use keyword `Find` from library `RPA.Recognition` instead
        Attempt to find the template from the given image.

        :param image:       Path to image or Image instance, used to search from
        :param template:    Path to image or Image instance, used to search with
        :param limit:       Limit returned results to maximum of `limit`.
        :param region:      Area to search from. Can speed up search significantly.
        :param tolerance:   Tolerance for matching, value between 0.1 and 1.0
        :return:            List of matching regions
        :raises ImageNotFoundError: No match was found
        """
        # Ensure images are in Pillow format
        image = to_image(image)
        template = to_image(template)

        # Crop image if requested
        if region is not None:
            region = to_region(region)
            image = image.crop(region.as_tuple())

        # Verify template still fits in image
        if template.size[0] > image.size[0] or template.size[1] > image.size[1]:
            raise ValueError("Template is larger than search region")

        # Strip alpha channels
        if image.mode == "RGBA":
            image = image.convert("RGB")
        if template.mode == "RGBA":
            template = template.convert("RGB")

        # Do the actual search
        start = time.time()
        matches = self.matcher.match(image, template, limit, tolerance)
        logging.info("Scanned image in %.2f seconds", time.time() - start)

        if not matches:
            raise ImageNotFoundError("No matches for given template")

        # Convert region coördinates back to full-size coördinates
        if region is not None:
            for match in matches:
                match.move(region.left, region.top)

        return matches

    def find_template_on_screen(self, template, **kwargs) -> List[Region]:
        """*DEPRECATED!!* use `RPA.Desktop.Find Element` instead
        Attempt to find the template image from the current desktop.
        For argument descriptions, see ``find_template_in_image()``
        """
        return self.find_template_in_image(self.take_screenshot(), template, **kwargs)

    def wait_template_on_screen(self, template, timeout=5, **kwargs):
        """*DEPRECATED!!* use `RPA.Desktop.Wait For Element` instead
        Wait for template image to appear on current desktop.
        For further argument descriptions, see ``find_template_in_image()``

        :param timeout: Time to wait for template (in seconds)
        """
        start_time = time.time()
        while time.time() - start_time < float(timeout):
            try:
                return self.find_template_on_screen(template, **kwargs)
            except ImageNotFoundError:
                time.sleep(0.1)
        raise ImageNotFoundError("Couldn't find template on screen within timeout")

    def show_region_in_image(self, image, region, color="red", width=5):
        """Draw a rectangle onto the image around the given region.

        :param image:   image to draw onto
        :param region:  coordinates for region or Region object
        :param color:   color of rectangle
        :param width:   line width of rectangle
        """
        image = to_image(image)
        region = to_region(region)

        draw = ImageDraw.Draw(image)
        draw.rectangle(region.as_tuple(), outline=color, width=int(width))
        return image

    def show_region_on_screen(self, region, color="red", width=5):
        """Draw a rectangle around the given region on the current desktop.

        :param region:  coordinates for region or Region object
        :param color:   color of rectangle
        :param width:   line width of rectangle
        """
        image = self.take_screenshot()
        return self.show_region_in_image(image, region, color, width)

    def get_pixel_color_in_image(self, image, point):
        """Get the RGB value of a pixel in the image.

        :param image:   image to get pixel from
        :param point:   coordinates for pixel or Point object
        """
        point = to_point(point)
        pixel = image.getpixel(point.as_tuple())
        return RGB.from_pixel(pixel)

    def get_pixel_color_on_screen(self, point):
        """Get the RGB value of a pixel currently on screen.

        :param point:   coordinates for pixel or Point object
        """
        return self.get_pixel_color_in_image(self.take_screenshot(), point)


class TemplateMatcher:
    """Container class for different template matching methods."""

    DEFAULT_TOLERANCE = 0.95  # Tolerance for correlation matching methods
    LIMIT_FAILSAFE = 256  # Fail-safe limit of maximum match count

    def __init__(self, opencv=False):
        self.logger = logging.getLogger(__name__)
        self._opencv = opencv
        self._tolerance = self.DEFAULT_TOLERANCE
        self._tolerance_warned = False

    @property
    def tolerance(self):
        return self._tolerance

    @tolerance.setter
    def tolerance(self, value):
        self._tolerance = clamp(0.10, value, 1.00)

    def match(self, image, template, limit=None, tolerance=None):
        """Attempt to find the template in the given image.

        :param image:       image to search from
        :param template:    image to search with
        :param limit:       maximum number of returned matches
        :param tolerance:   minimum correlation factor between template and image
        :return:            list of regions that match criteria
        """
        if self._opencv:
            match_func = self._iter_match_opencv
        else:
            match_func = self._iter_match_pillow

        matches = []
        for match in match_func(image, template, tolerance):
            matches.append(match)
            if limit is not None and len(matches) >= int(limit):
                break
            elif len(matches) >= self.LIMIT_FAILSAFE:
                self.logger.warning(
                    "Reached maximum of %d matches", self.LIMIT_FAILSAFE
                )
                break

        return matches

    def _iter_match_opencv(self, image, template, tolerance):
        """Use opencv's matchTemplate() to slide the `template` over
        `image` to calculate correlation coefficients, and then
        filter with a tolerance to find all relevant global maximums.
        """
        # pylint: disable=no-member
        tolerance = tolerance or self.tolerance
        template_width, template_height = template.size

        image = numpy.array(image)
        template = numpy.array(template)

        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        template = cv2.cvtColor(template, cv2.COLOR_RGB2BGR)

        # Template matching result is a single channel array of shape:
        # Width:  Image width  - template width  + 1
        # Height: Image height - template height + 1
        coefficients = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        coeff_height, coeff_width = coefficients.shape

        while True:
            # The point (match_x, match_y) is the top-left of the best match
            _, match_coeff, _, (match_x, match_y) = cv2.minMaxLoc(coefficients)
            if match_coeff < tolerance:
                break

            # Zero out values for a template-sized region around the best match
            # to prevent duplicate matches for the same element.
            left = clamp(0, match_x - template_width // 2, coeff_width)
            top = clamp(0, match_y - template_height // 2, coeff_height)
            right = clamp(0, match_x + template_width // 2, coeff_width)
            bottom = clamp(0, match_y + template_height // 2, coeff_height)

            coefficients[top:bottom, left:right] = 0

            yield Region.from_size(match_x, match_y, template_width, template_height)

    def _iter_match_pillow(self, image, template, tolerance):
        """Brute-force search for template image in larger image.

        Use optimized string search for finding the first row and then
        check if whole template matches.

        TODO: Generalize string-search algorithm to work in two dimensions
        """
        if tolerance is not None and not self._tolerance_warned:
            self._tolerance_warned = True
            self.logger.warning(
                "Template matching tolerance not supported for current search method"
            )

        image = ImageOps.grayscale(image)
        template = ImageOps.grayscale(template)

        template_width, template_height = template.size
        template_rows = chunks(tuple(template.getdata()), template_width)

        image_width, _ = image.size
        image_rows = chunks(tuple(image.getdata()), image_width)

        for image_y, image_row in enumerate(image_rows[: -len(template_rows)]):
            for image_x in self._search_string(image_row, template_rows[0]):
                match = True
                for match_y, template_row in enumerate(template_rows[1:], image_y):
                    match_row = image_rows[match_y][image_x : image_x + template_width]
                    if template_row != match_row:
                        match = False
                        break

                if match:
                    yield Region.from_size(
                        image_x, image_y, template_width, template_height
                    )

    def _search_string(self, text, pattern):
        """Python implementation of Knuth-Morris-Pratt string search algorithm."""
        pattern_len = len(pattern)

        # Build table of shift amounts
        shifts = [1] * (pattern_len + 1)
        shift = 1
        for idx in range(pattern_len):
            while shift <= idx and pattern[idx] != pattern[idx - shift]:
                shift += shifts[idx - shift]
            shifts[idx + 1] = shift

        # Do the actual search
        start_idx = 0
        match_len = 0
        for char in text:
            while (
                match_len == pattern_len
                or match_len >= 0
                and pattern[match_len] != char
            ):
                start_idx += shifts[match_len]
                match_len -= shifts[match_len]
            match_len += 1
            if match_len == pattern_len:
                yield start_idx
