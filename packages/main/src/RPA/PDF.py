import collections
from collections import OrderedDict
import logging
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Iterable

from fpdf import FPDF, HTMLMixin
from PIL import Image
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfpage import PDFPage

from pdfminer.layout import (
    LAParams,
    LTPage,
    LTText,
    LTTextBox,
    LTLine,
    LTRect,
    LTCurve,
    LTFigure,
    LTTextLine,
    LTTextBoxVertical,
    LTChar,
    LTImage,
    LTTextGroup,
)

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdftypes import resolve1
from pdfminer.utils import enc, bbox2str
from pdfminer.converter import PDFConverter

from PyPDF2 import PdfFileWriter, PdfFileReader
from PyPDF2.generic import NameObject, BooleanObject, IndirectObject
import PyPDF2

from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from RPA.RobotLogListener import RobotLogListener
from RPA.core.helpers import required_param
from RPA.core.notebook import notebook_print

try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


def iterable_items_to_int(bbox):
    if bbox is None:
        return list()
    return list(map(int, bbox))


logging.getLogger("pdfminer").setLevel(logging.WARNING)


class TargetObject:
    """Container for Target text box"""

    boxid: int
    bbox: tuple
    text: str


class RpaFigure:
    """Class for each LTFigure element in the PDF"""

    figure_name: str
    figure_bbox: list
    item: dict
    image_name: str

    def __init__(self, name: str, bbox: Iterable) -> None:
        self.figure_name = name
        self.figure_bbox = iterable_items_to_int(bbox)
        self.image_name = None
        self.item = None

    def set_item(self, item: Any):
        # LTImage
        self.item = item

    def details(self):
        return '<image src="%s" width="%d" height="%d" />' % (
            self.image_name,
            self.item["width"],
            self.item["height"],
        )


class RpaPdfPage:
    """Class for each PDF page"""

    bbox: list
    content: OrderedDict
    content_id: int
    pageid: str
    rotate: int

    def __init__(self, pageid: int, bbox: Iterable, rotate: int) -> None:
        self.pageid = pageid
        self.bbox = iterable_items_to_int(bbox)
        self.rotate = rotate
        self.content = collections.OrderedDict()
        self.content_id = 0

    def add_content(self, content: Any) -> None:
        self.content[self.content_id] = content
        self.content_id += 1

    def get_content(self) -> OrderedDict:
        return self.content

    def get_figures(self) -> OrderedDict:
        return {k: v for k, v in self.content.items() if isinstance(v, RpaFigure)}

    def get_textboxes(self) -> OrderedDict:
        return {k: v for k, v in self.content.items() if isinstance(v, RpaTextBox)}

    def __str__(self) -> str:
        page_as_str = '<page id="%s" bbox="%s" rotate="%d">\n' % (
            self.pageid,
            bbox2str(self.bbox),
            self.rotate,
        )
        for _, c in self.content.items():
            page_as_str += f"{c}\n"
        return page_as_str


class RpaTextBox:
    """Class for each LTTextBox element in the PDF"""

    item: dict
    textbox_bbox: list
    textbox_id: int
    textbox_wmode: str

    def __init__(self, boxid: int, bbox: Iterable, wmode: str) -> None:
        self.textbox_id = boxid
        self.textbox_bbox = iterable_items_to_int(bbox)
        self.textbox_wmode = wmode

    def set_item(self, item: Any):
        self.item = {
            "bbox": iterable_items_to_int(item.bbox),
            "text": item.get_text().strip(),
        }

    @property
    def left(self) -> Any:
        return self.bbox[0] if (self.bbox and len(self.bbox) == 4) else None

    @property
    def bottom(self) -> Any:
        return self.bbox[1] if (self.bbox and len(self.bbox) == 4) else None

    @property
    def right(self) -> Any:
        return self.bbox[2] if (self.bbox and len(self.bbox) == 4) else None

    @property
    def top(self) -> Any:
        return self.bbox[3] if (self.bbox and len(self.bbox) == 4) else None

    @property
    def boxid(self) -> int:
        return self.textbox_id

    @property
    def text(self) -> str:
        return self.item["text"]

    @text.setter
    def text(self, newtext):
        self.item["text"] = newtext

    @property
    def bbox(self) -> list:
        return self.item["bbox"]

    def __str__(self) -> str:
        return self.text


class RpaPdfDocument:
    """Class for parsed PDF document"""

    encoding: str = "utf-8"
    pages: OrderedDict
    xml_content: bytearray = bytearray()

    def __init__(self) -> None:
        self.pages = collections.OrderedDict()

    def append_xml(self, xml: bytes) -> None:
        self.xml_content += xml

    def add_page(self, page: RpaPdfPage) -> None:
        self.pages[page.pageid] = page

    def get_pages(self) -> OrderedDict:
        return self.pages

    def get_page(self, pagenum: int) -> RpaPdfPage:
        return self.pages[pagenum]

    def dump_xml(self) -> str:
        return self.xml_content.decode("utf-8")


