import logging
from robotlibcore import DynamicCore

from RPA.PDF.keywords import DocumentKeywords, FinderKeywords, ModelKeywords


class PDF(DynamicCore):
    """`PDF` is a library for managing PDF documents.

    It can be used to extract text from PDFs,
    add watermarks to pages, and decrypt/encrypt documents.


    Usage example:

    **Robot Framework**

    .. code-block:: robotframework

        ***Settings***
        Library    RPA.PDF

        ***Tasks***
        Extract Data
            ${text}=    Get Text From PDF    ./tmp/sample.pdf

        Fill Form
            Open PDF    ./tmp/sample.pdf
            Set Field Value    phone_nr   080123123
            Set Field Value    address    robot street 14
            Save Field Values


    .. code-block:: python

        from RPA.PDF import PDF

        pdf = PDF()

        def extract_data():
            text = pdf.get_text_from_pdf("./tmp/sample.pdf")

        def fill_form():
            pdf.open_pdf("./tmp/sample.pdf")
            pdf.set_field_value("phone_nr", 080123123)
            pdf.set_field_value("address", "robot street 14")
            pdf.save_field_values()

    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.fileobjects = {}
        self.active_pdf_document = None

        # Register keyword libraries to LibCore
        libraries = [
            DocumentKeywords(self),
            FinderKeywords(self),
            ModelKeywords(self),
        ]
        super().__init__(libraries)

        # TODO: how to use this RPA.main keyword library
        # listener = RobotLogListener()
        # listener.register_protected_keywords(["RPA.PDF.decrypt"])
