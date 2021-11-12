import re
import sys
import typing
from collections import OrderedDict
from typing import (
    Any,
    Iterable,
    Optional,
)

import PyPDF2
import pdfminer
from pdfminer.converter import PDFConverter
from pdfminer.layout import (
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
from pdfminer.utils import enc, bbox2str
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import (
    PDFResourceManager,
)

from RPA.PDF.keywords import (
    LibraryContext,
    keyword,
)


def iterable_items_to_int(bbox) -> list:
    if bbox is None:
        return []
    return list(map(int, bbox))


class Figure:
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

    def details(self) -> str:
        return '<image src="%s" width="%d" height="%d" />' % (
            self.image_name or self.figure_name,
            self.item.width,
            self.item.height,
        )


class TextBox:
    """Class for each LTTextBox element in the PDF"""

    item: dict
    textbox_bbox: list
    textbox_id: int
    textbox_wmode: str

    def __init__(
        self, boxid: int, bbox: Iterable, wmode: str, trim: bool = True
    ) -> None:
        self.textbox_id = boxid
        self.textbox_bbox = iterable_items_to_int(bbox)
        self.textbox_wmode = wmode
        self.trim = trim

    def set_item(self, item: Any):
        text = item.get_text()
        self.item = {
            "bbox": iterable_items_to_int(item.bbox),
            "text": text.strip() if self.trim else text,
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


class Page:
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
        return {k: v for k, v in self.content.items() if isinstance(v, Figure)}

    def get_textboxes(self) -> OrderedDict:
        return {k: v for k, v in self.content.items() if isinstance(v, TextBox)}

    def __str__(self) -> str:
        page_as_str = '<page id="%s" bbox="%s" rotate="%d">\n' % (
            self.pageid,
            bbox2str(self.bbox),
            self.rotate,
        )
        for _, c in self.content.items():
            page_as_str += f"{c}\n"
        return page_as_str


class Document:
    """Class for the parsed PDF document."""

    ENCODING: str = "utf-8"

    def __init__(self, path: str, *, fileobject: typing.BinaryIO):
        self._path = path
        self._fileobject = fileobject

        self._pages = OrderedDict()
        self._xml_content_list: typing.List[bytes] = []
        self.fields: Optional[dict] = None
        self.is_converted = False

    @property
    def path(self):
        return self._path

    @property
    def fileobject(self) -> typing.BinaryIO:
        self._fileobject.seek(0, 0)
        return self._fileobject

    @property
    def reader(self) -> PyPDF2.PdfFileReader:
        """Get a PyPDF reader instance for the PDF."""
        return PyPDF2.PdfFileReader(self.fileobject, strict=False)

    def add_page(self, page: Page) -> None:
        self._pages[page.pageid] = page

    def get_pages(self) -> OrderedDict:
        return self._pages

    def get_page(self, pagenum: int) -> Page:
        return self._pages[pagenum]

    def append_xml(self, xml: bytes) -> None:
        self._xml_content_list.append(xml)

    def dump_xml(self) -> str:
        return b"".join(self._xml_content_list).decode(self.ENCODING)

    def close(self):
        self._fileobject.close()


class Converter(PDFConverter):
    """Class for converting PDF into RPA classes"""

    CONTROL = re.compile("[\x00-\x08\x0b-\x0c\x0e-\x1f]")

    def __init__(
        self,
        active_document: Document,
        rsrcmgr,
        codec: str = "utf-8",
        pageno: int = 1,
        laparams=None,
        imagewriter=None,
        stripcontrol=False,
        trim=True,
    ):
        super().__init__(
            rsrcmgr, sys.stdout, codec=codec, pageno=pageno, laparams=laparams
        )
        self.active_pdf_document = active_document
        self.figure = None
        self.current_page = None
        self.imagewriter = imagewriter
        self.stripcontrol = stripcontrol
        self.trim = trim
        self.write_header()

    def write(self, text: str):
        if self.codec:
            text = text.encode(self.codec)
        else:
            text = text.encode()
        self.active_pdf_document.append_xml(text)

    def write_header(self):
        if self.codec:
            self.write('<?xml version="1.0" encoding="%s" ?>\n' % self.codec)
        else:
            self.write('<?xml version="1.0" ?>\n')
        self.write("<pages>\n")

    def write_footer(self):
        self.write("</pages>\n")

    def write_text(self, text: str):
        if self.stripcontrol:
            text = self.CONTROL.sub("", text)
        self.write(enc(text))

    def receive_layout(self, ltpage: LTPage):  # noqa: C901 pylint: disable=R0915
        # TODO: document this
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
                self.current_page = Page(item.pageid, item.bbox, item.rotate)

                self.write(s)
                for child in item:
                    render(child)
                if item.groups is not None:
                    self.write("<layout>\n")
                    for group in item.groups:
                        show_group(group)
                    self.write("</layout>\n")
                self.write("</page>\n")
                self.active_pdf_document.add_page(self.current_page)
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
                self.figure = Figure(item.name, item.bbox)
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
                box = TextBox(item.index, item.bbox, wmode, self.trim)
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


class ModelKeywords(LibraryContext):
    """Keywords for converting PDF document into specific RPA object model"""

    @keyword
    def convert(self, source_path: str = None, trim: bool = True) -> None:
        """Parse source PDF into entities.

        These entities can be used for text searches or XML dumping for example. The
        conversion will be done automatically when using the dependent keywords
        directly.

        :param source_path: source PDF filepath
        :param trim: trim whitespace from the text is set to True (default)

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                Convert    /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                pdf.convert("/tmp/sample.pdf")
        """
        self.ctx.switch_to_pdf(source_path)
        if self.ctx.active_pdf_document.is_converted:
            return

        self.logger.debug(
            "Converting active PDF document: %s", self.ctx.active_pdf_document.path
        )
        rsrcmgr = PDFResourceManager()
        if not self.ctx.convert_settings:
            self.set_convert_settings()
        laparams = pdfminer.layout.LAParams(**self.ctx.convert_settings)
        device = Converter(
            self.ctx.active_pdf_document, rsrcmgr, laparams=laparams, trim=trim
        )
        interpreter = pdfminer.pdfinterp.PDFPageInterpreter(rsrcmgr, device)

        # Look at all (nested) objects on each page.
        source_parser = PDFParser(self.ctx.active_pdf_document.fileobject)
        source_document = PDFDocument(source_parser)
        source_pages = PDFPage.create_pages(source_document)
        for _, page in enumerate(source_pages, 0):
            interpreter.process_page(page)
        device.close()

        self.ctx.active_pdf_document.is_converted = True

    @keyword
    def get_input_fields(
        self, source_path: str = None, replace_none_value: bool = False
    ) -> dict:
        """Get input fields in the PDF.

        Stores input fields internally so that they can be used without
        parsing the PDF again.

        Parameter ``replace_none_value`` is for convience to visualize fields.

        If no source path given, assumes a PDF is already opened.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                ${fields}=  Get Input Fields    /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                fields = pdf.get_input_fields("/tmp/sample.pdf")

        :param source_path: source filepath, defaults to None.
        :param replace_none_value: if value is None replace it with key name,
            defaults to False.
        :return: dictionary of input key values or `None`.
        """
        self.ctx.switch_to_pdf(source_path)
        active_document = self.ctx.active_pdf_document

        active_fields = active_document.fields
        if active_fields:
            return active_fields

        source_parser = PDFParser(active_document.fileobject)
        source_document = PDFDocument(source_parser)

        try:
            fields = pdfminer.pdftypes.resolve1(source_document.catalog["AcroForm"])[
                "Fields"
            ]
        except KeyError as err:
            raise KeyError(
                'PDF "%s" does not have any input fields.'
                % self.ctx.active_pdf_document.path
            ) from err

        record_fields = {}
        for miner_field in fields:
            field = pdfminer.pdftypes.resolve1(miner_field)
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

        self.ctx.active_pdf_document.fields = record_fields or None
        return record_fields

    @keyword
    def set_field_value(
        self, field_name: str, value: Any, source_path: str = None
    ) -> None:
        """Set value for field with given name on the active document.

        Tries to match on field identifier and its label.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                Open PDF    ./tmp/sample.pdf
                Set Field Value    phone_nr    077123123
                Save Field Values    output_path=./tmp/output.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                pdf.open_pdf("./tmp/sample.pdf")
                pdf.set_field_value("phone_nr", "077123123")
                pdf.save_field_values(output_path="./tmp/output.pdf")

        :param field_name: field to update.
        :param value: new value for the field.
        :param source_path: source PDF filepath.
        :raises ValueError: when field can't be found or more than 1 field matches
            the given `field_name`.
        """
        fields = self.get_input_fields(source_path=source_path)
        if not fields:
            raise ValueError("Document does not have input fields")

        if field_name in fields.keys():
            fields[field_name]["value"] = value  # pylint: disable=E1136
        else:
            label_matches = 0
            field_key = None
            for k, _ in fields.items():
                # pylint: disable=E1136
                if fields[k]["label"] == field_name:
                    label_matches += 1
                    field_key = k
            if label_matches == 1:
                fields[field_key]["value"] = value  # pylint: disable=E1136
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

    @keyword
    def save_field_values(
        self,
        source_path: str = None,
        output_path: str = None,
        newvals: dict = None,
        use_appearances_writer: bool = False,
    ) -> None:
        """Save field values in PDF if it has fields.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                Open PDF    ./tmp/sample.pdf
                Set Field Value    phone_nr    077123123
                Save Field Values    output_path=./tmp/output.pdf

            Multiple operations
                &{new_fields}=       Create Dictionary
                ...                  phone_nr=077123123
                ...                  title=dr
                Save Field Values    source_path=./tmp/sample.pdf
                ...                  output_path=./tmp/output.pdf
                ...                  newvals=${new_fields}

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                pdf.open_pdf("./tmp/sample.pdf")
                pdf.set_field_value("phone_nr", "077123123")
                pdf.save_field_values(output_path="./tmp/output.pdf")

            def multiple_operations():
                new_fields = {"phone_nr": "077123123", "title": "dr"}
                pdf.save_field_values(
                    source_path="./tmp/sample.pdf",
                    output_path="./tmp/output.pdf",
                    newvals=new_fields
                )

        :param source_path: source PDF with fields to update
        :param output_path: updated target PDF
        :param newvals: new values when updating many at once
        :param use_appearances_writer: for some PDF documents the updated
            fields won't be visible, try to set this to `True` if you
            encounter problems
        """
        # NOTE:
        # The resulting PDF will be a mutated version of the original PDF,
        # and it won't necessarily show correctly in all document viewers.
        # It also won't show anymore as having fields at all.
        # The tests will XFAIL for the time being.

        self.ctx.switch_to_pdf(source_path)
        reader = self.ctx.active_pdf_document.reader
        if "/AcroForm" in reader.trailer["/Root"]:
            reader.trailer["/Root"]["/AcroForm"].update(
                {
                    PyPDF2.generic.NameObject(
                        "/NeedAppearances"
                    ): PyPDF2.generic.BooleanObject(True)
                }
            )

        writer = PyPDF2.PdfFileWriter()
        if use_appearances_writer:
            writer = self._set_need_appearances_writer(writer)
        if newvals:
            self.logger.debug("Updating form fields with provided values for all pages")
            updated_fields = newvals
        elif self.ctx.active_pdf_document.fields:
            self.logger.debug("Updating form fields with PDF values for all pages")
            updated_fields = {
                k: v["value"] or ""
                for (k, v) in self.ctx.active_pdf_document.fields.items()
            }
        else:
            self.logger.debug("No values available for updating the form fields")
            updated_fields = {}

        for idx in range(reader.getNumPages()):
            page = reader.getPage(idx)
            if updated_fields:
                try:
                    writer.updatePageFormFieldValues(page, fields=updated_fields)
                except Exception as exc:  # pylint: disable=W0703
                    self.logger.warning(repr(exc))
            writer.addPage(page)

        if output_path is None:
            output_path = self.ctx.active_pdf_document.path
        with open(output_path, "wb") as stream:
            writer.write(stream)

    def _set_need_appearances_writer(self, writer: PyPDF2.PdfFileWriter):
        # See 12.7.2 and 7.7.2 for more information:
        # http://www.adobe.com/content/dam/acom/en/devnet/acrobat/pdfs/PDF32000_2008.pdf
        try:
            catalog = writer._root_object  # pylint: disable=W0212
            # get the AcroForm tree
            if "/AcroForm" not in catalog:
                catalog.update(
                    {
                        PyPDF2.generic.NameObject(
                            "/AcroForm"
                        ): PyPDF2.generic.IndirectObject(
                            len(writer._objects), 0, writer  # pylint: disable=W0212
                        )
                    }
                )

            need_appearances = PyPDF2.generic.NameObject("/NeedAppearances")
            catalog["/AcroForm"][need_appearances] = PyPDF2.generic.BooleanObject(True)
            return writer

        except Exception:  # pylint: disable=broad-except
            self.logger.exception()
            return writer

    @keyword
    def dump_pdf_as_xml(self, source_path: str = None) -> str:
        """Get PDFMiner format XML dump of the PDF

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                ${xml}=  Dump PDF as XML    /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                xml = pdf.dump_pdf_as_xml("/tmp/sample.pdf")

        :param source_path: filepath to the source PDF
        :return: XML content as a string
        """
        self.convert(source_path)
        return self.active_pdf_document.dump_xml()

    @keyword
    def set_convert_settings(
        self,
        line_margin: float = None,
        word_margin: float = None,
        char_margin: float = None,
    ):
        """Change settings for PDFMiner document conversion.

        `line_margin` controls how textboxes are grouped - if conversion results in
        texts grouped into one group then set this to lower value

        `word_margin` controls how spaces are inserted between words - if conversion
        results in text without spaces then set this to lower value

        `char_margin` controls how characters are grouped into words - if conversion
        results in individual characters instead of then set this to higher value

        :param line_margin: relative margin between bounding lines, default 0.5
        :param word_margin: relative margin between words, default 0.1
        :param char_margin: relative margin between characters, default 2.0

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ***Settings***
            Library    RPA.PDF

            ***Tasks***
            Example Keyword
                Set Convert Settings  line_margin=0.00000001
                ${texts}=  Get Text From PDF  /tmp/sample.pdf

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                pdf.set_convert_settings(line_margin=)
                texts = pdf.get_text_from_pdf("/tmp/sample.pdf")
        """
        self.ctx.convert_settings["detect_vertical"] = True
        self.ctx.convert_settings["all_texts"] = True
        if line_margin:
            self.ctx.convert_settings["line_margin"] = line_margin
        if char_margin:
            self.ctx.convert_settings["char_margin"] = char_margin
        if word_margin:
            self.ctx.convert_settings["word_margin"] = word_margin
