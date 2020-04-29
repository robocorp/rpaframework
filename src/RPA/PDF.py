import logging
from pathlib import Path

from fpdf import FPDF, HTMLMixin
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
import PyPDF2
from PyPDF2.xmp import XmpInformation

from RPA.core.utils import UNDEFINED
from RPA.RobotLogListener import RobotLogListener

try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


class PDF(FPDF, HTMLMixin):
    """RPA Framework library for PDF management.
    """

    def __init__(self, outdir: str = ".") -> None:
        FPDF.__init__(self)
        HTMLMixin.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.output_directory = Path(outdir)
        self.source_pdf = None
        listener = RobotLogListener()
        listener.register_protected_keywords(["RPA.PDF.decrypt"])

    def set_output_directory(self, outdir: str = ".") -> None:
        """Set output directory where target files are saved to.

        :param outdir: output directory path, default to current directory
        """
        self.output_directory = Path(outdir)

    def get_output_directory(self) -> str:
        """Get output directory where target files are saved to.

        :return: absolute filepath as string
        """
        return str(self.output_directory)

    def set_source_document(self, source_pdf: str = None) -> None:
        """Set source PDF document for further operations.

        :param source_pdf: filepath to the source pdf
        """
        self.source_pdf = source_pdf

    def add_pages(self, pages: int = 1) -> None:
        """Adds pages into PDF documents.

        :param pages: number of pages to add, defaults to 1
        """
        for _ in range(int(pages)):
            self.add_page()

    def add_pages_to_source_document(
        self, pages: int = 1, source_pdf: str = None, target_pdf: str = None
    ) -> None:
        """Add pages into current source document

        :param pages: number of pages to add, defaults to 1
        :param source_pdf: filepath to the source pdf
        :param target_pdf: filename to the target pdf, stored by default
            to `output_directory`
        """
        source_pdf = self._validate(source_pdf, target_pdf)
        source_reader = PyPDF2.PdfFileReader(open(source_pdf, "rb"))
        source_page = source_reader.getPage(0)

        pdf_writer = PyPDF2.PdfFileWriter()
        output_filepath = Path(self.output_directory / target_pdf)
        pageobject = PyPDF2.pdf.PageObject.createBlankPage(
            None, source_page.mediaBox.getWidth(), source_page.mediaBox.getHeight()
        )
        pdf_writer.appendPagesFromReader(source_reader)
        for _ in range(int(pages)):
            pdf_writer.addPage(pageobject)
        with open(output_filepath, "wb") as f:
            pdf_writer.write(f)

    def template_html_to_pdf(
        self, template: str, filename: str, variables: dict = None
    ) -> None:
        """Use HTML template file to generate PDF file.

        :param template: filepath to HTML template
        :param filename: filepath where to save PDF document
        :param variables: dictionary of variables to fill into template, defaults to {}
        """
        variables = variables or {}

        html = ""
        self.add_pages(1)
        with open(template, "r") as templatefile:
            html = templatefile.read()
            for key, value in variables.items():
                html = html.replace("{{" + key + "}}", str(value))

        self.write_html(html)
        self.output(self.output_directory / filename)
        self.__init__()

    def get_info(self, source_pdf: str = None) -> dict:
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

    def extract_pages_from_pdf(
        self, pages: int, source_pdf: str = None, target_pdf: str = None
    ) -> None:
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
            pdf_writer.addPage(pdf_reader.getPage(int(page)))
        with open(str(output_filepath), "wb") as f:
            pdf_writer.write(f)

    def get_text_from_pdf(self, pages: int, source_pdf: str = None) -> dict:
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
            page_obj = pdf_reader.getPage(int(page))
            texts[page] = page_obj.extractText()
        return texts

    def _validate(self, source: str = UNDEFINED, target: str = UNDEFINED) -> str:
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
        self,
        pages: int,
        source_pdf: str = None,
        target_pdf: str = None,
        clockwise: bool = True,
        angle: int = 90,
    ) -> None:
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
            source_page = pdf_reader.getPage(int(page))
            if page in pagelist:
                if clockwise:
                    source_page.rotateClockwise(int(angle))
                else:
                    source_page.rotateCounterClockwise(int(angle))
            else:
                source_page = pdf_reader.getPage(int(page))
            pdf_writer.addPage(source_page)
        with open(str(output_filepath), "wb") as fh:
            pdf_writer.write(fh)

    def is_pdf_encrypted(self, source_pdf: str = None) -> bool:
        """Check if PDF is encrypted.

        Returns True even if PDF was decrypted.

        :param source_pdf: filepath to the source pdf
        :return: True if file is encrypted
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).isEncrypted

    def pdf_encrypt(
        self,
        source_pdf: str = None,
        target_pdf: str = None,
        user_pwd: str = "",
        owner_pwd: str = None,
        use_128bit: bool = True,
    ) -> None:
        """Encrypt PDF document.

        :param source_pdf: filepath to the source pdf
        :param target_pdf: filename to the target pdf, stored by default
            to `output_directory`
        :param user_pwd: allows opening and reading PDF with restrictions
        :param owner_pwd: allows opening PDF without any restrictions, by
            default same `user_pwd`
        :param use_128bit: whether to 128bit encryption, when false 40bit
            encryption is used, default True
        """
        source_pdf = self._validate(source_pdf, target_pdf)
        output_filepath = Path(self.output_directory / target_pdf)
        if owner_pwd is None:
            owner_pwd = user_pwd
        pdf_reader = PyPDF2.PdfFileReader(source_pdf)
        pdf_writer = PyPDF2.PdfFileWriter()
        pdf_writer.appendPagesFromReader(pdf_reader)
        pdf_writer.encrypt(user_pwd, owner_pwd, use_128bit)
        with open(str(output_filepath), "wb") as f:
            pdf_writer.write(f)

    def pdf_decrypt(self, source_pdf: str = None, password: str = None) -> bool:
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
        except KeyError:
            self.logger.info("PDF is not encrypted")
            return False
        return False

    def get_fields(
        self,
        source_pdf: str = None,
        target_file: str = None,
        tree: str = None,
        retval: str = None,
    ) -> dict:
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

    def get_form_text_fields(self, source_pdf: str = None) -> dict:
        """Get form text fields with textual data (inputs, dropdowns).

        :param source_pdf: filepath to the source pdf
        :return: dict of fields or None
        """
        source_pdf = self._validate(source_pdf)
        try:
            fields = PyPDF2.PdfFileReader(source_pdf).getFormTextFields()
        except TypeError:
            return None
        return fields

    def get_outlines(
        self, source_pdf: str = None, node: str = None, outlines: str = None
    ) -> list:
        """Get document outline.

        :param source_pdf: filepath to the source pdf
        :param node: source node to check for outlines
        :param outlines: ...
        :return: nested list of outlines
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).getOutlines(node, outlines)

    def get_page_layout(self, source_pdf: str = None) -> str:
        """Get page layout setting.

        :param source_pdf: filepath to the source pdf
        :return: page layout currently in use as string or None
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).getPageLayout()

    def get_page_mode(self, source_pdf: str = None) -> str:
        """Get page mode setting.

        :param source_pdf: filepath to the source pdf
        :return: page mode currently in use as string or None
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).getPageMode()

    def get_xmp_metadata(self, source_pdf: str = None) -> XmpInformation:
        """Get document XMP (Extensible Metadata Platform) data.

        :param source_pdf: filepath to the source pdf
        :return: XmpInformation object or None if no metadata was found
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).getXmpMetadata()

    def get_named_destinations(
        self, source_pdf: str = None, tree: str = None, retval: str = None
    ) -> dict:
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

    def get_number_of_pages(self, source_pdf: str = None) -> int:
        """Get number of pages in the document.

        :param source_pdf: filepath to the source pdf
        :raises PdfReadError: if file is encrypted or other restrictions are in place
        """
        source_pdf = self._validate(source_pdf)
        return PyPDF2.PdfFileReader(source_pdf).getNumPages()