class RPAConverter(PDFConverter):
    """Class for converting PDF into RPA classes"""

    CONTROL = re.compile("[\x00-\x08\x0b-\x0c\x0e-\x1f]")

    def __init__(
        self,
        rsrcmgr,
        codec="utf-8",
        pageno=1,
        laparams=None,
        imagewriter=None,
        stripcontrol=False,
    ):
        PDFConverter.__init__(
            self, rsrcmgr, sys.stdout, codec=codec, pageno=pageno, laparams=laparams
        )
        self.rpa_pdf_document = RpaPdfDocument()
        self.figure = None
        self.current_page = None
        self.imagewriter = imagewriter
        self.stripcontrol = stripcontrol
        self.write_header()

    def write(self, text):
        if self.codec:
            text = text.encode(self.codec)
        self.rpa_pdf_document.append_xml(text)

    def write_header(self):
        if self.codec:
            self.write('<?xml version="1.0" encoding="%s" ?>\n' % self.codec)
        else:
            self.write('<?xml version="1.0" ?>\n')
        self.write("<pages>\n")

    def write_footer(self):
        self.write("</pages>\n")

    def write_text(self, text):
        if self.stripcontrol:
            text = self.CONTROL.sub("", text)
        self.write(enc(text))

    def receive_layout(self, ltpage):  # noqa: C901 pylint: disable=R0915
        def show_group(item):
            if isinstance(item, LTTextBox):
                self.write(
                    '<textbox id="%d" bbox="%s" />\n'
                    % (item.index, bbox2str(item.bbox))
                )
            elif isinstance(item, LTTextGroup):
                self.write('<textgroup bbox="%s">\n' % bbox2str(item.bbox))
                for child in item:
                    show_group(child)
                self.write("</textgroup>\n")

        #  pylint: disable=R0912, R0915
        def render(item):
            if isinstance(item, LTPage):
                s = '<page id="%s" bbox="%s" rotate="%d">\n' % (
                    item.pageid,
                    bbox2str(item.bbox),
                    item.rotate,
                )
                self.current_page = RpaPdfPage(item.pageid, item.bbox, item.rotate)

                self.write(s)
                for child in item:
                    render(child)
                if item.groups is not None:
                    self.write("<layout>\n")
                    for group in item.groups:
                        show_group(group)
                    self.write("</layout>\n")
                self.write("</page>\n")
                self.rpa_pdf_document.add_page(self.current_page)
            elif isinstance(item, LTLine):
                s = '<line linewidth="%d" bbox="%s" />\n' % (
                    item.linewidth,
                    bbox2str(item.bbox),
                )
                self.write(s)
            elif isinstance(item, LTRect):
                s = '<rect linewidth="%d" bbox="%s" />\n' % (
                    item.linewidth,
                    bbox2str(item.bbox),
                )
                self.write(s)
            elif isinstance(item, LTCurve):
                s = '<curve linewidth="%d" bbox="%s" pts="%s"/>\n' % (
                    item.linewidth,
                    bbox2str(item.bbox),
                    item.get_pts(),
                )
                self.write(s)
            elif isinstance(item, LTFigure):
                self.figure = RpaFigure(item.name, item.bbox)
                if self.figure:
                    s = '<figure name="%s" bbox="%s">\n' % (
                        item.name,
                        bbox2str(item.bbox),
                    )
                    self.write(s)
                    for child in item:
                        if self.figure:
                            self.figure.set_item(item)
                        render(child)
                    self.write("</figure>\n")
                    self.current_page.add_content(self.figure)
                    self.figure = None
            elif isinstance(item, LTTextLine):
                self.write('<textline bbox="%s">\n' % bbox2str(item.bbox))
                for child in item:
                    render(child)
                self.write("</textline>\n")
            elif isinstance(item, LTTextBox):
                wmode = ""

                if isinstance(item, LTTextBoxVertical):
                    wmode = ' wmode="vertical"'
                s = '<textbox id="%d" bbox="%s"%s>\n' % (
                    item.index,
                    bbox2str(item.bbox),
                    wmode,
                )
                box = RpaTextBox(item.index, item.bbox, wmode)
                self.write(s)
                box.set_item(item)
                self.current_page.add_content(box)
                for child in item:
                    render(child)
                self.write("</textbox>\n")
            elif isinstance(item, LTChar):
                s = (
                    '<text font="%s" bbox="%s" colourspace="%s" '
                    'ncolour="%s" size="%.3f">'
                    % (
                        enc(item.fontname),
                        bbox2str(item.bbox),
                        item.ncs.name,
                        item.graphicstate.ncolor,
                        item.size,
                    )
                )
                self.write(s)
                self.write_text(item.get_text())
                self.write("</text>\n")
            elif isinstance(item, LTText):
                self.write("<text>%s</text>\n" % item.get_text())
            elif isinstance(item, LTImage):
                if self.figure:
                    self.figure.set_item(item)
                if self.imagewriter is not None:
                    name = self.imagewriter.export_image(item)
                    self.write(
                        '<image src="%s" width="%d" height="%d" />\n'
                        % (enc(name), item.width, item.height)
                    )
                else:
                    self.write(
                        '<image width="%d" height="%d" />\n' % (item.width, item.height)
                    )
            else:
                assert False, str(("Unhandled", item))

        render(ltpage)

    def close(self):
        self.write_footer()
        return self.rpa_pdf_document


