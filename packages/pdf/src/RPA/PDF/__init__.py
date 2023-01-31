import logging
from typing import Dict

from robotlibcore import DynamicCore
from RPA.core.logger import RobotLogListener

from RPA.PDF.keywords import DocumentKeywords, FinderKeywords, ModelKeywords
from RPA.PDF.keywords.model import Document


class PDF(DynamicCore):
    """`PDF` is a library for managing PDF documents.

    It can be used to extract text from PDFs, add watermarks to pages, and
    decrypt/encrypt documents.

    There is also limited support for updating form field values. (check
    ``Set Field Value`` and ``Save Field Values`` for more info)

    The input PDF file can be passed as an argument to the keywords, or it can be
    omitted if you first call ``Open PDF``. A reference to the current active PDF will
    be stored in the library instance and can be changed by using the ``Switch To PDF``
    keyword with another PDF file path, therefore you can asynchronously work with
    multiple PDFs.

    .. Attention::
        Keep in mind that this library works with text-based PDFs, and it **can't
        extract information from an image-based (scan)** PDF file. For accurate
        results, you have to use specialized external services wrapped by the
        ``RPA.DocumentAI`` library.

    Portal example with video recording demo for parsing PDF invoices:
    https://github.com/robocorp/example-parse-pdf-invoice

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.PDF
        Library    String

        *** Tasks ***
        Extract Data From First Page
            ${text} =    Get Text From PDF    report.pdf
            ${lines} =     Get Lines Matching Regexp    ${text}[${1}]    .+pain.+
            Log    ${lines}

        Get Invoice Number
            Open Pdf    invoice.pdf
            ${matches} =  Find Text    Invoice Number
            Log List      ${matches}

        Fill Form Fields
            Switch To Pdf    form.pdf
            ${fields} =     Get Input Fields   encoding=utf-16
            Log Dictionary    ${fields}
            Set Field Value    Given Name Text Box    Mark
            Save Field Values    output_path=${OUTPUT_DIR}${/}completed-form.pdf
            ...                  use_appearances_writer=${True}

    .. code-block:: python

        from RPA.PDF import PDF
        from robot.libraries.String import String

        pdf = PDF()
        string = String()

        def extract_data_from_first_page():
            text = pdf.get_text_from_pdf("report.pdf")
            lines = string.get_lines_matching_regexp(text[1], ".+pain.+")
            print(lines)

        def get_invoice_number():
            pdf.open_pdf("invoice.pdf")
            matches = pdf.find_text("Invoice Number")
            for match in matches:
                print(match)

        def fill_form_fields():
            pdf.switch_to_pdf("form.pdf")
            fields = pdf.get_input_fields(encoding="utf-16")
            for key, value in fields.items():
                print(f"{key}: {value}")
            pdf.set_field_value("Given Name Text Box", "Mark")
            pdf.save_field_values(
                output_path="completed-form.pdf",
                use_appearances_writer=True
            )
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.documents: Dict[str, Document] = {}
        self.active_pdf_document = None
        self.convert_settings = {}

        # Register keyword libraries to LibCore
        libraries = [
            DocumentKeywords(self),
            FinderKeywords(self),
            ModelKeywords(self),
        ]
        super().__init__(libraries)

        listener = RobotLogListener()
        listener.register_protected_keywords(["RPA.PDF.Decrypt PDF"])

        logging.getLogger("pdfminer").setLevel(logging.WARNING)
