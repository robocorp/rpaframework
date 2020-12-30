import logging
from robotlibcore import DynamicCore

from RPA.PDF.utils import Buffer
from RPA.PDF.keywords import DocumentKeywords, FinderKeywords, ModelKeywords


class PDF(DynamicCore):
    """`PDF` is a library for managing PDF documents.

    It provides an easy method of generating a PDF document from an HTML formatted
    template file.

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.PDF

        *** Variables ***
        ${TEMPLATE}    order.template
        ${PDF}         result.pdf
        &{VARS}        name=Robot Generated
        ...            email=robot@domain.com
        ...            zip=00100
        ...            items=Item 1, Item 2

        *** Tasks ***
        Create PDF from HTML template
            Template HTML to PDF   ${TEMPLATE}  ${PDF}  ${VARS}

    **Python**

    .. code-block:: python

        from RPA.PDF import PDF

        p = PDF()
        orders = ["item 1", "item 2", "item 3"]
        vars = {
            "name": "Robot Process",
            "email": "robot@domain.com",
            "zip": "00100",
            "items": "<br/>".join(orders),
        }
        p.template_html_to_pdf("order.template", "order.pdf", vars)
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.buffer = Buffer(self.logger)
        self.rpa_pdf_document = None

        # Register keyword libraries to LibCore
        libraries = [
            DocumentKeywords(self),
            FinderKeywords(self),
            ModelKeywords(self),
        ]
        super().__init__(libraries)
