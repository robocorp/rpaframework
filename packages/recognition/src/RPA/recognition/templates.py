import logging
import time
import math
from pathlib import Path
from typing import Any, Iterator, List, Optional, Union

import cv2
import numpy
from PIL import Image
from RPA.core import geometry
from RPA.core.geometry import Region


DEFAULT_CONFIDENCE = 80.0
LIMIT_FAILSAFE = 256

logger = logging.getLogger(__name__)


def clamp(minimum, value, maximum):
    """Clamp value between given minimum and maximum."""
    return max(minimum, min(value, maximum))


def log2lin(minimum, value, maximum):
    """Maps logarithmic scale to linear scale of same range."""
    assert value >= minimum
    assert value <= maximum
    return (maximum - minimum) * (math.log(value) - math.log(minimum)) / (
        math.log(maximum) - math.log(minimum)
    ) + minimum


class ImageNotFoundError(Exception):
    """Raised when template matching fails."""


def find(
    image: Union[Image.Image, Path],
    template: Union[Image.Image, Path],
    region: Optional[Region] = None,
    limit: Optional[int] = None,
    confidence: float = DEFAULT_CONFIDENCE,
) -> List[Region]:
    """Attempt to find the template from the given image.

    :param image:       Path to image or Image instance, used to search from
    :param template:    Path to image or Image instance, used to search with
    :param limit:       Limit returned results to maximum of `limit`.
    :param region:      Area to search from. Can speed up search significantly.
    :param confidence:  Confidence for matching, value between 1 and 100
    :return:            List of matching regions
    :raises ImageNotFoundError: No match was found
    """
    # Ensure images are in Pillow format
    image = _to_image(image)
    template = _to_image(template)

    # Convert confidence value to tolerance
    tolerance = _to_tolerance(confidence)

    # Crop image if requested
    if region is not None:
        region = geometry.to_region(region)
        image = image.crop(region.as_tuple())

    # Verify template still fits in image
    if template.size[0] > image.size[0] or template.size[1] > image.size[1]:
        raise ValueError("Template is larger than search region")

    # Do the actual search
    start = time.time()

    matches: List[Region] = []
    for match in _match_template(image, template, tolerance):
        matches.append(match)
        if limit is not None and len(matches) >= int(limit):
            break
        elif len(matches) >= LIMIT_FAILSAFE:
            logger.warning("Reached maximum of %d matches", LIMIT_FAILSAFE)
            break

    logging.info("Scanned image in %.2f seconds", time.time() - start)

    if not matches:
        raise ImageNotFoundError("No matches for given template")

    # Convert region coördinates back to full-size coördinates
    if region is not None:
        for match in matches:
            match.move(region.left, region.top)

    return matches


def _to_image(obj: Any) -> Image.Image:
    """Convert `obj` to instance of Pillow's Image class."""
    if obj is None or isinstance(obj, Image.Image):
        return obj
    return Image.open(obj)


def _to_tolerance(confidence):
    """Convert confidence value to tolerance.

    Confidence is a logarithmic scale from 1 to 100,
    tolerance is a linear scale from 0.01 to 1.00.
    """
    value = float(confidence)
    value = clamp(1, value, 100)
    value = log2lin(1, value, 100)
    value = value / 100.0
    return value


def _match_template(
    image: Image.Image, template: Image.Image, tolerance: float
) -> Iterator[Region]:
    """Use opencv's matchTemplate() to slide the `template` over
    `image` to calculate correlation coefficients, and then
    filter with a tolerance to find all relevant global maximums.
    """
    template_width, template_height = template.size

    if image.mode == "RGBA":
        image = image.convert("RGB")
    if template.mode == "RGBA":
        template = template.convert("RGB")

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
