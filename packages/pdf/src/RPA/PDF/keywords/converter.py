import re
import sys
from typing import Any, Iterable

from collections import OrderedDict
from pdfminer.converter import PDFConverter
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
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.utils import enc, bbox2str


from RPA.PDF.keywords import (
    LibraryContext,
    keyword,
)


def iterable_items_to_int(bbox):
    if bbox is None:
        return list()
    return list(map(int, bbox))


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
        return f"{self.text} {self.bbox}"


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
        self.content = OrderedDict()
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


class RpaPdfDocument:
    """Class for parsed PDF document"""

    encoding: str = "utf-8"
    pages: OrderedDict
    xml_content: bytearray = bytearray()

    def __init__(self) -> None:
        self.pages = OrderedDict()

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


class ConverterKeywords(LibraryContext):
    """Keywords for converting PDF document into specific RPA object model"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.active_fileobject = None

    @keyword
    def convert(self, source_pdf: str = None) -> None:
        """Parse source PDF into entities which can be
        used for text searches for example.

        :param source_pdf: source
        """
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

    @keyword
    def pdf_to_image(self, pdf_document: str = None, pages=None, target_file: str = ""):
        pass
