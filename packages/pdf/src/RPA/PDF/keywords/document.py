import os
import tempfile
from pathlib import Path
from typing import Any

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
    pass


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
        """Open PDF document.

        :param source_path: filepath to the source pdf
        :raises ValueError: if PDF is already open

        Also opens file for reading.
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
    def html_to_pdf(
        self,
        content: str,
        target_pdf: str,
        variables: dict = None,
    ) -> None:
        """Use HTML content to generate PDF file.

        :param content: HTML content
        :param target_pdf: filepath where to save PDF document
        :param variables: dictionary of variables to fill into template, defaults to {}
        """
        variables = variables or {}
        html = content

        for key, value in variables.items():
            html = html.replace("{{" + key + "}}", str(value))

        default_output = Path(self.output_directory / "html2pdf.pdf")
        output_path = Path(target_pdf) if target_pdf else default_output

        self._write_html_to_pdf(html, output_path)

    def _write_html_to_pdf(self, html, output_path):
        self.ctx.logger.info("Writing output to file %s", output_path)
        self._add_pages(1)
        self.fpdf.write_html(html)

        pdf_content = self.fpdf.output(dest="S")
        with open(output_path, "wb") as outfile:
            outfile.write(pdf_content)
        # self.__init__()  # TODO: what should happen here exactly?
        self.fpdf = PDF()

    def _add_pages(self, pages: int = 1) -> None:
        """Adds pages into PDF documents.

        :param pages: number of pages to add, defaults to 1
        """
        for _ in range(int(pages)):
            self.fpdf.add_page()

    @keyword
    def get_pdf_info(self, source_path: str = None) -> dict:
        """Get information from PDF document.

        Usage example:

        >>> get_info("my_document.pdf")
        {'Author': None,
         'Creator': None,
         'Encrypted': False,
         'Fields': False,
         'Pages': 9,
         'Producer': 'PyPDF2',
         'Subject': None,
         'Title': None}

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

        :param source_path: filepath to the source pdf
        :return: True if file is encrypted
        """
        self.switch_to_pdf(source_path)
        reader = PyPDF2.PdfFileReader(self.ctx.active_pdf_document.fileobject)
        return reader.isEncrypted

    @keyword
    def get_number_of_pages(self, source_path: str = None) -> int:
        """Get number of pages in the document.

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

        :param source_path: filepath
        :raises ValueError: if PDF filepath is not given and there are no active
            file to activate
        """
        if source_path and source_path not in self.ctx.fileobjects:
            return self.open_pdf(source_path)
        if not source_path and not (self.ctx.active_pdf_document or self.ctx.active_pdf_document.fileobject):
            raise ValueError("No PDF is open")
        if (
            source_path
            and self.ctx.active_pdf_document.fileobject != self.ctx.fileobjects[source_path]
        ):
            self.logger.debug("Switching to document %s", source_path)
            self.ctx.active_pdf_document.path = str(source_path)
            self.ctx.active_pdf_document.fileobject = self.ctx.fileobjects[str(source_path)]
            self.ctx.active_pdf_document.fields = None

    @keyword
    def get_text_from_pdf(
        self, source_path: str = None, pages: Any = None, details: bool = False
    ) -> dict:
        """Get text from set of pages in source PDF document.

        :param source_path: filepath to the source pdf
        :param pages: page numbers to get text (numbers start from 0)
        :param details: set to `True` to return textboxes, default `False`
        :return: dictionary of pages and their texts

        PDF needs to be parsed before text can be read.
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
        self, source_path: str = None, target_pdf: str = None, pages: Any = None
    ) -> None:
        """Extract pages from source PDF and save to target PDF document.

        Page numbers start from 1.

        :param source_path: filepath to the source pdf
        :param target_pdf: filepath to the target pdf, stored by default
            in `output_directory`
        :param pages: page numbers to extract from PDF (numbers start from 0)
            if None then extracts all pages
        """
        self.switch_to_pdf(source_path)
        reader = PyPDF2.PdfFileReader(self.ctx.active_pdf_document.fileobject)
        writer = PyPDF2.PdfFileWriter()

        default_output = Path(self.output_directory / "extracted.pdf")
        output_filepath = Path(target_pdf) if target_pdf else default_output

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
        pages: int,
        source_path: str = None,
        target_pdf: str = None,
        clockwise: bool = True,
        angle: int = 90,
    ) -> None:
        """Rotate pages in source PDF document and save to target PDF document.

        :param source_path: filepath to the source pdf
        :param target_pdf: filepath to the target pdf, stored by default
            to `output_directory`
        :param pages: page numbers to extract from PDF (numbers start from 0)
        :param clockwise: directorion that page will be rotated to, default True
        :param angle: number of degrees to rotate, default 90
        """
        self.switch_to_pdf(source_path)
        reader = PyPDF2.PdfFileReader(self.ctx.active_pdf_document.fileobject)
        writer = PyPDF2.PdfFileWriter()

        default_output = Path(self.output_directory / "rotated.pdf")
        output_filepath = Path(target_pdf) if target_pdf else default_output

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
        target_pdf: str = None,
        user_pwd: str = "",
        owner_pwd: str = None,
        use_128bit: bool = True,
    ) -> None:
        """Encrypt PDF document.

        :param source_path: filepath to the source pdf
        :param target_pdf: filepath to the target pdf, stored by default
            to `output_directory`
        :param user_pwd: allows opening and reading PDF with restrictions
        :param owner_pwd: allows opening PDF without any restrictions, by
            default same `user_pwd`
        :param use_128bit: whether to 128bit encryption, when false 40bit
            encryption is used, default True
        """
        self.switch_to_pdf(source_path)
        reader = PyPDF2.PdfFileReader(self.ctx.active_pdf_document.fileobject)

        default_output = Path(self.output_directory / "encrypted.pdf")
        output_filepath = Path(target_pdf) if target_pdf else default_output

        if owner_pwd is None:
            owner_pwd = user_pwd
        writer = PyPDF2.PdfFileWriter()
        writer.appendPagesFromReader(reader)
        writer.encrypt(user_pwd, owner_pwd, use_128bit)
        with open(str(output_filepath), "wb") as f:
            writer.write(f)

    @keyword
    def decrypt_pdf(
        self, source_path: str, target_pdf: str, password: str
    ) -> bool:
        """Decrypt PDF with password.

        :param source_path: filepath to the source pdf
        :param target_pdf: filepath to the decrypted pdf
        :param password: password as a string
        :return: True if decrypt was successful, else False or Exception
        :raises ValueError: on decryption errors
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

            self.save_pdf(source=None, target=target_pdf, custom_reader=reader)
            return True

        except NotImplementedError as e:
            raise ValueError(
                f"Document {source_path} uses an unsupported encryption method."
            ) from e
        except KeyError:
            self.logger.info("PDF is not encrypted")
            return False
        return False

    @keyword
    def replace_textbox_text(self, text: str, replace: str, source_path: str = None):
        """Replace text content of a textbox with something else in the PDF.

        :param text: this text will be replaced
        :param replace: used to replace `text`
        :raises ValueError: when no matching text found.
        """
        if source_path or self.active_pdf_document is None:
            self.ctx.convert(source_path)
        for _, page in self.active_pdf_document.get_pages().items():
            for _, textbox in page.get_textboxes().items():
                if textbox.text == text:
                    textbox.text = replace
                    return
        raise ValueError("Did not find any matching text")

    @keyword
    def get_all_figures(self, source_path: str = None) -> dict:
        """Return all figures in the PDF document.

        :return: dictionary of figures divided into pages

        PDF needs to be parsed before elements can be found.
        """
        if source_path or self.active_pdf_document is None:
            self.ctx.convert(source_path)
        pages = {}
        for pagenum, page in self.active_pdf_document.get_pages().items():
            pages[pagenum] = page.get_figures()
        return pages

    @keyword
    def add_watermark_image_to_pdf(self, imagefile, target_pdf, source=None, coverage=0.2):
        """Add image to PDF which can be new or existing PDF.

        :param imagefile: filepath to image file to add into PDF
        :param source: filepath to source, if not given add image to currently
            active PDF
        :param target: filepath of target PDF
        :param coverage: [description], defaults to 0.2
        :raises ValueError: [description]
        """
        if source is None and self.ctx.active_pdf_document.fileobject.path:
            source = self.active_pdf_path
        elif source is None and self.ctx.active_pdf_document.fileobject.path is None:
            raise ValueError("No source PDF exists")
        temp_pdf = os.path.join(tempfile.gettempdir(), "temp.pdf")
        writer = PyPDF2.PdfFileWriter()
        pdf = FPDF()
        pdf.add_page()
        reader = PyPDF2.PdfFileReader(source)
        mediabox = reader.getPage(0).mediaBox
        im = Image.open(imagefile)
        max_width = int(float(mediabox.getWidth()) * coverage)
        max_height = int(float(mediabox.getHeight()) * coverage)
        width, height = self.fit_dimensions_to_box(*im.size, max_width, max_height)

        pdf.image(name=imagefile, x=40, y=60, w=width, h=height)
        pdf.output(name=temp_pdf, dest="F")

        img = PyPDF2.PdfFileReader(temp_pdf)
        watermark = img.getPage(0)
        for n in range(reader.getNumPages()):
            page = reader.getPage(n)
            page.mergePage(watermark)
            writer.addPage(page)

        with open(target_pdf, "wb") as f:
            writer.write(f)

    @staticmethod
    def fit_dimensions_to_box(width, height, max_width, max_height):
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
        self, source: str = None, target: str = None, custom_reader: PyPDF2.PdfFileReader = None
    ):
        """Save current over itself or to `target_pdf`.

        :param source: filepath to source PDF. If not given, the active fileobject is used.
        :param target: filepath to target PDF
        :param custom_reader: a modified PDF reader.
        """
        if not custom_reader:
            self.ctx.get_input_fields(source)

        if self.ctx.active_pdf_document.fields:
            self.logger.info("Saving PDF with input fields")
            self.ctx.update_field_values(source, target, self.ctx.active_pdf_document.fields)
        else:
            self.logger.info("Saving PDF")
            self.switch_to_pdf(source)
            if custom_reader:
                reader = custom_reader
            else:
                reader = PyPDF2.PdfFileReader(self.ctx.active_pdf_document.fileobject, strict=False)
            writer = PyPDF2.PdfFileWriter()

            for i in range(reader.getNumPages()):
                page = reader.getPage(i)
                try:
                    writer.addPage(page)
                except Exception as e:  # pylint: disable=W0703
                    self.logger.warning(repr(e))
                    writer.addPage(page)

            if target is None:
                target = self.ctx.active_pdf_path
            with open(target, "wb") as f:
                writer.write(f)
