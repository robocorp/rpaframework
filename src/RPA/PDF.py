import logging
from pathlib import Path

from fpdf import FPDF, HTMLMixin
import PyPDF2

from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from RPA.core.utils import UNDEFINED
from RPA.RobotLogListener import RobotLogListener

try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


class PDF(FPDF, HTMLMixin):
    """RPA Framework library for PDF management.
    """

    def __init__(self, outdir="."):
        FPDF.__init__(self)
        HTMLMixin.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.output_directory = Path(outdir)
        self.source_pdf = None
        listener = RobotLogListener()
        listener.register_protected_keywords(["RPA.PDF.decrypt"])

    def set_output_directory(self, outdir="."):
        """Set output directory where target files are saved to.

        :param outdir: output directory path, default to current directory
        """
        self.output_directory = Path(outdir)

    def get_output_directory(self):
        """Get output directory where target files are saved to.

        :return: absolute filepath as string
        """
        return str(self.output_directory)

    def set_source_document(self, source_pdf):
        """Set source PDF document for further operations.

        :param source_pdf: filepath to the source pdf
        """
        self.source_pdf = source_pdf

    def add_pages(self, pages=1):
        """Adds pages into PDF documents.

        :param pages: number of pages to add, defaults to 1
        """
        for _ in range(pages):
            self.add_page()

    def template_html_to_pdf(self, template, filename, variables=None):
        """Use HTML template file to generate PDF file.

        :param template: filepath to HTML template
        :param filename: filepath where to save PDF document
        :param variables: dictionary of variables to fill into template, defaults to {}
        """
        variables = variables or {}

        html = ""
        with open(template, "r") as templatefile:
            html = templatefile.read()
            for key, value in variables.items():
                html = html.replace("{{" + key + "}}", str(value))

        self.write_html(html)
        self.output(self.output_directory / filename)
        self.__init__()

    def get_info(self, source_pdf=None):
        """Get information from PDF document.

        :param source_pdf: filepath to the source pdf
        :return: dictionary of PDF information
        """
        source_pdf = self._validate(source_pdf)
        page_structure = {}

        pdf_reader = PyPDF2.PdfFileReader(source_pdf)
        info = pdf_reader.getDocumentInfo()
        page_structure["author"] = info.author
        page_structure["creator"] = info.creator
        page_structure["producer"] = info.producer
        page_structure["subject"] = info.subject
        page_structure["title"] = info.title
        page_structure["numberOfPages"] = pdf_reader.getNumPages()
        return page_structure

    def extract_pages_from_pdf(self, pages, source_pdf=None, target_pdf=None):
        """Extract pages from source PDF and save to target PDF document.

        :param source_pdf: filepath to the source pdf
        :param target_pdf: filename to the target pdf, stored by default
            to `output_directory`
        :param pages: page numbers to extract from PDF (numbers start from 0)
        """
        source_pdf = self._validate(source_pdf, target_pdf)
        pdf_writer = PyPDF2.PdfFileWriter()
        output_filepath = Path(self.output_directory / target_pdf)
        if not isinstance(pages, list):
            pagelist = [pages]
        else:
            pagelist = pages
        pdf_reader = PyPDF2.PdfFileReader(source_pdf)
        for page in pagelist:
            pdf_writer.addPage(pdf_reader.getPage(page))
        with open(str(output_filepath), "wb") as f:
            pdf_writer.write(f)

    def get_text_from_pdf(self, pages, source_pdf=None):
        """Get text from set of pages in source PDF document.

        :param source_pdf: filepath to the source pdf
        :param pages: page numbers to get text (numbers start from 0)
        :return: dictionary of pages and their texts
        """
        source_pdf = self._validate(source_pdf)
        texts = {}
        pdf_reader = PyPDF2.PdfFileReader(source_pdf)
        if not isinstance(pages, list):
            pagelist = [pages]
        else:
            pagelist = pages
        for page in pagelist:
            page_obj = pdf_reader.getPage(page)
            texts[page] = page_obj.extractText()
        return texts

    def _validate(self, source=UNDEFINED, target=UNDEFINED):
        if target is not UNDEFINED:
            if target is None:
                raise ValueError("Target filepath is missing.")
        if source is not UNDEFINED:
            if source is None and self.source_pdf is None:
                raise ValueError("Source filepath is missing.")
            elif source is None:
                source = self.source_pdf
        return source

    def page_rotate(
        self, pages, source_pdf=None, target_pdf=None, clockwise=True, angle=90
    ):
        """Rotate pages in source PDF document and save to target PDF document.

        :param source_pdf: filepath to the source pdf
        :param target_pdf: filename to the target pdf, stored by default
            to `output_directory`
        :param pages: page numbers to extract from PDF (numbers start from 0)
        :param clockwise: directorion that page will be rotated to, default True
        :param angle: number of degrees to rotate, default 90
        """
        source_pdf = self._validate(source_pdf, target_pdf)
        output_filepath = Path(self.output_directory / target_pdf)
        pdf_writer = PyPDF2.PdfFileWriter()
        pdf_reader = PyPDF2.PdfFileReader(source_pdf)
        if not isinstance(pages, list):
            pagelist = [pages]
        else:
            pagelist = pages
        for page in range(pdf_reader.getNumPages()):
            source_page = pdf_reader.getPage(page)
            if page in pagelist:
                if clockwise:
                    source_page.rotateClockwise(angle)
                else:
                    source_page.rotateCounterClockwise(angle)
            else:
                source_page = pdf_reader.getPage(page)
            pdf_writer.addPage(source_page)
        with open(str(output_filepath), "wb") as fh:
            pdf_writer.write(fh)

    def is_pdf_encrypted(self, source_pdf=None):
        """Check if PDF is encrypted.

        Returns True even if PDF was decrypted.

        :param source_pdf: filepath to the source pdf
        :return: True if file is encrypted
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).isEncrypted()

    def pdf_decrypt(self, source_pdf=None, password=None):
        """Decrypt PDF with password.

        :param source_pdf: filepath to the source pdf
        :param password: password as a string
        :return: True if decrypt was successful, else False or Exception
        :raises ValueError: on decryption errors
        """
        source_pdf = self._validate(source_pdf)
        try:
            match_result = PyPDF2.PdfFileReader(source_pdf).decrypt(password)
            if match_result == 0:
                raise ValueError("PDF decrypt failed.")
            elif match_result == 1:
                self.logger.info("PDF was decrypted with user password.")
                return True
            elif match_result == 2:
                self.logger.info("PDF was decrypted with owner password.")
                return True
        except NotImplementedError:
            raise ValueError(
                f"Document {source_pdf} uses an unsupported encryption method."
            )
        return False

    def get_fields(self, source_pdf=None, target_file=None, tree=None, retval=None):
        """Get interactive form fields from PDF source and store into target
        file in text format.

        :param source_pdf: filepath to the source pdf
        :param target_file: filepath to save field information into
        :param tree: used for recursive purposes, default is None
        :param retval:  used for recursive purposes, default is None
        :return: dict of fields or None
        """
        source_pdf = self._validate(source_pdf, target_file)
        return PyPDF2.PdfFileReader(source_pdf).getFields(
            tree=tree, retval=retval, fileobj=target_file
        )

    def get_form_text_fields(self, source_pdf=None):
        """Get form text fields with textual data (inputs, dropdowns).

        :param source_pdf: filepath to the source pdf
        :return: dict of fields or None
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).getFormTextFields()

    def get_outlines(self, source_pdf=None, node=None, outlines=None):
        """Get document outline.

        :param source_pdf: filepath to the source pdf
        :param node: source node to check for outlines
        :param outlines: ...
        :return: nested list of outlines
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).getOutlines(node, outlines)

    def get_page_layout(self, source_pdf=None):
        """Get page layout setting.

        :param source_pdf: filepath to the source pdf
        :return: page layout currently in use as string or None
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).getPageLayout()

    def get_page_mode(self, source_pdf=None):
        """Get page mode setting.

        :param source_pdf: filepath to the source pdf
        :return: page mode currently in use as string or None
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).getPageMode()

    def get_xmp_metadata(self, source_pdf=None):
        """Get document XMP (Extensible Metadata Platform) data.

        :param source_pdf: filepath to the source pdf
        :return: XmpInformation object or None if no metadata was found
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).getXmpMetadata()

    def get_named_destinations(self, source_pdf=None, tree=None, retval=None):
        """Get named destination in the document.

        :param source_pdf: filepath to the source pdf
        :param tree: used for recursive purposes, default is None
        :param retval:  used for recursive purposes, default is None
        :return: dict of destinations or None
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).getNamedDestinations(
            tree=tree, retval=retval
        )

    def get_number_of_pages(self, source_pdf=None):
        """Get number of pages in the document.

        :param source_pdf: filepath to the source pdf
        :raises PdfReadError: if file is encrypted or other restrictions are in place
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).getNumPages()
