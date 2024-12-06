import time
from typing import Optional
from PIL import ImageOps

from RPA.core.geometry import Region
from RPA.Desktop.keywords import LibraryContext, keyword, screen, HAS_RECOGNITION

if HAS_RECOGNITION:
    from RPA.recognition import ocr  # pylint: disable=no-name-in-module
else:
    ocr = None


def ensure_recognition():
    if not HAS_RECOGNITION:
        raise ValueError(
            "Keyword requires OCR features, please install the "
            "rpaframework-recognition package"
        )


class TextKeywords(LibraryContext):
    """Keywords for reading screen information and content."""

    @keyword
    def read_text(
        self,
        locator: Optional[str] = None,
        invert: bool = False,
        language: str = None,
        configuration: str = None,
    ):
        """Read text using OCR from the screen, or an area of the
        screen defined by the given locator.

        :param locator: Location of element to read text from
        :param invert:  Invert image colors, useful for reading white text
            on dark background
        :param language: 3-character ISO 639-2 language code of the text.
            This is passed directly to the pytesseract lib in the lang parameter.
            See https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html#using-one-language
        :param configuration: Tesseract specific parameters like Page Segmentation
            Modes(psm) or OCR Engine Mode (oem). This is passed directly to the
            pytesseract lib in the config parameter.
            See https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html

        Usage examples:

        .. code-block:: robotframework

            ${label_region}=  Find Element  image:label.png
            ${value_region}=  Move Region   ${label_region}  100  0
            ${text}=          Read Text     ${value_region}

        .. code-block:: python

            label_region = desktop.find_element("image:label.png")
            value_region = desktop.move_region(label_region, 100, 0)
            text = desktop.read_text(value_region)

        """  # noqa: E501
        ensure_recognition()

        if locator is not None:
            element = self.ctx.wait_for_element(locator)
            if not isinstance(element, Region):
                raise ValueError("Locator must resolve to a region")

            area = "element: %s" % element
            image = screen.grab(element)
        else:
            area = "screen"
            image = screen.grab()

        screen.log_image(image)

        if invert:
            image = ImageOps.invert(image)

        self.logger.info(
            "Reading text from %s (invert: %s, language: %s, configuration: %s)",
            area,
            invert or "Not set",
            language or "Not set",
            configuration or "Not set",
        )

        start_time = time.time()
        text = ocr.read(image, language, configuration)
        self.logger.info("Read text in %.2f seconds", time.time() - start_time)

        return text
