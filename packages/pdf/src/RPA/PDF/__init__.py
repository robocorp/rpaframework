import logging
from robotlibcore import DynamicCore

from RPA.core.logger import RobotLogListener

from RPA.PDF.keywords import DocumentKeywords, FinderKeywords, ModelKeywords


class PDF(DynamicCore):
    """`PDF` is a library for managing PDF documents.

    It can be used to extract text from PDFs,
    add watermarks to pages, and decrypt/encrypt documents.

    There is also limited support for updating form field values.

    Input PDF file can be passed as an argument to the keywords,
    or it can be omitted if you first call `Open PDF`. Reference
    to the current active PDF will be stored in the library instance.


    **Examples**

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
            Save Field Values  output_path=output.pdf


    .. code-block:: python

        from RPA.PDF import PDF

        pdf = PDF()

        def extract_data():
            text = pdf.get_text_from_pdf("./tmp/sample.pdf")

        def fill_form():
            pdf.open_pdf("./tmp/sample.pdf")
            pdf.set_field_value("phone_nr", 080123123)
            pdf.set_field_value("address", "robot street 14")
            pdf.save_field_values(output_path="output.pdf")

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

        listener = RobotLogListener()
        listener.register_protected_keywords(["RPA.PDF.decrypt"])

        logging.getLogger("pdfminer").setLevel(logging.INFO)