class PageGenerator:
    """Supporting generator class for Pages"""

    def __init__(self, gen):
        self.generator = gen

    def __iter__(self):
        return self.generator

    def __len__(self):
        return sum(1 for _ in self.generator)


class PDF(FPDF, HTMLMixin):
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
    PIXEL_TOLERANCE = 5

    anchor_element: dict
    active_fileobject: object
    fileobjects: dict
    modified_reader: PdfFileReader
    output_directory: Path
    rpa_pdf_document: RpaPdfDocument

    def __init__(self, outdir: str = ".") -> None:
        FPDF.__init__(self)
        HTMLMixin.__init__(self)
        self.logger = logging.getLogger(__name__)

        self.active_fields = None
        self.active_fileobject = None
        self.active_pdf = None
        self.anchor_element = None
        self.fileobjects = {}
        self.modified_reader = None
        self.rpa_pdf_document = None

        self.set_output_directory(outdir)

        listener = RobotLogListener()
        listener.register_protected_keywords(["RPA.PDF.decrypt"])

    def __del__(self):
        self.close_all_pdf_documents()

    def close_all_pdf_documents(self) -> None:
        """Close all opened PDF file descriptors."""
        for filename, fileobject in self.fileobjects.items():
            fileobject.close()
            self.logger.debug('PDF "%s" closed', filename)
        self.anchor_element = None
        self.fileobjects = {}
        self.active_pdf = None
        self.active_fileobject = None
        self.active_fields = None
        self.rpa_pdf_document = None

    def close_pdf_document(self, source_pdf: str = None):
        """Close PDF file descriptor for certain file.

        :param source_pdf: filepath
        :raises ValueError: if file descriptor for the file is not found
        """
        if str(source_pdf) not in self.fileobjects.keys():
            raise ValueError('PDF "%s" is not open' % source_pdf)
        self.logger.info("Closing PDF document: %s", source_pdf)
        self.fileobjects[source_pdf].close()
        del self.fileobjects[source_pdf]
        self.active_pdf = None
        self.active_fileobject = None
        self.active_fields = None
        self.rpa_pdf_document = None

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

    def open_pdf_document(self, source_pdf: str = None) -> None:
        """Open PDF document.

        :param source_pdf: filepath to the source pdf
        :raises ValueError: if PDF is already open

        Also opens file for reading.
        """
        if source_pdf is None:
            raise ValueError("Source PDF is missing")
        if str(source_pdf) in self.fileobjects.keys():
            raise ValueError(
                "PDF file is already open. Please close it before opening again."
            )
        self.active_pdf = str(source_pdf)
        self.active_fileobject = open(source_pdf, "rb")
        self.active_fields = None
        self.fileobjects[source_pdf] = self.active_fileobject
        self.rpa_pdf_document = None

    def switch_to_pdf_document(self, source_pdf: str = None) -> None:
        """Switch library's current fileobject to already open file
        or open file if not opened.

        :param source_pdf: filepath
        :raises ValueError: if PDF filepath is not given and there are no active
            file to activate
        """
        if source_pdf is not None and str(source_pdf) not in self.fileobjects.keys():
            self.open_pdf_document(source_pdf)
            return
        if source_pdf is None and self.active_fileobject is None:
            raise ValueError("No PDF is open")
        if (
            source_pdf is not None
            and self.active_fileobject != self.fileobjects[source_pdf]
        ):
            self.logger.debug("Switching to another open document")
            self.active_pdf = str(source_pdf)
            self.active_fileobject = self.fileobjects[str(source_pdf)]
            self.active_fields = None
            self.rpa_pdf_document = None

    def add_pages(self, pages: int = 1) -> None:
        """Adds pages into PDF documents.

        :param pages: number of pages to add, defaults to 1
        """
        for _ in range(int(pages)):
            self.add_page()

    def add_pages_to_document(
        self, pages: int = 1, source_pdf: str = None, target_pdf: str = None
    ) -> None:
        """Add empty pages into current source document

        :param pages: number of pages to add, defaults to 1
        :param source_pdf: filepath to the source pdf
        :param target_pdf: filename to the target pdf, stored by default
            to `output_directory`
        """
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.active_fileobject)
        source_page = reader.getPage(0)

        writer = PyPDF2.PdfFileWriter()
        output_filepath = Path(self.output_directory / target_pdf)
        pageobject = PyPDF2.pdf.PageObject.createBlankPage(
            None, source_page.mediaBox.getWidth(), source_page.mediaBox.getHeight()
        )
        writer.appendPagesFromReader(reader)
        for _ in range(int(pages)):
            writer.addPage(pageobject)
        with open(output_filepath, "wb") as f:
            writer.write(f)

    def template_html_to_pdf(
        self,
        template: str = None,
        filename: str = None,
        variables: dict = None,
        create_dirs: bool = True,
        exists_ok: bool = True,
    ) -> None:
        """Use HTML template file to generate PDF file.

        :param template: filepath to HTML template
        :param filename: filepath where to save PDF document
        :param variables: dictionary of variables to fill into template, defaults to {}
        :param create_dirs: directory structure is created if it is missing,
         default `True`
        :param exists_ok: file is overwritten if it exists, default `True`
        """
        required_param([template, filename], "template_html_to_pdf")
        variables = variables or {}

        with open(template, "r") as templatefile:
            html = templatefile.read()
        for key, value in variables.items():
            html = html.replace("{{" + key + "}}", str(value))

        target_path = self.output_directory / filename
        self._write_html_to_pdf(html, target_path, create_dirs, exists_ok)

    def html_to_pdf(
        self,
        content: str = None,
        filename: str = None,
        variables: dict = None,
        create_dirs: bool = True,
        exists_ok: bool = True,
    ) -> None:
        """Use HTML content to generate PDF file.

        :param content: HTML content
        :param filename: filepath where to save PDF document
        :param variables: dictionary of variables to fill into template, defaults to {}
        :param create_dirs: directory structure is created if it is missing,
         default `True`
        :param exists_ok: file is overwritten if it exists, default `True`
        """
        required_param([content, filename], "html_to_pdf")
        variables = variables or {}

        html = content.encode("utf-8").decode("latin-1")

        for key, value in variables.items():
            html = html.replace("{{" + key + "}}", str(value))

        target_path = self.output_directory / filename
        self._write_html_to_pdf(html, target_path, create_dirs, exists_ok)

    def _write_html_to_pdf(self, html, output_path, create_dirs, exists_ok):
        if create_dirs:
            Path(output_path).resolve().parent.mkdir(parents=True, exist_ok=True)
        if not exists_ok and Path(output_path).exists():
            raise FileExistsError(output_path)
        notebook_print(link=str(output_path))
        self.add_pages(1)
        self.write_html(html)
        pdf_content = self.output(dest="S").encode("latin-1")
        with open(output_path, "wb") as outfile:
            outfile.write(pdf_content)
        self.__init__()

    def get_info(self, source_pdf: str = None) -> dict:
        """Get information from PDF document.

        :param source_pdf: filepath to the source pdf
        :return: dictionary of PDF information
        """
        self.switch_to_pdf_document(source_pdf)
        pdf = PyPDF2.PdfFileReader(self.active_fileobject)
        docinfo = pdf.getDocumentInfo()
        parser = PDFParser(self.active_fileobject)
        document = PDFDocument(parser)
        fields = None
        try:
            fields = resolve1(document.catalog["AcroForm"])["Fields"]
        except KeyError:
            pass
        info = {
            "Author": docinfo.author,
            "Creator": docinfo.creator,
            "Producer": docinfo.producer,
            "Subject": docinfo.subject,
            "Title": docinfo.title,
            "Pages": pdf.getNumPages(),
            "Encrypted": self.is_pdf_encrypted(source_pdf),
            "Fields": bool(fields),
        }
        return info

    def extract_pages_from_pdf(
        self, source_pdf: str = None, target_pdf: str = None, pages: Any = None
    ) -> None:
        """Extract pages from source PDF and save to target PDF document.

        :param source_pdf: filepath to the source pdf
        :param target_pdf: filename to the target pdf, stored by default
            to `output_directory`
        :param pages: page numbers to extract from PDF (numbers start from 0)
            if None then extracts all pages

        Page numbers starting from 1.
        """
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.active_fileobject)
        writer = PyPDF2.PdfFileWriter()
        output_filepath = Path(self.output_directory / target_pdf)
        if pages and not isinstance(pages, list):
            pages = pages.split(",")
        elif pages is None:
            pages = range(reader.getNumPages())
        pages = list(map(int, pages))
        for pagenum in pages:
            writer.addPage(reader.getPage(int(pagenum) - 1))
        with open(str(output_filepath), "wb") as f:
            writer.write(f)

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
            self.parse_pdf()
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
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.active_fileobject)
        output_filepath = Path(self.output_directory / target_pdf)
        writer = PyPDF2.PdfFileWriter()

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

    def is_pdf_encrypted(self, source_pdf: str = None) -> bool:
        """Check if PDF is encrypted.

        Returns True even if PDF was decrypted.

        :param source_pdf: filepath to the source pdf
        :return: True if file is encrypted
        """
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.active_fileobject)
        return reader.isEncrypted

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
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.active_fileobject)
        output_filepath = Path(self.output_directory / target_pdf)
        if owner_pwd is None:
            owner_pwd = user_pwd
        writer = PyPDF2.PdfFileWriter()
        writer.appendPagesFromReader(reader)
        writer.encrypt(user_pwd, owner_pwd, use_128bit)
        with open(str(output_filepath), "wb") as f:
            writer.write(f)

    def pdf_decrypt(
        self, source_pdf: str = None, target_pdf: str = None, password: str = None
    ) -> bool:
        """Decrypt PDF with password.

        :param source_pdf: filepath to the source pdf
        :param target_pdf: filepath to the decrypted pdf
        :param password: password as a string
        :return: True if decrypt was successful, else False or Exception
        :raises ValueError: on decryption errors
        """
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.active_fileobject)
        try:
            self.modified_reader = None
            match_result = reader.decrypt(password)
            if match_result == 0:
                raise ValueError("PDF decrypt failed.")
            elif match_result == 1:
                self.logger.info("PDF was decrypted with user password.")
            elif match_result == 2:
                self.logger.info("PDF was decrypted with owner password.")
            else:
                return False
            self.modified_reader = reader
            self.save_pdf(None, target_pdf, True)
            return True

        except NotImplementedError as e:
            raise ValueError(
                f"Document {source_pdf} uses an unsupported encryption method."
            ) from e
        except KeyError:
            self.logger.info("PDF is not encrypted")
            return False
        return False

    def _extract_pages_from_file(self, source_pdf: str):
        self.switch_to_pdf_document(source_pdf)
        pdf_pages = PDFPage.get_pages(self.active_fileobject)
        return PageGenerator(pdf_pages)

    def get_number_of_pages(self, source_pdf: str = None) -> int:
        """Get number of pages in the document.

        :param source_pdf: filepath to the source pdf
        :raises PdfReadError: if file is encrypted or other restrictions are in place
        """
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.active_fileobject)
        return reader.getNumPages()

    def parse_pdf(self, source_pdf: str = None) -> None:
        """Parse source PDF into entities which can be
        used for text searches for example.

        :param source_pdf: source
        """
        if source_pdf is not None:
            self.switch_to_pdf_document(source_pdf)
        source_parser = PDFParser(self.active_fileobject)
        source_document = PDFDocument(source_parser)
        source_pages = PDFPage.create_pages(source_document)
        rsrcmgr = PDFResourceManager()
        laparams = LAParams(
            detect_vertical=True,
            all_texts=True,
        )
        device = RPAConverter(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        # # Look at all (nested) objects on each page
        for _, page in enumerate(source_pages, 0):
            interpreter.process_page(page)
        self.rpa_pdf_document = device.close()

    def _set_need_appearances_writer(self, writer: PdfFileWriter):
        # See 12.7.2 and 7.7.2 for more information:
        # http://www.adobe.com/content/dam/acom/en/devnet/acrobat/pdfs/PDF32000_2008.pdf
        try:
            catalog = writer._root_object  # pylint: disable=W0212
            # get the AcroForm tree
            if "/AcroForm" not in catalog:
                catalog.update(
                    {
                        NameObject("/AcroForm"): IndirectObject(
                            len(writer._objects), 0, writer  # pylint: disable=W0212
                        )
                    }
                )

            need_appearances = NameObject("/NeedAppearances")
            catalog["/AcroForm"][need_appearances] = BooleanObject(True)
            # del writer._root_object["/AcroForm"]['NeedAppearances']
            return writer

        except Exception as e:  # pylint: disable=broad-except
            print("set_need_appearances_writer() catch : ", repr(e))
            return writer

    def update_field_values(
        self, source_pdf: str = None, target_pdf: str = None, newvals: dict = None
    ) -> None:
        """Update field values in PDF if it has fields.

        :param source_pdf: source PDF with fields to update
        :param target_pdf: updated target PDF
        :param newvals: dictionary with key values to update
        """
        self.switch_to_pdf_document(source_pdf)
        reader = PyPDF2.PdfFileReader(self.active_fileobject, strict=False)
        if "/AcroForm" in reader.trailer["/Root"]:
            reader.trailer["/Root"]["/AcroForm"].update(
                {NameObject("/NeedAppearances"): BooleanObject(True)}
            )
        writer = PdfFileWriter()

        self._set_need_appearances_writer(writer)

        for i in range(reader.getNumPages()):
            page = reader.getPage(i)
            try:
                if newvals:
                    self.logger.debug("Updating form field values for page %s", i)
                    updatedFields = {
                        k: v["value"] if v["value"] else ""
                        for (k, v) in newvals.items()
                    }
                    writer.updatePageFormFieldValues(page, fields=updatedFields)
                elif self.active_fields:
                    updatedFields = {
                        k: v["value"] if v["value"] else ""
                        for (k, v) in self.active_fields.items()
                    }
                    writer.updatePageFormFieldValues(page, fields=updatedFields)
                writer.addPage(page)
            except Exception as e:  # pylint: disable=W0703
                self.logger.warning(repr(e))
                writer.addPage(page)

        if target_pdf is None:
            target_pdf = self.active_pdf
        with open(target_pdf, "wb") as f:
            writer.write(f)

    def get_input_fields(
        self, source_pdf: str = None, replace_none_value: bool = False
    ) -> dict:
        """Get input fields in the PDF.

        :param source_pdf: source filepath, defaults to None
        :param replace_none_value: if value is None replace it with key name,
            defaults to False
        :return: dictionary of input key values or `None`

        Stores input fields internally so that they can be used without
        parsing PDF again.

        Parameter `replace_none_value` is for convience to visualize fields.
        """
        record_fields = {}
        if source_pdf is None and self.active_fields:
            return self.active_fields
        self.switch_to_pdf_document(source_pdf)
        source_parser = PDFParser(self.active_fileobject)
        source_document = PDFDocument(source_parser)
        try:
            fields = resolve1(source_document.catalog["AcroForm"])["Fields"]
        except KeyError:
            self.logger.info(
                'PDF "%s" does not have any input fields.', self.active_pdf
            )
            return None

        for i in fields:
            field = resolve1(i)
            if field is None:
                continue
            name, value, rect, label = (
                field.get("T"),
                field.get("V"),
                field.get("Rect"),
                field.get("TU"),
            )
            if value is None and replace_none_value:
                record_fields[name.decode("iso-8859-1")] = {
                    "value": name.decode("iso-8859-1"),
                    "rect": iterable_items_to_int(rect),
                    "label": label.decode("iso-8859-1") if label else None,
                }
            else:
                try:
                    record_fields[name.decode("iso-8859-1")] = {
                        "value": value.decode("iso-8859-1") if value else "",
                        "rect": iterable_items_to_int(rect),
                        "label": label.decode("iso-8859-1") if label else None,
                    }
                except AttributeError:
                    self.logger.debug("Attribute error")
                    record_fields[name.decode("iso-8859-1")] = {
                        "value": value,
                        "rect": iterable_items_to_int(rect),
                        "label": label.decode("iso-8859-1") if label else None,
                    }

        self.active_fields = record_fields if record_fields else None
        return record_fields

    def set_anchor_to_element(self, locator: str) -> bool:
        """Sets anchor point in the document for further searches.

        PDF needs to be parsed before elements can be found.

        :param locator: element to search for
        :return: True if element was found
        """
        self.logger.info("Set anchor to element: ('locator=%s')", locator)
        if self.rpa_pdf_document is None:
            self.parse_pdf()
        if locator.startswith("text:"):
            criteria = "text"
            _, locator = locator.split(":", 1)
            match = self._find_matching_textbox(criteria, locator)
            if match:
                self.anchor_element = match
                return True
        elif locator.startswith("coords:"):
            _, locator = locator.split(":", 1)
            coords = locator.split(",")
            if len(coords) == 2:
                left, bottom = coords
                top = bottom
                right = left
            elif len(coords) == 4:
                left, bottom, right, top = coords
            else:
                raise ValueError("Give 2 coordinates for point, or 4 for area")
            self.anchor_element = TargetObject()
            self.anchor_element.boxid = -1
            self.anchor_element.bbox = (
                int(left),
                int(bottom),
                int(right),
                int(top),
            )
            self.anchor_element.text = None
            return True
        else:
            # use "text" criteria by default
            criteria = "text"
            match = self._find_matching_textbox(criteria, locator)
            if match:
                self.anchor_element = match
                return True
        self.anchor_element = None
        return False

    def _find_matching_textbox(self, criteria: str, locator: str) -> str:
        self.logger.info(
            "find_matching_textbox: ('criteria=%s', 'locator=%s')", criteria, locator
        )
        matches = []
        for _, page in self.rpa_pdf_document.get_pages().items():
            content = page.get_textboxes()
            for _, item in content.items():
                # Only text matching at the moment
                if item.text.lower() == locator.lower():
                    matches.append(item)
        match_count = len(matches)
        if match_count == 1:
            self.logger.debug("Found 1 match for locator '%s'", locator)
            return matches[0]
        elif match_count == 0:
            self.logger.info("Did not find any matches")
        else:
            self.logger.info("Found %d matches for locator '%s'", match_count, locator)
            for m in matches:
                self.logger.debug("box %d bbox %s text '%s'", m.boxid, m.bbox, m.text)
        return False

    def get_value_from_anchor(
        self,
        locator: str,
        pagenum: int = 1,
        direction: str = "right",
        strict: bool = False,
        regexp: str = None,
        only_closest: bool = True,
    ) -> str:
        """Get closest text (value) to anchor element.

        PDF needs to be parsed before elements can be found.

        :param locator: element to set anchor to
        :param pagenum: page number where search if performed on, default 1 (first)
        :param direction: in which direction to search for text,
            directions  'top'/'up', 'bottom'/'down', 'left' or 'right',
            defaults to 'right'
        :param strict: if element margins should be used for matching points,
            used when direction is 'top' or 'bottom', default `False`
        :param regexp: expected format of value to match, defaults to None
        :param only_closest: return all possible values or only the closest
        :return: closest matching text or `None`
        """
        self.logger.debug(
            "Get Value From Anchor: ('locator=%s', 'direction=%s', 'regexp=%s')",
            locator,
            direction,
            regexp,
        )
        self.set_anchor_to_element(locator)
        possibles = []
        if self.anchor_element:
            self.logger.debug("we have anchor: %s", self.anchor_element.bbox)
            page = self.rpa_pdf_document.get_page(int(pagenum))
            for _, item in page.get_textboxes().items():
                possible = None
                # Skip anchor element from matching
                if item.boxid == self.anchor_element.boxid:
                    continue
                if direction in ["left", "right"]:
                    possible = self._is_match_on_horizontal(direction, item, regexp)
                elif direction in ["top", "bottom", "up", "down"]:
                    possible = self._is_match_on_vertical(
                        direction, item, strict, regexp
                    )
                elif direction == "box":
                    possible = self._is_match_in_box(item)
                if possible:
                    possibles.append(possible)
            if only_closest:
                return self._get_closest_from_possibles(direction, possibles)
            else:
                return possibles
        self.logger.info("NO ANCHOR")
        return possibles

    def _is_within_tolerance(self, base, target):
        max_target = target + self.PIXEL_TOLERANCE
        min_target = max(target - self.PIXEL_TOLERANCE, 0)
        return min_target <= base <= max_target

    def _is_match_on_horizontal(self, direction, item, regexp):
        (left, _, right, top) = self.anchor_element.bbox
        match = False
        direction_ok = False
        if (
            direction == "right"
            and self._is_within_tolerance(item.top, top)
            and item.left >= right
        ):
            direction_ok = True
        elif (
            direction == "left"
            and self._is_within_tolerance(item.top, top)
            and item.right <= left
        ):
            direction_ok = True
        if regexp and direction_ok and item and re.match(regexp, item.text):
            match = True
        elif regexp is None and direction_ok and item:
            match = True
        return item if match else None

    def _is_match_on_vertical(self, direction, item, strict, regexp):
        (left, bottom, right, top) = self.anchor_element.bbox
        text = None
        direction_down = direction in ["bottom", "down"]
        direction_up = direction in ["top", "up"]
        if (direction_down and item.top <= bottom) or (
            direction_up and item.bottom >= top
        ):
            if not strict and (item.right <= right or item.left >= left):
                text = item
            elif strict and (item.right == right or item.left == left):
                text = item
            if regexp and text and re.match(regexp, item.text):
                self.logger.debug(
                    "POSSIBLE MATCH %s %s %s", item.boxid, item.text, item.bbox
                )
                return item
            elif regexp is None and text:
                self.logger.debug(
                    "POSSIBLE MATCH %s %s %s", item.boxid, item.text, item.bbox
                )
                return item
        return None

    def _is_match_in_box(self, item):
        (left, bottom, right, top) = self.anchor_element.bbox
        if (
            left <= item.left
            and right >= item.right
            and bottom <= item.bottom
            and top >= item.top
        ):
            return item
        return None

    def _get_closest_from_possibles(self, direction, possibles):
        distance = 500000
        closest = None
        (_, bottom, right, top) = self.anchor_element.bbox
        direction_down = direction in ["bottom", "down"]
        for p in possibles:
            if direction_down:
                vertical_distance = bottom - p.top
            else:
                vertical_distance = top - p.bottom
            h_distance_to_right = abs(right - p.right)
            h_distance_to_left = abs(right - p.left)
            horizontal_distance = min(h_distance_to_left, h_distance_to_right)
            calc_distance = math.sqrt(
                math.pow(horizontal_distance, 2) + math.pow(vertical_distance, 2)
            )
            if calc_distance < distance:
                distance = calc_distance
                closest = p

        return closest

    def get_all_figures(self) -> dict:
        """Return all figures in the PDF document.

        :return: dictionary of figures divided into pages

        PDF needs to be parsed before elements can be found.
        """
        if self.rpa_pdf_document is None:
            raise ValueError("PDF has not been parsed yet")
        pages = {}
        for pagenum, page in self.rpa_pdf_document.get_pages().items():
            pages[pagenum] = page.get_figures()
        return pages

    def set_field_value(self, field_name: str, value: Any, save: bool = False):
        """Set value for field with given name.

        :param field_name: field to update
        :param value: new value for the field

        Tries to match on field identifier and its label.

        Exception is thrown if field can't be found or more than 1 field matches
        the given `field_name`.
        """
        if not self.active_fields:
            self.get_input_fields()
            if not self.active_fields:
                raise ValueError("Document does not have input fields")

        if field_name in self.active_fields.keys():
            self.active_fields[field_name]["value"] = value  # pylint: disable=E1136
        else:
            label_matches = 0
            field_key = None
            for k, _ in self.active_fields.items():
                # pylint: disable=E1136
                if self.active_fields[k]["label"] == field_name:
                    label_matches += 1
                    field_key = k
            if label_matches == 1:
                self.active_fields[field_key]["value"] = value  # pylint: disable=E1136
            elif label_matches > 1:
                raise ValueError(
                    "Unable to set field value - field name: '%s' matched %d fields"
                    % (field_name, label_matches)
                )
            else:
                raise ValueError(
                    "Unable to set field value - field name: '%s' "
                    "not found in the document" % field_name
                )
        if save:
            self.update_field_values(None, None, self.active_fields)

    def replace_text(self, text: str, replace: str):
        """Replace text content with something else in the PDF.

        :param text: this text will be replaced
        :param replace: used to replace `text`
        """
        if self.rpa_pdf_document is None:
            self.parse_pdf()
        for _, page in self.rpa_pdf_document.get_pages().items():
            for _, textbox in page.get_textboxes().items():
                if textbox.text == text:
                    textbox.text = replace
                    return
        self.logger.info("Did not find any matching text")

    def add_image_to_pdf(self, imagefile, source=None, target=None, coverage=0.2):
        """Add image to PDF which can be new or existing PDF.

        :param imagefile: filepath to image file to add into PDF
        :param source: filepath to source, if not given add image to currently
            active PDF
        :param target: filepath of target PDF
        :param coverage: [description], defaults to 0.2
        :raises ValueError: [description]

        Result will be always written to `target_pdf` so that needs
        to be given for the keyword.
        """
        if target is None:
            raise ValueError("Target PDF needs to be set")
        if source is None and self.active_pdf:
            source = self.active_pdf
        elif source is None and self.active_pdf is None:
            raise ValueError("No source PDF exists")
        temp_pdf = os.path.join(tempfile.gettempdir(), "temp.pdf")
        writer = PdfFileWriter()
        pdf = FPDF()
        pdf.add_page()
        reader = PdfFileReader(source)
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

        img = PdfFileReader(temp_pdf)
        watermark = img.getPage(0)
        for n in range(reader.getNumPages()):
            page = reader.getPage(n)
            page.mergePage(watermark)
            writer.addPage(page)

        with open(target, "wb") as f:
            writer.write(f)

    def save_pdf(
        self, source: str = None, target: str = None, use_modified_reader: bool = False
    ):
        """Save current over itself or to `target_pdf`

        :param source: filepath to source PDF
        :param target: filepath to target PDF
        :param use_modified_reader: needs to be set to `True` if
            using modified PDF reader
        """
        if not use_modified_reader:
            self.get_input_fields(source)

        if self.active_fields:
            self.logger.info("Saving PDF with input fields")
            self.update_field_values(source, target, self.active_fields)
        else:
            self.logger.info("Saving PDF")
            self.switch_to_pdf_document(source)
            if use_modified_reader:
                reader = self.modified_reader
            else:
                reader = PyPDF2.PdfFileReader(self.active_fileobject, strict=False)
            writer = PdfFileWriter()

            for i in range(reader.getNumPages()):
                page = reader.getPage(i)
                try:
                    writer.addPage(page)
                except Exception as e:  # pylint: disable=W0703
                    self.logger.warning(repr(e))
                    writer.addPage(page)

            if target is None:
                target = self.active_pdf
            with open(target, "wb") as f:
                writer.write(f)

    def dump_pdf_as_xml(self, source_pdf: str = None):
        """Get PDFMiner format XML dump of the PDF

        :param source_pdf: filepath
        :return: XML content
        """
        self.switch_to_pdf_document(source_pdf)
        if self.rpa_pdf_document is None:
            self.parse_pdf()
        return self.rpa_pdf_document.dump_xml()
