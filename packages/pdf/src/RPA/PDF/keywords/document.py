import imghdr
import io
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Union

import pdfminer
import pypdf
from fpdf import FPDF, HTMLMixin
from pdfminer.image import ImageWriter
from pdfminer.layout import LTImage
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from PIL import Image
from robot.libraries.BuiltIn import BuiltIn

from RPA.PDF.keywords import LibraryContext, keyword
from RPA.PDF.keywords.model import Document, Figure, RobocorpPdfReader


FilePath = Union[str, Path]
PagesType = Union[int, str, List[int], List[str], None]

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def get_output_dir() -> Path:
    try:
        # A `None` may come from here too.
        output_dir = BuiltIn().get_variable_value("${OUTPUT_DIR}")
    except Exception:  # pylint: disable=broad-except
        output_dir = None
    # Keep empty string as current working directory path.
    if output_dir is None:
        output_dir = "output"

    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


class PDF(FPDF, HTMLMixin):
    """
    FDPF helper class.

    Note that we are using FDPF2, which is a maintained fork of FPDF
    https://github.com/PyFPDF/fpdf2
    """

    FONT_PATHS = {
        "": ASSETS_DIR / "Inter-Regular.ttf",
        "B": ASSETS_DIR / "Inter-Bold.ttf",
        "I": ASSETS_DIR / "Inter-Italic.ttf",
        "BI": ASSETS_DIR / "Inter-BoldItalic.ttf",
    }

    def add_unicode_fonts(self):
        for style, path in self.FONT_PATHS.items():
            self.add_font("Inter", style=style, fname=str(path))
        self.set_font("Inter")


