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

from RPA.core.helpers import required_param
from RPA.core.notebook import notebook_print
from RPA.PDF.keywords import (
    LibraryContext,
    keyword,
)


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

    def __del__(self):
        self.close_all_pdf_documents()

    def close_all_pdf_documents(self) -> None:
        """Close all opened PDF file descriptors."""
        for filename, fileobject in self.ctx.fileobjects.items():
            fileobject.close()
            self.logger.debug('PDF "%s" closed', filename)
        self.ctx.anchor_element = None
        self.ctx.fileobjects = {}
        self.ctx.active_pdf = None
        self.ctx.active_fileobject = None
        self.ctx.active_fields = None
        self.ctx.rpa_pdf_document = None

    @keyword
    def open_pdf_document(self, source_pdf: str = None) -> None:
        """Open PDF document.

        :param source_pdf: filepath to the source pdf
        :raises ValueError: if PDF is already open

        Also opens file for reading.
        """
        if source_pdf is None:
            raise ValueError("Source PDF is missing")
        if str(source_pdf) in self.ctx.fileobjects.keys():
            raise ValueError(
                "PDF file is already open. Please close it before opening again."
            )
        self.ctx.active_pdf = str(source_pdf)
        self.ctx.active_fileobject = open(source_pdf, "rb")
        self.ctx.active_fields = None
        self.ctx.fileobjects[source_pdf] = self.ctx.active_fileobject
        self.ctx.rpa_pdf_document = None

    @keyword
    def html_to_pdf(
        self,
        content: str = None,
        target_pdf: str = None,
        variables: dict = None,
        create_dirs: bool = True,
        exists_ok: bool = True,
    ) -> None:
        """Use HTML content to generate PDF file.

        :param content: HTML content
        :param target_pdf: filepath where to save PDF document
        :param variables: dictionary of variables to fill into template, defaults to {}
        :param create_dirs: directory structure is created if it is missing,
         default `True`
        :param exists_ok: file is overwritten if it exists, default `True`
        """
        required_param([content, target_pdf], "html_to_pdf")
        variables = variables or {}

        html = content

        for key, value in variables.items():
            html = html.replace("{{" + key + "}}", str(value))

        default_output = Path(self.output_directory / "html2pdf.pdf")
        output_filepath = Path(target_pdf) if target_pdf else default_output

        self._write_html_to_pdf(html, output_filepath, create_dirs, exists_ok)

    def _write_html_to_pdf(self, html, output_path, create_dirs, exists_ok):
        # TODO: is this needed?
        # if create_dirs:
        #     Path(output_path).resolve().parent.mkdir(parents=True, exist_ok=True)
        # if not exists_ok and Path(output_path).exists():
        #     raise FileExistsError(output_path)
        notebook_print(link=str(output_path))
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
    def get_info(self, source_pdf: str = None) -> dict:
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

        :param source_pdf: filepath to the source PDF.
        :return: dictionary of PDF information.
        """
        self.switch_to_pdf_document(source_pdf)
        pdf = PyPDF2.PdfFileReader(self.ctx.active_fileobject)
        docinfo = pdf.getDocumentInfo()
        parser = PDFParser(self.ctx.active_fileobject)
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
            "Encrypted": self.is_pdf_encrypted(source_pdf),
            "Fields": bool(fields),
        }

    @keyword
    def is_pdf_encrypted(self, source_pdf: str = None) -> bool:
        """Check if PDF is encrypted.

        Returns True even if PDF was decrypted.

        :param source_pdf: filepath to the source pdf
        :return: True if file is encrypted
        """
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.ctx.active_fileobject)
        return reader.isEncrypted

    @keyword
    def get_number_of_pages(self, source_pdf: str = None) -> int:
        """Get number of pages in the document.

        :param source_pdf: filepath to the source pdf
        :raises PdfReadError: if file is encrypted or other restrictions are in place
        """
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.ctx.active_fileobject)
        return reader.getNumPages()

    @keyword
    def switch_to_pdf_document(self, source_pdf: str = None) -> None:
        """Switch library's current fileobject to already open file
        or open file if not opened.

        :param source_pdf: filepath
        :raises ValueError: if PDF filepath is not given and there are no active
            file to activate
        """
        if source_pdf is not None and str(source_pdf) not in self.ctx.fileobjects.keys():
            self.open_pdf_document(source_pdf)
            return
        if source_pdf is None and self.ctx.active_fileobject is None:
            raise ValueError("No PDF is open")
        if (
            source_pdf is not None
            and self.ctx.active_fileobject != self.ctx.fileobjects[source_pdf]
        ):
            self.logger.debug("Switching to another open document")
            self.ctx.active_pdf = str(source_pdf)
            self.ctx.active_fileobject = self.ctx.fileobjects[str(source_pdf)]
            self.ctx.active_fields = None
            self.ctx.rpa_pdf_document = None

    @keyword
    def get_text_from_pdf(
        self, source_pdf: str = None, pages: Any = None, details: bool = False
    ) -> dict:
        """Get text from set of pages in source PDF document.

        :param source_pdf: filepath to the source pdf
        :param pages: page numbers to get text (numbers start from 0)
        :param details: set to `True` to return textboxes, default `False`
        :return: dictionary of pages and their texts

        PDF needs to be parsed before text can be read.
        """
        self.switch_to_pdf_document(source_pdf)
        if self.rpa_pdf_document is None:
            self.ctx.convert()

        if pages and not isinstance(pages, list):
            pages = pages.split(",")
        if pages is not None:
            pages = list(map(int, pages))
        pdf_text = {}
        for idx, page in self.rpa_pdf_document.get_pages().items():
            pdf_text[idx] = [] if details else ""
            for _, item in page.get_textboxes().items():
                if details:
                    pdf_text[idx].append(item)
                else:
                    pdf_text[idx] += item.text
        return pdf_text

    @keyword
    def extract_pages_from_pdf(
        self, source_pdf: str = None, target_pdf: str = None, pages: Any = None
    ) -> None:
        """Extract pages from source PDF and save to target PDF document.

        Page numbers start from 1.

        :param source_pdf: filepath to the source pdf
        :param target_pdf: filepath to the target pdf, stored by default
            in `output_directory`
        :param pages: page numbers to extract from PDF (numbers start from 0)
            if None then extracts all pages
        """
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.ctx.active_fileobject)
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
        :param target_pdf: filepath to the target pdf, stored by default
            to `output_directory`
        :param pages: page numbers to extract from PDF (numbers start from 0)
        :param clockwise: directorion that page will be rotated to, default True
        :param angle: number of degrees to rotate, default 90
        """
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.ctx.active_fileobject)
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
        :param target_pdf: filepath to the target pdf, stored by default
            to `output_directory`
        :param user_pwd: allows opening and reading PDF with restrictions
        :param owner_pwd: allows opening PDF without any restrictions, by
            default same `user_pwd`
        :param use_128bit: whether to 128bit encryption, when false 40bit
            encryption is used, default True
        """
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.ctx.active_fileobject)

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
    def pdf_decrypt(
        self, source_pdf: str, target_pdf: str, password: str
    ) -> bool:
        """Decrypt PDF with password.

        :param source_pdf: filepath to the source pdf
        :param target_pdf: filepath to the decrypted pdf
        :param password: password as a string
        :return: True if decrypt was successful, else False or Exception
        :raises ValueError: on decryption errors
        """
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.ctx.active_fileobject)
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
                f"Document {source_pdf} uses an unsupported encryption method."
            ) from e
        except KeyError:
            self.logger.info("PDF is not encrypted")
            return False
        return False

    @keyword
    def replace_textbox_text(self, text: str, replace: str, source_pdf: str = None):
        """Replace text content of a textbox with something else in the PDF.

        :param text: this text will be replaced
        :param replace: used to replace `text`
        """
        if source_pdf or self.rpa_pdf_document is None:
            self.ctx.convert(source_pdf)
        for _, page in self.rpa_pdf_document.get_pages().items():
            for _, textbox in page.get_textboxes().items():
                if textbox.text == text:
                    textbox.text = replace
                    return
        self.logger.warning("Did not find any matching text")

    @keyword
    def get_all_figures(self, source_pdf: str = None) -> dict:
        """Return all figures in the PDF document.

        :return: dictionary of figures divided into pages

        PDF needs to be parsed before elements can be found.
        """
        if source_pdf or self.rpa_pdf_document is None:
            self.ctx.convert(source_pdf)
        pages = {}
        for pagenum, page in self.rpa_pdf_document.get_pages().items():
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
        # FIXME: is this working as intended? Now it adds
        # watermark images on every page
        if source is None and self.active_pdf:
            source = self.active_pdf
        elif source is None and self.active_pdf is None:
            raise ValueError("No source PDF exists")
        temp_pdf = os.path.join(tempfile.gettempdir(), "temp.pdf")
        writer = PyPDF2.PdfFileWriter()
        pdf = FPDF()
        pdf.add_page()
        reader = PyPDF2.PdfFileReader(source)
        mediabox = reader.getPage(0).mediaBox
        im = Image.open(imagefile)
        width, height = im.size
        max_width = int(float(mediabox.getWidth()) * coverage)
        max_height = int(float(mediabox.getHeight()) * coverage)
        if width > max_width:
            width = int(max_width)
            height = int(coverage * height)
        elif height > max_height:
            height = max_height
            width = int(coverage * width)

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

        if self.ctx.active_fields:
            self.logger.info("Saving PDF with input fields")
            self.ctx.update_field_values(source, target, self.ctx.active_fields)
        else:
            self.logger.info("Saving PDF")
            self.switch_to_pdf_document(source)
            if custom_reader:
                reader = custom_reader
            else:
                reader = PyPDF2.PdfFileReader(self.ctx.active_fileobject, strict=False)
            writer = PyPDF2.PdfFileWriter()

            for i in range(reader.getNumPages()):
                page = reader.getPage(i)
                try:
                    writer.addPage(page)
                except Exception as e:  # pylint: disable=W0703
                    self.logger.warning(repr(e))
                    writer.addPage(page)

            if target is None:
                target = self.ctx.active_pdf
            with open(target, "wb") as f:
                writer.write(f)
