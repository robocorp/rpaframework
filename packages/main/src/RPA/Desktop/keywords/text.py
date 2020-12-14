import time
from typing import Optional
from PIL import ImageOps

from RPA.core.geometry import Region
from RPA.Desktop.keywords import LibraryContext, keyword, screen, HAS_RECOGNITION

if HAS_RECOGNITION:
    from RPA.recognition import ocr  # pylint: disable=no-name-in-module


def ensure_recognition():
    if not HAS_RECOGNITION:
        raise ValueError(
            "Keyword requires OCR features, please install the "
            "rpaframework-recognition package"
        )


class TextKeywords(LibraryContext):
    """Keywords for reading screen information and content."""

    @keyword
    def read_text(self, locator: Optional[str] = None, invert: bool = False):
        """Read text using OCR from the screen, or an area of the
        screen defined by the given locator.

        :param locator: Location of element to read text from
        :param invert:  Invert image colors, useful for reading white text
                        on dark background

        Usage examples:

        .. code-block:: robotframework

            ${label_region}=  Find Element  image:label.png
            ${value_region}=  Move Region   ${label_region}  100  0
            ${text}=          Read Text     ${value_region}

        .. code-block:: python

            label_region = desktop.find_element("image:label.png")
            value_region = desktop.move_region(label_region, 100, 0)
            text = desktop.read_text(value_region)

        """
        ensure_recognition()

        if locator is not None:
            element = self.ctx.wait_for_element(locator)
            if not isinstance(element, Region):
                raise ValueError("Locator must resolve to a region")

            self.logger.info("Reading text from element: %s", element)
            image = screen.grab(element)
        else:
            self.logger.info("Reading text from screen")
            image = screen.grab()

        screen.log_image(image)

        if invert:
            image = ImageOps.invert(image)

        start_time = time.time()
        text = ocr.read(image)
        self.logger.info("Read text in %.2f seconds", time.time() - start_time)

        return text