class DocumentKeywords(LibraryContext):
    """Keywords for basic PDF operations"""

    ENCODING = "utf-8"

    @staticmethod
    def resolve_input(path: FilePath) -> str:
        """Normalizes input path and returns as string."""
        inp = Path(path)
        inp = inp.expanduser().resolve()
        return str(inp)

    @staticmethod
    def resolve_output(path: Optional[FilePath] = None) -> str:
        """Normalizes output path and returns as string."""
        if path is None:
            output = get_output_dir() / "output.pdf"
        else:
            output = Path(path)

        output = output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        return str(output)

    @keyword
    def close_all_pdfs(self) -> None:
        """Close all opened PDF file descriptors.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Close Multiple PDFs
                Close all pdfs
        """
        file_paths = list(self.ctx.documents.keys())
        for filename in file_paths:
            self.close_pdf(filename)

    @keyword
    def close_pdf(self, source_pdf: str = None) -> None:
        """Close PDF file descriptor for a certain file.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Close just one pdf
                Close pdf   path/to/the/pdf/file.pdf

        :param source_pdf: filepath to the source pdf.
        :raises ValueError: if file descriptor for the file is not found.
        """
        if not source_pdf:
            if self.active_pdf_document:
                source_pdf = self.active_pdf_document.path
            else:
                raise ValueError("No active PDF document open")

        source_pdf = str(source_pdf)
        if source_pdf not in self.ctx.documents:
            raise ValueError(f"PDF {source_pdf!r} is not open")

        self.logger.info("Closing PDF document: %s", source_pdf)
        self.ctx.documents[source_pdf].close()
        del self.ctx.documents[source_pdf]
        self.active_pdf_document = None

    @keyword
    def open_pdf(self, source_path: FilePath) -> None:
        """Open a PDF document for reading.

        This is called automatically in the other PDF keywords
        when a path to the PDF file is given as an argument.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Open my pdf file
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
        if not source_path:
            raise ValueError("Source PDF is missing")

        source_path = self.resolve_input(source_path)
        if source_path in self.ctx.documents:
            raise ValueError(
                "PDF file is already open, please close it before opening it again"
            )

        self.logger.debug("Opening new document: %s", source_path)
        # pylint: disable=consider-using-with
        self.active_pdf_document = self.ctx.documents[source_path] = Document(
            source_path, fileobject=open(source_path, "rb")
        )

    @keyword
    def template_html_to_pdf(
        self,
        template: str,
        output_path: str,
        variables: dict = None,
        encoding: str = ENCODING,
    ) -> None:
        """Use HTML template file to generate PDF file.

        It provides an easy method of generating a PDF document from an HTML formatted
        template file.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Create PDF from HTML template
                ${TEMPLATE}=    Set Variable    order.template
                ${PDF}=         Set Variable    result.pdf
                &{DATA}=        Create Dictionary
                ...             name=Robot Generated
                ...             email=robot@domain.com
                ...             zip=00100
                ...             items=Item 1, Item 2
                Template HTML to PDF
                ...    template=${TEMPLATE}
                ...    output_path=${PDF}
                ...    variables=${DATA}

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

        :param template: Filepath to the HTML template.
        :param output_path: Filepath where to save PDF document.
        :param variables: Dictionary of variables to fill into template, defaults to {}.
        :param encoding: Codec used for text I/O.
        """
        variables = variables or {}

        with open(template, "r", encoding=encoding or self.ENCODING) as templatefile:
            html = templatefile.read()
        for key, value in variables.items():
            html = html.replace("{{" + key + "}}", str(value))

        self.html_to_pdf(html, output_path, encoding=encoding)

    @keyword
    def html_to_pdf(
        self,
        content: str,
        output_path: str,
        encoding: str = ENCODING,
    ) -> None:
        """Generate a PDF file from HTML content.

        Note that input must be well-formed and valid HTML.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Create PDF from HTML
                HTML to PDF    ${html_content_as_string}  /tmp/output.pdf

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def create_pdf_from_html():
                pdf.html_to_pdf(html_content_as_string, "/tmp/output.pdf")

        :param content: HTML content.
        :param output_path: Filepath where to save the PDF document.
        :param encoding: Codec used for text I/O.
        """
        output_path = self.resolve_output(output_path)
        self.logger.info("Writing output to file %s", output_path)

        fpdf = PDF()
        # Support unicode content with a font capable of rendering it.
        fpdf.core_fonts_encoding = encoding
        fpdf.add_unicode_fonts()
        fpdf.set_margin(0)
        fpdf.add_page()
        fpdf.write_html(content)
        fpdf.output(name=output_path)

    @keyword
    def get_pdf_info(self, source_path: str = None) -> dict:
        """Get metadata from a PDF document.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Get PDF metadata
                ${metadata}=    Get PDF Info    /tmp/sample.pdf

            *** Keywords ***
            Get metadata from an already opened PDF
                ${metadata}=    Get PDF Info

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def get_pdf_metadata():
                metadata = pdf.get_pdf_info("/tmp/sample.pdf")

        :param source_path: filepath to the source PDF.
        :return: dictionary of PDF information.
        """
        self.switch_to_pdf(source_path)

        reader = self.active_pdf_document.reader
        docinfo = reader.metadata
        num_pages = self.pages_count

        parser = PDFParser(self.active_pdf_document.fileobject)
        document = PDFDocument(parser)
        try:
            fields = pdfminer.pdftypes.resolve1(document.catalog["AcroForm"])["Fields"]
        except KeyError:
            fields = None

        optional = (
            lambda attr: getattr(docinfo, attr) if docinfo is not None else None
        )  # noqa
        return {
            "Author": optional("author"),
            "Creator": optional("creator"),
            "Producer": optional("producer"),
            "Subject": optional("subject"),
            "Title": optional("title"),
            "Pages": num_pages,
            "Encrypted": self.is_pdf_encrypted(source_path),
            "Fields": bool(fields),
        }

    @keyword
    def is_pdf_encrypted(self, source_path: str = None) -> bool:
        """Check if PDF is encrypted.

        If no source path given, assumes a PDF is already opened.

        :param source_path: filepath to the source pdf.
        :return: True if file is encrypted.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Is PDF encrypted
                ${is_encrypted}=    Is PDF Encrypted    /tmp/sample.pdf

            *** Keywords ***
            Is open PDF encrypted
                ${is_encrypted}=    Is PDF Encrypted

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                is_encrypted = pdf.is_pdf_encrypted("/tmp/sample.pdf")
        """
        self.switch_to_pdf(source_path)
        reader = self.active_pdf_document.reader
        return reader.is_encrypted

    @keyword
    def get_number_of_pages(self, source_path: str = None) -> int:
        """Get number of pages in the document.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Number of pages in PDF
                ${page_count}=    Get Number Of Pages    /tmp/sample.pdf

            Number of pages in opened PDF
                ${page_count}=    Get Number Of Pages

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def number_of_pages_in_pdf():
                page_count = pdf.get_number_of_pages("/tmp/sample.pdf")

        :param source_path: filepath to the source pdf
        :raises PdfReadError: if file is encrypted or other restrictions are in place
        """
        self.switch_to_pdf(source_path)
        reader = self.active_pdf_document.reader
        return len(reader.pages)

    @keyword
    def switch_to_pdf(self, source_path: Optional[FilePath] = None) -> None:
        """Switch library's current fileobject to already opened file
        or open a new file if not opened.

        This is done automatically in the PDF library keywords.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Jump to another PDF
                Switch to PDF    /tmp/another.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def jump_to_another_pdf():
                pdf.switch_to_pdf("/tmp/sample.pdf")


        :param source_path: filepath to the source pdf.
        :raises ValueError: if PDF filepath is not given and there are no active
            file to activate.
        """
        if not source_path:
            if not self.active_pdf_document:
                raise ValueError("No PDF is open")
            self.logger.debug(
                "Using already set document: %s", self.active_pdf_document.path
            )
            return

        source_path = self.resolve_input(source_path)
        if source_path not in self.ctx.documents:
            self.open_pdf(source_path)
        elif self.ctx.documents[source_path] != self.active_pdf_document:
            self.logger.debug("Switching to already opened document: %s", source_path)
            self.active_pdf_document = self.ctx.documents[source_path]
        else:
            self.logger.debug("Using already set document: %s", source_path)

    @keyword
    def get_text_from_pdf(
        self,
        source_path: str = None,
        pages: PagesType = None,
        details: bool = False,
        trim: bool = True,
    ) -> dict:
        """Get text from set of pages in source PDF document.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Text extraction from PDF
                ${text}=    Get Text From PDF    /tmp/sample.pdf

            Text extraction from open PDF
                ${text}=    Get Text From PDF

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def text_extraction_from_pdf():
                text = pdf.get_text_from_pdf("/tmp/sample.pdf")


        :param source_path: filepath to the source pdf.
        :param pages: page numbers to get text (numbers start from 1).
        :param details: set to `True` to return textboxes, default `False`.
        :param trim: set to `False` to return raw texts, default `True`
            means whitespace is trimmed from the text
        :return: dictionary of pages and their texts.
        """
        self.switch_to_pdf(source_path)
        self.ctx.convert(trim=trim)

        reader = self.active_pdf_document.reader
        pages = self._get_page_numbers(pages, reader)
        pdf_text = {}
        for idx, page in self.active_pdf_document.get_pages().items():
            if page.pageid not in pages:
                continue
            pdf_text[idx] = [] if details else ""
            for _, item in page.textboxes.items():
                if details:
                    pdf_text[idx].append(item)
                else:
                    pdf_text[idx] += item.text
        return pdf_text

    @keyword
    def extract_pages_from_pdf(
        self,
        source_path: str = None,
        output_path: str = None,
        pages: PagesType = None,
    ) -> None:
        """Extract pages from source PDF and save to a new PDF document.

        Page numbers start from 1.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Save PDF pages to a new document
                ${pages}=    Extract Pages From PDF
                ...          source_path=/tmp/sample.pdf
                ...          output_path=/tmp/output.pdf
                ...          pages=5

            Save PDF pages from open PDF to a new document
                ${pages}=    Extract Pages From PDF
                ...          output_path=/tmp/output.pdf
                ...          pages=5

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def save_pdf_pages_to_a_new_document():
                pages = pdf.extract_pages_from_pdf(
                    source_path="/tmp/sample.pdf",
                    output_path="/tmp/output.pdf",
                    pages=5
                )

        :param source_path: filepath to the source pdf.
        :param output_path: filepath to the target pdf, stored by default
            in the robot output directory as ``output.pdf``
        :param pages: page numbers to extract from PDF (numbers start from 1)
            if None then extracts all pages.
        """
        self.switch_to_pdf(source_path)
        reader = self.active_pdf_document.reader
        writer = pypdf.PdfWriter()

        output_path = self.resolve_output(output_path)

        pages: List[int] = self._get_page_numbers(pages, reader)  # 1-indexed
        for page_nr in pages:
            writer.add_page(reader.pages[page_nr - 1])
        with open(output_path, "wb") as stream:
            writer.write(stream)

    @keyword
    def rotate_page(
        self,
        pages: PagesType,
        source_path: Optional[str] = None,
        output_path: Optional[str] = None,
        clockwise: bool = True,
        angle: int = 90,
    ) -> None:
        """Rotate pages in source PDF document and save to target PDF document.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            PDF page rotation
                Rotate Page
                ...          source_path=/tmp/sample.pdf
                ...          output_path=/tmp/output.pdf
                ...          pages=5

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def pdf_page_rotation():
                pages = pdf.rotate_page(
                    source_path="/tmp/sample.pdf",
                    output_path="/tmp/output.pdf",
                    pages=5
                )

        :param pages: page numbers to extract from PDF (numbers start from 1).
        :param source_path: filepath to the source pdf.
        :param output_path: filepath to the target pdf, stored by default
            in the robot output directory as ``output.pdf``
        :param clockwise: directorion that page will be rotated to, default True.
        :param angle: number of degrees to rotate, default 90.
        """
        # TODO: don't save to a new file every time
        self.switch_to_pdf(source_path)
        reader = self.active_pdf_document.reader
        writer = pypdf.PdfWriter()

        output_path = self.resolve_output(output_path)

        angle = int(angle) * (1 if clockwise else -1)
        pages = self._get_page_numbers(pages, reader)
        for page, source_page in enumerate(reader.pages):
            if page + 1 in pages:
                source_page.rotate(angle)
            writer.add_page(source_page)
        with open(output_path, "wb") as stream:
            writer.write(stream)

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

            *** Keywords ***
            Secure this PDF
                Encrypt PDF    /tmp/sample.pdf

            Secure this PDF and set passwords
                Encrypt PDF
                ...    source_path=/tmp/sample.pdf
                ...    output_path=/tmp/new/sample_encrypted.pdf
                ...    user_pwd=complex_password_here
                ...    owner_pwd=different_complex_password_here
                ...    use_128bit=${TRUE}

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def secure_this_pdf():
                pdf.encrypt_pdf("/tmp/sample.pdf")

        :param source_path: filepath to the source pdf.
        :param output_path: filepath to the target pdf, stored by default
            in the robot output directory as ``output.pdf``
        :param user_pwd: allows opening and reading PDF with restrictions.
        :param owner_pwd: allows opening PDF without any restrictions, by
            default same `user_pwd`.
        :param use_128bit: whether to 128bit encryption, when false 40bit
            encryption is used, default True.
        """
        # TODO: don't save to a new file every time
        self.switch_to_pdf(source_path)
        reader = self.active_pdf_document.reader

        output_path = self.resolve_output(output_path)

        if owner_pwd is None:
            owner_pwd = user_pwd
        writer = pypdf.PdfWriter()
        writer.append_pages_from_reader(reader)
        writer.encrypt(user_pwd, owner_pwd, use_128bit)
        with open(output_path, "wb") as f:
            writer.write(f)

    @keyword
    def decrypt_pdf(self, source_path: str, output_path: str, password: str) -> bool:
        """Decrypt PDF with password.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Make PDF human readable
                ${success}=  Decrypt PDF    /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def make_pdf_human_readable():
                success = pdf.decrypt_pdf("/tmp/sample.pdf")

        :param source_path: filepath to the source pdf.
        :param output_path: filepath to the decrypted pdf.
        :param password: password as a string.
        :return: True if decrypt was successful, else False or Exception.
        :raises ValueError: on decryption errors.
        """
        self.switch_to_pdf(source_path)
        reader = self.active_pdf_document.reader
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

            output_path = self.resolve_output(output_path)
            self.save_pdf(output_path, reader)
            return True

        except NotImplementedError as e:
            raise ValueError(
                f"Document {source_path!r} uses an unsupported encryption method"
            ) from e
        except KeyError:
            self.logger.info("PDF is not encrypted")
            return False

    @keyword
    def get_all_figures(self, source_path: str = None) -> dict:
        """Return all figures in the PDF document.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Image fetch
                &{figures}=  Get All Figures    /tmp/sample.pdf

            Image fetch from open PDF
                &{figures}=  Get All Figures

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def image_fetch():
                figures = pdf.get_all_figures("/tmp/sample.pdf")

        :param source_path: filepath to the source pdf.
        :return: dictionary of figures divided into pages.
        """
        self.switch_to_pdf(source_path)
        self.ctx.convert()
        pages = {}
        for pagenum, page in self.active_pdf_document.get_pages().items():
            pages[pagenum] = page.figures
        return pages

    @keyword
    def add_watermark_image_to_pdf(
        self,
        image_path: FilePath,
        output_path: FilePath,
        source_path: Optional[FilePath] = None,
        coverage: float = 0.2,
    ) -> None:
        """Add an image into an existing or new PDF.

        If no source path is given, assume a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Indicate approved with watermark
                Add Watermark Image To PDF
                ...             image_path=approved.png
                ...             source_path=/tmp/sample.pdf
                ...             output_path=output/output.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def indicate_approved_with_watermark():
                pdf.add_watermark_image_to_pdf(
                    image_path="approved.png"
                    source_path="/tmp/sample.pdf"
                    output_path="output/output.pdf"
                )

        :param image_path: filepath to image file to add into PDF
        :param source: filepath to source, if not given add image to currently
            active PDF
        :param output_path: filepath of target PDF
        :param coverage: how the watermark image should be scaled on page,
         defaults to 0.2
        """
        # Ensure an active input PDF.
        self.switch_to_pdf(source_path)
        input_reader = self.active_pdf_document.reader

        # Set image boundaries.
        mediabox = input_reader.pages[0].mediabox
        img_obj = Image.open(image_path)
        max_width = int(float(mediabox.width) * coverage)
        max_height = int(float(mediabox.height) * coverage)
        img_width, img_height = self.fit_dimensions_to_box(
            *img_obj.size, max_width, max_height
        )

        # Put the image on the first page of a temporary PDF file, so we can merge this
        #  PDF formatted image page with every single page of the targeted PDF.
        # NOTE(cmin764): Keep the watermark image PDF reader open along the entire
        #  process, so the final PDF gets rendered correctly)
        with tempfile.TemporaryFile(suffix=".pdf") as temp_img_pdf:
            # Save image in temporary PDF using FPDF.
            pdf = FPDF()
            pdf.add_page()
            pdf.image(name=image_path, x=40, y=60, w=img_width, h=img_height)
            pdf.output(name=temp_img_pdf)

            # Get image page from temporary PDF using pypdf. (compatible with the
            # writer)
            img_pdf_reader = RobocorpPdfReader(temp_img_pdf)
            watermark_page = img_pdf_reader.pages[0]

            # Write the merged pages of source PDF into the destination one.
            output_writer = pypdf.PdfWriter()
            for page in input_reader.pages:
                page.merge_page(watermark_page)
                output_writer.add_page(page)

            # Since the input PDF can be the same with the output, make sure we close
            #  the input stream after writing into an auxiliary buffer. (if the input
            #  stream is closed before writing, then the writing is incomplete; and we
            #  can't read and write at the same time into the same file, that's why we
            #  use an auxiliary buffer)
            output_buffer = io.BytesIO()
            output_writer.write(output_buffer)
            self.active_pdf_document.close()
            output_path = self.resolve_output(output_path)
            with open(output_path, "wb") as output_stream:
                output_stream.write(output_buffer.getvalue())

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
        output_path: str,
        reader: RobocorpPdfReader,
    ):
        """Save the contents of a pypdf reader to a new file.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Save changes to PDF
                Save PDF    /tmp/output.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def save_changes_to_pdf():
                pdf.save_pdf(output_path="output/output.pdf")

        :param output_path: filepath to target PDF
        :param reader: a pypdf reader
        """
        writer = pypdf.PdfWriter()
        for page in reader.pages:
            try:
                writer.add_page(page)
            except Exception as exc:  # pylint: disable=W0703
                self.logger.warning(repr(exc))
                raise

        output_path = self.resolve_output(output_path)
        with open(output_path, "wb") as stream:
            writer.write(stream)

    @staticmethod
    def _get_page_numbers(
        pages: PagesType = None, reader: Optional[RobocorpPdfReader] = None
    ) -> List[int]:
        """Resolve page numbers argument to a list of 1-indexed integer pages."""
        if not pages and not reader:
            raise ValueError("Need a reader instance or explicit page numbers")

        if pages and isinstance(pages, str):
            pages = pages.split(",")
        elif pages and isinstance(pages, int):
            pages = [pages]
        elif reader and not pages:
            pages = range(1, len(reader.pages) + 1)

        return list(map(int, pages))

    @keyword
    def save_figure_as_image(
        self, figure: Figure, images_folder: str = ".", file_prefix: str = ""
    ) -> Optional[str]:
        """Try to save the image data from Figure object, and return
        the file name, if successful.

        Figure needs to have byte `stream` and that needs to be recognized
        as image format for successful save.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Figure to Image
                ${image_file_path} =     Save figure as image
                ...             figure=pdf_figure_object
                ...             images_folder=/tmp/images
                ...             file_prefix=file_name_here

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def figure_to_image():
                image_file_path = pdf.save_figure_as_image(
                    figure="pdf_figure_object"
                    images_folder="/tmp/images"
                    file_prefix="file_name_here"
                )

        :param figure: PDF Figure object which will be saved as an image.
         The PDF Figure object can be determined from the `Get All Figures` keyword
        :param images_folder: directory where image files will be created
        :param file_prefix: image filename prefix
        :return: image filepath or None
        """
        result = None
        images_folder = Path(images_folder)
        lt_image = figure.item
        if hasattr(lt_image, "stream") and lt_image.stream:
            file_stream = lt_image.stream.get_rawdata()
            file_ext = imghdr.what("", file_stream)
            if file_ext:
                filename = "".join([str(file_prefix), lt_image.name, ".", file_ext])
                imagepath = images_folder / filename
                with open(imagepath, "wb") as fout:
                    fout.write(file_stream)
                    result = str(imagepath)
            elif isinstance(lt_image, LTImage):
                img_writer = ImageWriter(images_folder)
                filename = img_writer.export_image(lt_image)
                src = images_folder / filename
                if file_prefix:
                    dest = images_folder / f"{file_prefix}{filename}"
                    os.rename(src, dest)
                    src = dest
                result = str(src)
            else:
                self.logger.info("Unable to determine image type for a figure")
        else:
            self.logger.info(
                "Image object does not have stream and can't be saved as an image"
            )
        return result

    @keyword
    def save_figures_as_images(
        self,
        source_path: Optional[str] = None,
        images_folder: str = ".",
        pages: Optional[str] = None,
        file_prefix: str = "",
    ) -> List[str]:
        """Save figures from given PDF document as image files.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Figures to Images
                ${image_filenames} =    Save figures as images
                ...             source_path=/tmp/sample.pdf
                ...             images_folder=/tmp/images
                ...             pages=${4}
                ...             file_prefix=file_name_here

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def figures_to_images():
                image_filenames = pdf.save_figures_as_image(
                    source_path="/tmp/sample.pdf"
                    images_folder="/tmp/images"
                    pages=4
                    file_prefix="file_name_here"
                )

        :param source_path: filepath to PDF document
        :param images_folder: directory where image files will be created
        :param pages: target figures in the pages, can be single page or range,
            default `None` means that all pages are scanned for figures to save
            (numbers start from 1)
        :param file_prefix: image filename prefix
        :return: list of image filenames created
        """
        figures = self.get_all_figures(source_path)
        pagecount = self.get_number_of_pages(source_path)
        page_list = self._get_pages(pagecount, pages)
        image_files = []
        for n in page_list:
            for _, figure in figures[n].items():
                image_file = self.save_figure_as_image(
                    figure, images_folder, file_prefix
                )
                if image_file:
                    image_files.append(image_file)
        return image_files

    @keyword
    def add_files_to_pdf(
        self, files: list = None, target_document: str = None, append: bool = False
    ) -> None:
        """Add images and/or pdfs to new PDF document

        Image formats supported are JPEG, PNG and GIF.

        The file can be added with extra properties by
        denoting `:` at the end of the filename. Each
        property should be separated by comma.

        Supported extra properties for PDFs are:

        - page and/or page ranges
        - no extras means that all source PDF pages are added
          into new PDF

        Supported extra properties for images are:

        - format, the PDF page format, for example. Letter or A4
        - rotate, how many degrees image is rotated counter-clockwise
        - align, only possible value at the moment is center
        - orientation, the PDF page orientation for the image, possible
          values P (portrait) or L (landscape)
        - x/y, coordinates for adjusting image position on the page

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keywords ***
            Add files to pdf
                ${files}=    Create List
                ...    ${TESTDATA_DIR}${/}invoice.pdf
                ...    ${TESTDATA_DIR}${/}approved.png:align=center
                ...    ${TESTDATA_DIR}${/}robot.pdf:1
                ...    ${TESTDATA_DIR}${/}approved.png:x=0,y=0
                ...    ${TESTDATA_DIR}${/}robot.pdf:2-10,15
                ...    ${TESTDATA_DIR}${/}approved.png
                ...    ${TESTDATA_DIR}${/}landscape_image.png:rotate=-90,orientation=L
                ...    ${TESTDATA_DIR}${/}landscape_image.png:format=Letter
                Add Files To PDF    ${files}    newdoc.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            list_of_files = [
                'invoice.pdf',
                'approved.png:align=center',
                'robot.pdf:1',
                'approved.png:x=0,y=0',
            ]
            def example_keyword():
                pdf.add_files_to_pdf(
                    files=list_of_files,
                    target_document="output/output.pdf"
                )

        :param files: list of filepaths to add into PDF (can be either images or PDFs)
        :param target_document: filepath of target PDF
        :param append: appends files to existing document if `append` is `True`
        """
        writer = pypdf.PdfWriter()

        if append:
            self._add_pages_to_writer(writer, target_document)

        for f in files:
            file_to_add = Path(f)
            namesplit = file_to_add.name.rsplit(":", 1)
            basename = namesplit[0]
            parameters = namesplit[1] if len(namesplit) == 2 else None
            file_to_add = file_to_add.parent / basename
            image_filetype = imghdr.what(str(file_to_add))
            self.logger.info("File %s type: %s", str(file_to_add), image_filetype)
            if basename.lower().endswith(".pdf"):
                reader = RobocorpPdfReader(str(file_to_add), strict=False)
                pages = self._get_pages(len(reader.pages), parameters)
                for page_nr in pages:
                    try:
                        # Because is 1-offset with `_get_pages()`.
                        page = reader.pages[page_nr - 1]
                        writer.add_page(page)
                    except IndexError:
                        self.logger.warning(
                            "File %s does not have page %d", file_to_add, page_nr
                        )
            elif image_filetype in ["png", "jpg", "jpeg", "gif"]:
                temp_pdf = os.path.join(tempfile.gettempdir(), "temp.pdf")
                settings = self._get_image_settings(str(file_to_add), parameters)
                if settings["format"]:
                    pdf = FPDF(
                        format=settings["format"], orientation=settings["orientation"]
                    )
                else:
                    pdf = FPDF(orientation=settings["orientation"])
                pdf.add_page()
                pdf.image(
                    name=settings["name"],
                    x=settings["x"],
                    y=settings["y"],
                    w=settings["width"],
                    h=settings["height"],
                )
                pdf.output(name=temp_pdf)

                reader = RobocorpPdfReader(temp_pdf)
                writer.add_page(reader.pages[0])

        with open(target_document, "wb") as f:
            writer.write(f)

    def _add_pages_to_writer(self, writer, target_document):
        if not Path(target_document).exists():
            self.logger.warn(
                "Trying to append files to document '%s' which does not exist."
                "Creating document instead." % target_document
            )
        else:
            reader = RobocorpPdfReader(str(target_document), strict=False)
            for idx, page in enumerate(reader.pages):
                self.logger.info("Adding page: %s", idx)
                writer.add_page(page)

    @staticmethod
    def _get_pages(pagecount: int, page_reference: Optional[str]) -> List[int]:
        """Returns a flattened list of pages based on provided 1-indexed ranges."""
        page_reference = page_reference or f"1-{pagecount}"
        temp = [
            (lambda sub: range(sub[0], sub[-1] + 1))(
                list(map(int, ele.strip().split("-")))
            )
            for ele in page_reference.split(",")
        ]
        return [b for a in temp for b in a]

    def _get_image_settings(self, imagepath, parameters):
        if isinstance(parameters, str):
            image_parameters = (
                dict(ele.lower().strip().split("=") for ele in parameters.split(","))
                if parameters
                else {}
            )
        else:
            image_parameters = parameters or {}
        self.logger.info("Image parameters: %s" % image_parameters)
        settings = {
            "x": int(image_parameters.get("x", 10)),
            "y": int(image_parameters.get("y", 10)),
            "format": image_parameters.get("format", None),
            "orientation": str(image_parameters.get("orientation", "P")).upper(),
            "width": None,
            "height": None,
            "name": imagepath,
        }
        rotate = image_parameters.get("rotate", None)
        align = image_parameters.get("align", None)

        max_width = 188 if settings["orientation"] == "P" else 244
        max_height = 244 if settings["orientation"] == "P" else 188

        im = Image.open(settings["name"])

        if rotate:
            rotate = int(rotate)
            file_ext = Path(settings["name"]).suffix
            temp_image = os.path.join(tempfile.gettempdir(), f"temp{file_ext}")
            rotated = im.rotate(rotate, expand=True)
            rotated.save(temp_image)
            settings["name"] = temp_image
            del image_parameters["rotate"]
            im.close()
            rotated.close()
            return self._get_image_settings(temp_image, image_parameters)
        elif align and align == "center":
            width, height = self.fit_dimensions_to_box(*im.size, max_width, max_height)
            settings["width"] = width
            settings["height"] = height
            settings["x"] = int((max_width / 2) - (width / 2)) + 10
            settings["y"] = int((max_height / 2) - (height / 2)) + 10
        if not settings["width"] or not settings["height"]:
            width, height = self.fit_dimensions_to_box(*im.size, max_width, max_height)
            settings["width"] = width
            settings["height"] = height
        im.close()
        return settings
