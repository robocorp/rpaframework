import os
import tempfile
from pathlib import Path
from typing import (
    Any,
    List,
    Tuple,
    Union,
)

import pdfminer
import PyPDF2
from fpdf import FPDF, HTMLMixin
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from PIL import Image

from RPA.PDF.keywords import (
    LibraryContext,
    keyword,
)
from .model import Document


class PDF(FPDF, HTMLMixin):
    """
    FDPF helper class.

    Note that we are using FDPF2, which is a maintained fork of FPDF
    https://github.com/PyFPDF/fpdf2
    """


class DocumentKeywords(LibraryContext):
    """Keywords for basic PDF operations"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.fpdf = PDF()
        self._output_directory = Path(".")

    @property
    def output_directory(self):
        return self._output_directory

    @output_directory.setter
    def output_directory(self, path: str):
        self.output_directory = Path(path)

    @keyword
    def open_pdf(self, source_path: str = None) -> None:
        """Open a PDF document for reading.

        This is called automatically in the other PDF keywords
        when a path to the PDF file is given as an argument.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                Open PDF    /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                metadata = pdf.open_pdf("/tmp/sample.pdf")

        :param source_path: filepath to the source pdf.
        :raises ValueError: if PDF is already open.
        """
        if source_path is None:
            raise ValueError("Source PDF is missing")
        if str(source_path) in self.ctx.fileobjects.keys():
            raise ValueError(
                "PDF file is already open. Please close it before opening again."
            )
        self.ctx.active_pdf_document = Document()
        self.ctx.active_pdf_document.path = str(source_path)
        self.ctx.active_pdf_document.fileobject = open(source_path, "rb")
        self.ctx.fileobjects[source_path] = self.ctx.active_pdf_document.fileobject

    @keyword
    def template_html_to_pdf(
        self,
        template: str,
        output_path: str,
        variables: dict = None,
    ) -> None:
        """Use HTML template file to generate PDF file.

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
            &{DATA}        name=Robot Generated
            ...            email=robot@domain.com
            ...            zip=00100
            ...            items=Item 1, Item 2

            *** Tasks ***
            Create PDF from HTML template
                Template HTML to PDF   ${TEMPLATE}  ${PDF}  ${DATA}

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            p = PDF()
            orders = ["item 1", "item 2", "item 3"]
            data = {
                "name": "Robot Process",
                "email": "robot@domain.com",
                "zip": "00100",
                "items": "<br/>".join(orders),
            }
            p.template_html_to_pdf("order.template", "order.pdf", data)

        :param template: filepath to the HTML template.
        :param output_path: filepath where to save PDF document.
        :param variables: dictionary of variables to fill into template, defaults to {}.
        """
        variables = variables or {}

        with open(template, "r") as templatefile:
            html = templatefile.read()
        for key, value in variables.items():
            html = html.replace("{{" + key + "}}", str(value))

        self.html_to_pdf(html, output_path)

    @keyword
    def html_to_pdf(
        self,
        content: str,
        output_path: str,
    ) -> None:
        """Generate a PDF file from HTML content.

        Note that input must be well-formed and valid HTML.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                HTML to PDF    ${html_content_as_string}  /tmp/output.pdf

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                pdf.html_to_pdf(html_content_as_string, "/tmp/output.pdf")

        :param content: HTML content.
        :param output_path: filepath where to save the PDF document.
        """
        default_output = Path(self.output_directory / "html2pdf.pdf")
        output_path = Path(output_path) if output_path else default_output
        self._write_html_to_pdf(content, output_path)

    def _write_html_to_pdf(self, html: str, output_path: str) -> None:
        self.logger.info("Writing output to file %s", output_path)
        self.fpdf.add_page()
        self.fpdf.write_html(html)
        self.fpdf.output(name=output_path)
        # self.__init__()  # TODO: what should happen here exactly?
        self.fpdf = PDF()

    @keyword
    def get_pdf_info(self, source_path: str = None) -> dict:
        """Get metadata from a PDF document.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                ${metadata}=    Get PDF Info    /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                metadata = pdf.get_pdf_info("/tmp/sample.pdf")

        :param source_path: filepath to the source PDF.
        :return: dictionary of PDF information.
        """
        self.switch_to_pdf(source_path)

        pdf = PyPDF2.PdfFileReader(self.ctx.active_pdf_document.fileobject)
        docinfo = pdf.getDocumentInfo()
        parser = PDFParser(self.ctx.active_pdf_document.fileobject)
        document = PDFDocument(parser)
        try:
            fields = pdfminer.pdftypes.resolve1(document.catalog["AcroForm"])["Fields"]
        except KeyError:
            fields = None

        return {
            "Author": docinfo.author,
            "Creator": docinfo.creator,
            "Producer": docinfo.producer,
            "Subject": docinfo.subject,
            "Title": docinfo.title,
            "Pages": pdf.getNumPages(),
            "Encrypted": self.is_pdf_encrypted(source_path),
            "Fields": bool(fields),
        }

    @keyword
    def is_pdf_encrypted(self, source_path: str = None) -> bool:
        """Check if PDF is encrypted.

        Returns True even if PDF was decrypted.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                ${is_encrypted}=    Is PDF Encrypted    /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                is_encrypted = pdf.is_pdf_encrypted("/tmp/sample.pdf")

        :param source_path: filepath to the source pdf.
        :return: True if file is encrypted.
        """
        # TODO: Why "Returns True even if PDF was decrypted."??
        self.switch_to_pdf(source_path)
        reader = PyPDF2.PdfFileReader(self.ctx.active_pdf_document.fileobject)
        return reader.isEncrypted

    @keyword
    def get_number_of_pages(self, source_path: str = None) -> int:
        """Get number of pages in the document.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                ${page_count}=    Get Number Of Pages    /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                page_count = pdf.get_number_of_pages("/tmp/sample.pdf")

        :param source_path: filepath to the source pdf
        :raises PdfReadError: if file is encrypted or other restrictions are in place
        """
        self.switch_to_pdf(source_path)
        reader = PyPDF2.PdfFileReader(self.ctx.active_pdf_document.fileobject)
        return reader.getNumPages()

    @keyword
    def switch_to_pdf(self, source_path: str = None) -> None:
        """Switch library's current fileobject to already open file
        or open file if not opened.

        This is done automatically in the PDF library keywords.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                Switch to PDF    /tmp/another.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                pdf.switch_to_pdf("/tmp/sample.pdf")


        :param source_path: filepath to the source pdf.
        :raises ValueError: if PDF filepath is not given and there are no active
            file to activate.
        """
        # TODO: should this be a keyword or a private method?
        if source_path and source_path not in self.ctx.fileobjects:
            self.open_pdf(source_path)
        elif not source_path and not (
            self.ctx.active_pdf_document or self.ctx.active_pdf_document.fileobject
        ):
            raise ValueError("No PDF is open")
        elif (
            source_path
            and self.ctx.active_pdf_document.fileobject
            != self.ctx.fileobjects[source_path]
        ):
            self.logger.debug("Switching to document %s", source_path)
            self.ctx.active_pdf_document.path = str(source_path)
            self.ctx.active_pdf_document.fileobject = self.ctx.fileobjects[
                str(source_path)
            ]
            self.ctx.active_pdf_document.fields = None

    @keyword
    def get_text_from_pdf(
        self, source_path: str = None, pages: Any = None, details: bool = False
    ) -> dict:
        """Get text from set of pages in source PDF document.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                ${text}=    Get Text From PDF    /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                text = pdf.get_text_from_pdf("/tmp/sample.pdf")


        :param source_path: filepath to the source pdf.
        :param pages: page numbers to get text (numbers start from 0).
        :param details: set to `True` to return textboxes, default `False`.
        :return: dictionary of pages and their texts.
        """
        self.switch_to_pdf(source_path)
        if not self.active_pdf_document.is_converted:
            self.ctx.convert()

        if pages and not isinstance(pages, list):
            pages = pages.split(",")
        if pages is not None:
            pages = list(map(int, pages))
        pdf_text = {}
        for idx, page in self.active_pdf_document.get_pages().items():
            pdf_text[idx] = [] if details else ""
            for _, item in page.get_textboxes().items():
                if details:
                    pdf_text[idx].append(item)
                else:
                    pdf_text[idx] += item.text
        return pdf_text

    @keyword
    def extract_pages_from_pdf(
        self, source_path: str = None, output_path: str = None, pages: Any = None
    ) -> None:
        """Extract pages from source PDF and save to a new PDF document.

        Page numbers start from 1.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                ${pages}=    Extract Pages From PDF
                ...          source_path=/tmp/sample.pdf
                ...          output_path=/tmp/output.pdf
                ...          pages=5

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                pages = pdf.extract_pages_from_pdf(
                    source_path="/tmp/sample.pdf",
                    output_path="/tmp/output.pdf",
                    pages=5
                )

        :param source_path: filepath to the source pdf.
        :param output_path: filepath to the target pdf, stored by default
            in `output_directory`.
        :param pages: page numbers to extract from PDF (numbers start from 0)
            if None then extracts all pages.
        """
        self.switch_to_pdf(source_path)
        reader = PyPDF2.PdfFileReader(self.ctx.active_pdf_document.fileobject)
        writer = PyPDF2.PdfFileWriter()

        default_output = Path(self.output_directory / "extracted.pdf")
        output_filepath = Path(output_path) if output_path else default_output

        if pages and not isinstance(pages, list):
            pages = pages.split(",")
        elif pages is None:
            pages = range(reader.getNumPages())
        pages = list(map(int, pages))
        for pagenum in pages:
            writer.addPage(reader.getPage(int(pagenum) - 1))
        with open(str(output_filepath), "wb") as f:
            writer.write(f)

    @keyword
    def rotate_page(
        self,
        pages: Union[List[int], int],
        source_path: str = None,
        output_path: str = None,
        clockwise: bool = True,
        angle: int = 90,
    ) -> None:
        """Rotate pages in source PDF document and save to target PDF document.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                Rotate Page
                ...          source_path=/tmp/sample.pdf
                ...          output_path=/tmp/output.pdf
                ...          pages=5

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def rotate_page():
                pages = pdf.rotate_page(
                    source_path="/tmp/sample.pdf",
                    output_path="/tmp/output.pdf",
                    pages=5
                )

        :param source_path: filepath to the source pdf.
        :param output_path: filepath to the target pdf, stored by default
            to `output_directory`.
        :param pages: page numbers to extract from PDF (numbers start from 0).
        :param clockwise: directorion that page will be rotated to, default True.
        :param angle: number of degrees to rotate, default 90.
        """
        # TODO: don't save to a new file every time
        self.switch_to_pdf(source_path)
        reader = PyPDF2.PdfFileReader(self.ctx.active_pdf_document.fileobject)
        writer = PyPDF2.PdfFileWriter()

        default_output = Path(self.output_directory / "rotated.pdf")
        output_filepath = Path(output_path) if output_path else default_output

        if not isinstance(pages, list):
            pagelist = [pages]
        else:
            pagelist = pages
        for page in range(reader.getNumPages()):
            source_page = reader.getPage(int(page))
            if page in pagelist:
                if clockwise:
                    source_page.rotateClockwise(int(angle))
                else:
                    source_page.rotateCounterClockwise(int(angle))
            else:
                source_page = reader.getPage(int(page))
            writer.addPage(source_page)
        with open(str(output_filepath), "wb") as f:
            writer.write(f)

    @keyword
    def encrypt_pdf(
        self,
        source_path: str = None,
        output_path: str = None,
        user_pwd: str = "",
        owner_pwd: str = None,
        use_128bit: bool = True,
    ) -> None:
        """Encrypt a PDF document.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                Encrypt PDF    /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                pdf.encrypt_pdf("/tmp/sample.pdf")

        :param source_path: filepath to the source pdf.
        :param output_path: filepath to the target pdf, stored by default
            to `output_directory`.
        :param user_pwd: allows opening and reading PDF with restrictions.
        :param owner_pwd: allows opening PDF without any restrictions, by
            default same `user_pwd`.
        :param use_128bit: whether to 128bit encryption, when false 40bit
            encryption is used, default True.
        """
        # TODO: don't save to a new file every time
        self.switch_to_pdf(source_path)
        reader = PyPDF2.PdfFileReader(self.ctx.active_pdf_document.fileobject)

        default_output = Path(self.output_directory / "encrypted.pdf")
        output_filepath = Path(output_path) if output_path else default_output

        if owner_pwd is None:
            owner_pwd = user_pwd
        writer = PyPDF2.PdfFileWriter()
        writer.appendPagesFromReader(reader)
        writer.encrypt(user_pwd, owner_pwd, use_128bit)
        with open(str(output_filepath), "wb") as f:
            writer.write(f)

    @keyword
    def decrypt_pdf(self, source_path: str, output_path: str, password: str) -> bool:
        """Decrypt PDF with password.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                ${success}=  Decrypt PDF    /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                success = pdf.decrypt_pdf("/tmp/sample.pdf")

        :param source_path: filepath to the source pdf.
        :param output_path: filepath to the decrypted pdf.
        :param password: password as a string.
        :return: True if decrypt was successful, else False or Exception.
        :raises ValueError: on decryption errors.
        """
        self.switch_to_pdf(source_path)
        reader = PyPDF2.PdfFileReader(self.ctx.active_pdf_document.fileobject)
        try:
            match_result = reader.decrypt(password)

            if match_result == 0:
                raise ValueError("PDF decrypt failed.")
            elif match_result == 1:
                self.logger.info("PDF was decrypted with user password.")
            elif match_result == 2:
                self.logger.info("PDF was decrypted with owner password.")
            else:
                return False

            self.save_pdf(
                source_path=None, output_path=output_path, custom_reader=reader
            )
            return True

        except NotImplementedError as e:
            raise ValueError(
                f"Document {source_path} uses an unsupported encryption metPDFhod."
            ) from e
        except KeyError:
            self.logger.info("PDF is not encrypted")
            return False
        return False

    @keyword
    def replace_textbox_text(self, old: str, new: str, source_path: str = None) -> None:
        """Replace text content of a textbox with something else in the PDF.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                Replace Textbox Text    /tmp/sample.pdf  example  my_value

        **Python**

        .. code-block:: pythonPDF

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                pdf.replace_textbox_text(
                    "/tmp/sample.pdf",
                    "example",
                    "my_value"
                )

        :param source_path: filepath to the source pdf.
        :param old: this text will be replaced.
        :param new: used to replace `old`.
        :raises ValueError: when no matching text found.
        """
        self.switch_to_pdf(source_path)
        if not self.active_pdf_document.is_converted:
            self.ctx.convert()

        for _, page in self.active_pdf_document.get_pages().items():
            for _, textbox in page.get_textboxes().items():
                if textbox.text == old:
                    textbox.text = new
                    return
        raise ValueError("Did not find any matching text")

    @keyword
    def get_all_figures(self, source_path: str = None) -> dict:
        """Return all figures in the PDF document.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                ${figures}=  Get All Figures    /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                figures = pdf.get_all_figures("/tmp/sample.pdf")

        :param source_path: filepath to the source pdf.
        :return: dictionary of figures divided into pages.
        """
        self.switch_to_pdf(source_path)
        if not self.active_pdf_document.is_converted:
            self.ctx.convert()
        pages = {}
        for pagenum, page in self.active_pdf_document.get_pages().items():
            pages[pagenum] = page.get_figures()
        return pages

    @keyword
    def add_watermark_image_to_pdf(
        self,
        image_path: str,
        output_path: str,
        source_path: str = None,
        coverage: float = 0.2,
    ) -> None:
        """Add image to PDF which can be new or existing PDF.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                Add Watermark Image To PDF
                ...             image_path=approved.png
                ...             source_path=/tmp/sample.pdf
                ...             output_path=output/output.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                pdf.add_watermark_image_to_pdf(
                    image_path="approved.png"
                    source_path="/tmp/sample.pdf"
                    output_path="output/output.pdf"
                )

        :param image_path: filepath to image file to add into PDF
        :param source: filepath to source, if not given add image to currently
            active PDF
        :param output_path: filepath of target PDF
        :param coverage: [description], defaults to 0.2
        :raises ValueError: [description]
        """
        if source_path is None and self.ctx.active_pdf_document.fileobject.path:
            source_path = self.active_pdf_document.path
        elif (
            source_path is None and self.ctx.active_pdf_document.fileobject.path is None
        ):
            raise ValueError("No source PDF exists")
        temp_pdf = os.path.join(tempfile.gettempdir(), "temp.pdf")
        writer = PyPDF2.PdfFileWriter()
        pdf = FPDF()
        pdf.add_page()
        reader = PyPDF2.PdfFileReader(source_path)
        mediabox = reader.getPage(0).mediaBox
        im = Image.open(image_path)
        max_width = int(float(mediabox.getWidth()) * coverage)
        max_height = int(float(mediabox.getHeight()) * coverage)
        width, height = self.fit_dimensions_to_box(*im.size, max_width, max_height)

        pdf.image(name=image_path, x=40, y=60, w=width, h=height)
        pdf.output(name=temp_pdf)

        img = PyPDF2.PdfFileReader(temp_pdf)
        watermark = img.getPage(0)
        for n in range(reader.getNumPages()):
            page = reader.getPage(n)
            page.mergePage(watermark)
            writer.addPage(page)

        with open(output_path, "wb") as f:
            writer.write(f)

    @staticmethod
    def fit_dimensions_to_box(
        width: int, height: int, max_width: int, max_height: int
    ) -> Tuple[int, int]:
        """
        Fit dimensions of width and height to a given box.
        """
        ratio = width / height
        if width > max_width:
            width = max_width
            height = int(width / ratio)
        if height > max_height:
            height = max_height
            width = int(ratio * height)

        if width == 0 or height == 0:
            raise ValueError("Image has invalid dimensions.")

        return width, height

    @keyword
    def save_pdf(
        self,
        source_path: str = None,
        output_path: str = None,
        custom_reader: PyPDF2.PdfFileReader = None,
    ):
        """Save current over itself or to `output_path`.

        If no source path given, assumes a PDF is already opened.

        :param source_path: filepath to source PDF.
            If not given, the active fileobject is used.
        :param output_path: filepath to target PDF
        :param custom_reader: a modified PDF reader.
        """
        if not custom_reader:
            self.ctx.get_input_fields(source_path)

        if self.ctx.active_pdf_document.fields:
            self.logger.info("Saving PDF with input fields")
            self.ctx.update_field_values(
                source_path, output_path, self.ctx.active_pdf_document.fields
            )
        else:
            self.logger.info("Saving PDF")
            self.switch_to_pdf(source_path)
            if custom_reader:
                reader = custom_reader
            else:
                reader = PyPDF2.PdfFileReader(
                    self.ctx.active_pdf_document.fileobject, strict=False
                )
            writer = PyPDF2.PdfFileWriter()

            for i in range(reader.getNumPages()):
                page = reader.getPage(i)
                try:
                    writer.addPage(page)
                except Exception as e:  # pylint: disable=W0703
                    self.logger.warning(repr(e))
                    writer.addPage(page)

            if output_path is None:
                output_path = self.ctx.active_pdf_path
            with open(output_path, "wb") as f:
                writer.write(f)
