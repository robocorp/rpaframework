import collections
from collections import OrderedDict
import logging
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable

from fpdf import FPDF, HTMLMixin

from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfpage import PDFPage

# from pdfminer.pdftypes import PDFObjectNotFound
from pdfminer.high_level import extract_text
from pdfminer.layout import (
    LAParams,
    LTContainer,
    LTPage,
    LTText,
    LTTextBox,
    LTLine,
    LTRect,
    LTCurve,
    LTFigure,
    LTTextLine,
    LTTextBoxVertical,
    LTTextBoxHorizontal,
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
from RPA.core.utils import UNDEFINED
from RPA.RobotLogListener import RobotLogListener

try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


def iterable_items_to_int(bbox):
    return list(map(lambda x: int(x), bbox))


class RpaFigure:
    figure_name: str
    figure_bbox: list
    item: dict

    def __init__(self, name: str, bbox: Iterable) -> None:
        self.figure_name = name
        self.figure_bbox = iterable_items_to_int(bbox)

    def set_item(self, item: Any):
        # LTImage
        self.item = {"name": enc(item.name), "width": item.width, "height": item.height}


class RpaPdfPage:
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

    def get_textboxes(self) -> OrderedDict:
        return {k: v for k, v in self.content.items() if type(v) == RpaTextBox}

    def __str__(self) -> str:
        page_as_str = '<page id="%s" bbox="%s" rotate="%d">\n' % (
            self.pageid,
            bbox2str(self.bbox),
            self.rotate,
        )
        for idx, c in self.content.items():
            page_as_str += f"{c}\n"
        return page_as_str


class RpaTextBox:
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

    @property
    def bbox(self) -> list:
        return self.item["bbox"]

    def __str__(self) -> str:
        return self.text


class RpaPdfDocument:
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

    def dump_xml(self) -> str:
        return self.xml_content.decode("utf-8")


class RPAConverter(PDFConverter):

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
        self.current_page = None
        self.imagewriter = imagewriter
        self.stripcontrol = stripcontrol
        self.write_header()
        return

    def write(self, text):
        if self.codec:
            text = text.encode(self.codec)
        self.rpa_pdf_document.append_xml(text)
        return

    def write_header(self):
        if self.codec:
            self.write('<?xml version="1.0" encoding="%s" ?>\n' % self.codec)
        else:
            self.write('<?xml version="1.0" ?>\n')
        self.write("<pages>\n")
        return

    def write_footer(self):
        self.write("</pages>\n")
        return

    def write_text(self, text):
        if self.stripcontrol:
            text = self.CONTROL.sub("", text)
        self.write(enc(text))
        return

    def receive_layout(self, ltpage):
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
            return

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
                s = '<figure name="%s" bbox="%s">\n' % (item.name, bbox2str(item.bbox))
                self.write(s)
                figure = RpaFigure(item.name, item.bbox)
                for child in item:
                    figure.set_item(item)
                    render(child)
                self.write("</figure>\n")
                self.current_page.add_content(figure)
            elif isinstance(item, LTTextLine):
                self.write('<textline bbox="%s">\n' % bbox2str(item.bbox))
                # print("TEXTLINE", item.bbox, item.get_text())
                for child in item:
                    render(child)
                self.write("</textline>\n")
            elif isinstance(item, LTTextBox):
                wmode = ""
                # box = None

                if isinstance(item, LTTextBoxVertical):
                    wmode = ' wmode="vertical"'
                    #
                s = '<textbox id="%d" bbox="%s"%s>\n' % (
                    item.index,
                    bbox2str(item.bbox),
                    wmode,
                )
                box = RpaTextBox(item.index, item.bbox, wmode)
                # print("TEXTBOX starting")
                # print(item)
                self.write(s)
                # if box is None:
                #    box = RpaTextBox(item.index, item.bbox, wmode)
                for child in item:
                    box.set_item(item)
                    render(child)
                self.write("</textbox>\n")
                # print("TEXTBOX ending")
                self.current_page.add_content(box)
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
                # self.current_page.add_content(item)
                self.write(s)
                self.write_text(item.get_text())
                self.write("</text>\n")
            elif isinstance(item, LTText):
                self.write("<text>%s</text>\n" % item.get_text())
            elif isinstance(item, LTImage):
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
            return

        render(ltpage)
        return

    def close(self):
        self.write_footer()
        return self.rpa_pdf_document


class PageGenerator(object):
    def __init__(self, gen):
        self.generator = gen

    def __iter__(self):
        return self.generator

    def __len__(self):
        return sum(1 for _ in self.generator)


class PDF(FPDF, HTMLMixin):
    """RPA Framework library for PDF management.
    """

    output_directory: Path
    rpa_pdf_document: RpaPdfDocument
    source_document: PDFDocument
    source_filepath: str
    source_parser: PDFParser
    source_reader: PdfFileReader

    def __init__(self, outdir: str = ".") -> None:
        FPDF.__init__(self)
        HTMLMixin.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.set_output_directory(outdir)
        self.rpa_pdf_document = None
        self.source_document = None
        self.source_filepath = None
        self.source_parser = None
        self.source_reader = None
        self.source_pages = None
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

    def open_pdf_document(self, source_pdf: str = None) -> None:
        """Open PDF document.

        :param source_pdf: filepath to the source pdf
        """
        if source_pdf is None:
            raise ValueError("Source filepath is missing")
        self.source_filepath = source_pdf
        with open(self.source_filepath, "rb") as f:
            self.source_parser = PDFParser(f)
            self.source_document = PDFDocument(self.source_parser)
            self.source_pages = PDFPage.create_pages(self.source_document)
            self.source_reader = PyPDF2.PdfFileReader(f)

    def add_pages(self, pages: int = 1) -> None:
        """Adds pages into PDF documents.

        :param pages: number of pages to add, defaults to 1
        """
        for _ in range(int(pages)):
            self.add_page()

    def add_pages_to_document(
        self, pages: int = 1, source_pdf: str = None, target_pdf: str = None
    ) -> None:
        """Add pages into current source document

        :param pages: number of pages to add, defaults to 1
        :param source_pdf: filepath to the source pdf
        :param target_pdf: filename to the target pdf, stored by default
            to `output_directory`
        """
        self.open_pdf_document(source_pdf)
        source_page = self.source_reader.getPage(0)

        pdf_writer = PyPDF2.PdfFileWriter()
        output_filepath = Path(self.output_directory / target_pdf)
        pageobject = PyPDF2.pdf.PageObject.createBlankPage(
            None, source_page.mediaBox.getWidth(), source_page.mediaBox.getHeight()
        )
        pdf_writer.appendPagesFromReader(self.source_reader)
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
        self.open_pdf_document(source_pdf)

        return self.source_document.info

    def extract_pages_from_pdf(
        self, pages: int, source_pdf: str = None, target_pdf: str = None
    ) -> None:
        """Extract pages from source PDF and save to target PDF document.

        :param source_pdf: filepath to the source pdf
        :param target_pdf: filename to the target pdf, stored by default
            to `output_directory`
        :param pages: page numbers to extract from PDF (numbers start from 0)
        """
        self.open_pdf_document(source_pdf)
        pdf_writer = PyPDF2.PdfFileWriter()
        output_filepath = Path(self.output_directory / target_pdf)
        if not isinstance(pages, list):
            pagelist = [pages]
        else:
            pagelist = pages
        for page in pagelist:
            pdf_writer.addPage(self.source_reader.getPage(int(page)))
        with open(str(output_filepath), "wb") as f:
            pdf_writer.write(f)

    def get_text_from_pdf(self, source_pdf: str = None, pages: list = None) -> dict:
        """Get text from set of pages in source PDF document.

        :param source_pdf: filepath to the source pdf
        :param pages: page numbers to get text (numbers start from 0)
        :return: dictionary of pages and their texts
        """
        if source_pdf is None and self.source_filepath is None:
            raise ValueError("Source filepath is missing")
        elif source_pdf is None:
            source_pdf = self.source_filepath

        with open(source_pdf, "rb") as infile:
            return extract_text(infile, page_numbers=pages)

    def _validate_filepaths(
        self, source: str = UNDEFINED, target: str = UNDEFINED
    ) -> str:
        if target is not UNDEFINED and target is None:
            raise ValueError("Target filepath is missing")
        if source is not UNDEFINED:
            if source is None and self.source_filepath is None:
                raise ValueError("Source filepath is missing")
            elif source is None:
                source = self.source_filepath
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
        self.open_pdf_document(source_pdf)
        output_filepath = Path(self.output_directory / target_pdf)
        pdf_writer = PyPDF2.PdfFileWriter()

        if not isinstance(pages, list):
            pagelist = [pages]
        else:
            pagelist = pages
        for page in range(self.source_reader.getNumPages()):
            source_page = self.source_reader.getPage(int(page))
            if page in pagelist:
                if clockwise:
                    source_page.rotateClockwise(int(angle))
                else:
                    source_page.rotateCounterClockwise(int(angle))
            else:
                source_page = self.source_reader.getPage(int(page))
            pdf_writer.addPage(source_page)
        with open(str(output_filepath), "wb") as fh:
            pdf_writer.write(fh)

    def is_pdf_encrypted(self, source_pdf: str = None) -> bool:
        """Check if PDF is encrypted.

        Returns True even if PDF was decrypted.

        :param source_pdf: filepath to the source pdf
        :return: True if file is encrypted
        """
        if self.source_reader is None:
            self.open_pdf_document(source_pdf)
        return self.source_reader.isEncrypted

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
        if self.source_reader is None:
            self.open_pdf_document(source_pdf)
        output_filepath = Path(self.output_directory / target_pdf)
        if owner_pwd is None:
            owner_pwd = user_pwd
        pdf_writer = PyPDF2.PdfFileWriter()
        pdf_writer.appendPagesFromReader(self.source_reader)
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
        self.open_pdf_document(source_pdf)
        try:
            match_result = self.source_reader.decrypt(password)
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

    def _extract_pages_from_file(self, source_pdf: str):
        self.open_pdf_document(source_pdf)
        with open(source_pdf, "rb") as infile:
            pdf_pages = PDFPage.get_pages(infile)
            return PageGenerator(pdf_pages)

    def get_number_of_pages(self, source_pdf: str = None) -> int:
        """Get number of pages in the document.

        :param source_pdf: filepath to the source pdf
        :raises PdfReadError: if file is encrypted or other restrictions are in place
        """
        self.open_pdf_document(source_pdf)
        return self.source_reader.getNumPages()

    def parse_pdf(self, source_pdf: str):
        """[summary]

        :param source_pdf: [description]
        :rtype: [type]
        """
        with open(source_pdf, "rb") as f:
            source_parser = PDFParser(f)
            source_document = PDFDocument(source_parser)
            source_pages = PDFPage.create_pages(source_document)
            rsrcmgr = PDFResourceManager()
            laparams = LAParams(detect_vertical=True, all_texts=True,)
            device = RPAConverter(rsrcmgr, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)

            # # Look at all (nested) objects on each page
            for _, page in enumerate(source_pages, 1):
                interpreter.process_page(page)
            self.rpa_pdf_document = device.close()
        return self.rpa_pdf_document

    def update_form_values(
        self, source_pdf: str, target_pdf: str, newvals: dict = None
    ):
        source_reader = PdfFileReader(open(source_pdf, "rb"), strict=False)
        if "/AcroForm" in source_reader.trailer["/Root"]:
            source_reader.trailer["/Root"]["/AcroForm"].update(
                {NameObject("/NeedAppearances"): BooleanObject(True)}
            )
        writer = PdfFileWriter()
        self.set_need_appearances_writer(writer)
        if "/AcroForm" in writer._root_object:
            writer._root_object["/AcroForm"].update(
                {NameObject("/NeedAppearances"): BooleanObject(True)}
            )

        for i in range(source_reader.getNumPages()):
            page = source_reader.getPage(i)
            try:
                if newvals:
                    print(f"updating form field values for page {i}")
                    writer.updatePageFormFieldValues(page, newvals)
                else:
                    writer.updatePageFormFieldValues(
                        page,
                        {
                            k: f"#{i} {k}={v}"
                            for i, (k, v) in enumerate(
                                source_reader.getFormTextFields().items()
                            )
                        },
                    )
                writer.addPage(page)
            except Exception as e:
                print(repr(e))
                writer.addPage(page)

        with open(target_pdf, "wb") as out:
            writer.write(out)

    def set_need_appearances_writer(self, writer: PdfFileWriter):
        # See 12.7.2 and 7.7.2 for more information: http://www.adobe.com/content/dam/acom/en/devnet/acrobat/pdfs/PDF32000_2008.pdf
        try:
            catalog = writer._root_object
            # get the AcroForm tree
            if "/AcroForm" not in catalog:
                writer._root_object.update(
                    {
                        NameObject("/AcroForm"): IndirectObject(
                            len(writer._objects), 0, writer
                        )
                    }
                )

            need_appearances = NameObject("/NeedAppearances")
            writer._root_object["/AcroForm"][need_appearances] = BooleanObject(True)
            # del writer._root_object["/AcroForm"]['NeedAppearances']
            return writer

        except Exception as e:
            print("set_need_appearances_writer() catch : ", repr(e))
            return writer

    def get_input_fields(
        self, source_pdf: str, replace_none_value: bool = True
    ) -> dict:
        record_fields = {}

        with open(source_pdf, "rb") as f:
            source_parser = PDFParser(f)
            source_document = PDFDocument(source_parser)
            fields = resolve1(source_document.catalog["AcroForm"])["Fields"]

            for i in fields:
                field = resolve1(i)
                if field is None:
                    continue
                name, value = field.get("T"), field.get("V")
                if value is None and replace_none_value:
                    print(f"setting default value to same as key: {name}")
                    record_fields[name.decode("iso-8859-1")] = name.decode("iso-8859-1")
                else:
                    try:
                        record_fields[name.decode("iso-8859-1")] = value.decode(
                            "iso-8859-1"
                        )
                        print(f"setting value: {value} to key: {name}")
                    except AttributeError:
                        record_fields[name.decode("iso-8859-1")] = value
                        print(
                            f"setting value: {value} to key: {name} / after AttributError"
                        )

        # convert to string
        return record_fields

    def set_anchor_to_element(self, locator: str) -> bool:
        print("set_anchor_to_element: ('locator=%s')" % locator)
        if locator.startswith("search:"):
            criteria = "search"
            locator = locator.split(":")[1]
            match = self.find_matching_textbox(criteria, locator)
            if match:
                self.anchor_element = match
                return True
        self.anchor_element = None
        return False

    def find_matching_textbox(self, criteria: str, locator: str) -> str:
        if self.rpa_pdf_document is None:
            print("PDF has not been parsed yet")
            return False
        print(
            "find_matching_textbox: criteria: ('criteria=%s', 'locator=%s')"
            % (criteria, locator)
        )
        matches = []
        for pagenum, page in self.rpa_pdf_document.get_pages().items():
            content = page.get_textboxes()
            for c, item in content.items():
                if item.text.lower() == locator.lower():
                    matches.append(item)
        match_count = len(matches)
        if match_count == 1:
            print("Found 1 match for locator '%s'" % locator)
            print(
                "\tbox %d bbox %s text '%s'"
                % (matches[0].boxid, matches[0].bbox, matches[0].text)
            )
            return matches[0]
        elif match_count == 0:
            print("Did not find any matches")
        else:
            print("Found %d matches for locator '%s'" % (match_count, locator))
            for m in matches:
                print("\tbox %d bbox %s text '%s'" % (m.boxid, m.bbox, m.text))
        return False

    def get_value_from_anchor(
        self,
        locator: str,
        direction: str = "right",
        flex: bool = True,
        regexp: str = None,
    ) -> str:
        # ${due date}=  get element from anchor  right
        print(
            "get_value_from_anchor: ('locator=%s', 'direction=%s')"
            % (locator, direction)
        )
        self.set_anchor_to_element(locator)
        if self.anchor_element:
            print("we have anchor", self.anchor_element.bbox)
            (left, bottom, right, top) = self.anchor_element.bbox
            # print(left, top, right, bottom)
            for pagenum, page in self.rpa_pdf_document.get_pages().items():
                content = page.get_textboxes()
                possible = []
                for c, item in content.items():
                    if item.boxid == self.anchor_element.boxid:
                        continue
                    if direction == "right" and item.top == top and item.left > right:
                        print("MATCH")
                        print(item.boxid, item.bbox, item.text)
                        return item.text
                    elif direction == "left" and item.top == top and item.right < left:
                        print("MATCH")
                        print(item.boxid, item.bbox, item.text)
                        return item.text
                    elif direction == "bottom" and item.top < bottom:
                        print("POSSIBLE MATCH")
                        print(item.boxid, item.bbox, item.text)
                        # return (item.boxid, item.text, type(item))
                        if flex and not (item.right <= right or item.left >= left):
                            continue
                        elif flex is False and not (
                            item.right == right or item.left == left
                        ):
                            continue
                        if regexp and re.match(regexp, item.text):
                            possible.append(item)
                        elif regexp is None:
                            possible.append(item)
                    else:
                        print("no match", item.boxid, item.text, item.bbox)
            distance = 500000
            closest = None
            for p in possible:
                if direction == "bottom":
                    distance_y = bottom - p.bottom
                    distance_x = right - p.right
                    calc_distance = math.sqrt(
                        (distance_x * distance_x) + (distance_y * distance_y)
                    )
                    print("DISTANCE: %s (%s)" % (p.text, calc_distance))
                    if calc_distance < distance:
                        distance = calc_distance
                        closest = p
            if len(possible) > 0 and closest:
                return closest.text
            return False

        else:
            print("NO ANCHOR")
            return False
