import logging
import time
from pathlib import Path
from typing import Union, Dict, List

import pytesseract
from pytesseract import TesseractNotFoundError
from PIL import Image

from RPA.core.geometry import Region
from RPA.recognition.utils import to_image

LOGGER = logging.getLogger(__name__)

# TODO: refer to conda package when created?
INSTALL_PROMPT = (
    "tesseract is not installed or not in PATH, "
    "see library documentation for installation instructions"
)


def find(image: Union[Image.Image, Path]):
    """Scan image for text and return a list of words,
    including their bounding boxes and confidences.

    :param image: Path to image or Image object
    """
    image = to_image(image)
    data = _scan_image(image)

    results = []
    for word in _iter_rows(data):
        if word["level"] != 5:
            continue

        region = Region.from_size(
            word["left"], word["top"], word["width"], word["height"]
        )
        results.append(
            {"text": word["text"], "region": region, "confidence": float(word["conf"])}
        )

    return results


def _scan_image(image: Union[Image.Image, Path]) -> Dict:
    """Use tesseract to scan image for text."""
    try:
        start_time = time.time()
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        logging.info("Scanned image in %.2f seconds", time.time() - start_time)
        return data
    except TesseractNotFoundError as err:
        raise EnvironmentError(INSTALL_PROMPT) from err


def _iter_rows(data: Dict) -> List:
    """Convert dictionary of columns to iterable rows."""
    return (dict(zip(data.keys(), values)) for values in zip(*data.values()))
