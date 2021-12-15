import re
import sys
import typing
from collections import OrderedDict
from typing import (
    Any,
    Set,
    Iterable,
    Optional,
    Tuple,
    Union,
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


Coords = Tuple[int, ...]


def iterable_items_to_ints(bbox: Optional[Iterable]) -> Coords:
    if bbox is None:
        return ()
    return tuple(map(int, bbox))


class BaseElement:
    """Base class for all kind of elements found in PDFs."""

    def __init__(self, bbox: Optional[Iterable]):
        self._bbox: Coords = iterable_items_to_ints(bbox)
        assert len(self._bbox) == 4, "must be in (left, bottom, right, top) format"

    @property
    def bbox(self) -> Coords:
        return self._bbox

    @property
    def left(self) -> int:
        return self.bbox[0]

    @property
    def bottom(self) -> int:
        return self.bbox[1]

    @property
    def right(self) -> int:
        return self.bbox[2]

    @property
    def top(self) -> int:
        return self.bbox[3]


class Figure(BaseElement):
    """Class for each LTFigure element in the PDF"""

    def __init__(self, item):
        super().__init__(item.bbox)
        self._item = item

    @property
    def item(self):
        return self._item

    def __str__(self) -> str:
        return (
            f'<image src="{self.item.name}" width="{int(self.item.width)}" '
            f'height="{int(self.item.height)}" />'
        )


class TextBox(BaseElement):
    """Class for each LTTextBox element in the PDF."""

    def __init__(self, boxid: int, *, item: Any, trim: bool = True) -> None:
        super().__init__(item.bbox)

        self._boxid = boxid
        self._text = item.get_text()
        if trim:
            self._text = self._text.strip()

    @property
    def boxid(self) -> int:
        return self._boxid

    @property
    def text(self) -> str:
        return self._text

    def __str__(self) -> str:
        return f"{self.text} {self.bbox}"


class Page(BaseElement):
    """Class that abstracts a PDF page."""

    def __init__(self, pageid: int, bbox: Iterable, rotate: int) -> None:
        super().__init__(bbox)

        self.pageid = pageid
        self.rotate = rotate

        self._content = OrderedDict()
        self._content_id = 0
        self._figures = OrderedDict()
        self._textboxes = OrderedDict()

    def add_content(self, content: Any) -> None:
        self._content[self._content_id] = content
        if isinstance(content, Figure):
            content_dict = self._figures
        elif isinstance(content, TextBox):
            content_dict = self._textboxes
        else:
            content_dict = None
        if content_dict is not None:
            content_dict[self._content_id] = content

        self._content_id += 1

    @property
    def content(self) -> OrderedDict:
        return self._content

    @property
    def figures(self) -> OrderedDict:
        return self._figures

    @property
    def textboxes(self) -> OrderedDict:
        return self._textboxes

    @property
    def tag(self) -> str:
        return (
            f'<page id="{self.pageid}" bbox="{bbox2str(self.bbox)}" '
            f'rotate="{self.rotate}">'
        )

    def __str__(self) -> str:
        items_str = "\n".join(self._content.values())
        return f"{self.tag}\n{items_str}"


class Document:
    """Class for the parsed PDF document."""

    ENCODING: str = "utf-8"

    def __init__(self, path: str, *, fileobject: typing.BinaryIO):
        self._path = path
        self._fileobject = fileobject

        self._pages = OrderedDict()
        self._xml_content_list: typing.List[bytes] = []
        self.fields: Optional[dict] = None
        self.has_converted_pages: Set[int] = set()

    @property
    def path(self):
        return self._path

    @property
    def fileobject(self) -> typing.BinaryIO:
        if self._fileobject.closed:
            # pylint: disable=consider-using-with
            self._fileobject = open(self.path, "rb")
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
        *,
        logger,
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
        self.current_page = None
        self.imagewriter = imagewriter
        self.stripcontrol = stripcontrol
        self.trim = trim
        self.write_header()

        self._logger = logger
        self._unique_figures: Set[Tuple[int, str, Coords]] = set()

    def _add_unique_figure(self, figure: Figure):
        figure_key = (self.current_page.pageid, str(figure), figure.bbox)
        if figure_key not in self._unique_figures:
            self.current_page.add_content(figure)
            self._unique_figures.add(figure_key)

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
                self.current_page = Page(item.pageid, item.bbox, item.rotate)
                self.write(self.current_page.tag + "\n")
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
                figure = Figure(item)
                s = '<figure name="%s" bbox="%s">\n' % (
                    item.name,
                    bbox2str(item.bbox),
                )
                self.write(s)
                for child in item:
                    render(child)
                self.write("</figure>\n")
                self._add_unique_figure(figure)
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
                box = TextBox(item.index, item=item, trim=self.trim)
                self.write(s)
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
                figure = Figure(item)
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
                self._add_unique_figure(figure)
            else:
                self._logger.warning("Unknown item: %r", item)

        render(ltpage)

    def close(self):
        self.write_footer()


class ModelKeywords(LibraryContext):
    """Keywords for converting PDF document into specific RPA object model"""

    FIELDS_ENCODING = "iso-8859-1"

    @keyword
    def convert(
        self,
        source_path: str = None,
        trim: bool = True,
        pagenum: Optional[Union[int, str]] = None,
    ):
        """Parse source PDF into entities.

        These entities can be used for text searches or XML dumping for example. The
        conversion will be done automatically when using the dependent keywords
        directly.

        :param source_path: source PDF filepath
        :param trim: trim whitespace from the text is set to True (default)
        :param pagenum: Page number where search is performed on, defaults to `None`. (
            meaning all pages get converted)

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
        converted_pages = self.active_pdf_document.has_converted_pages
        if pagenum is not None:
            pagenum = int(pagenum)
            if pagenum in converted_pages:
                return  # specific page already converted
        else:
            pages_count = self.active_pdf_document.reader.getNumPages()
            if len(converted_pages) >= pages_count:
                return  # all pages got converted already

        self.logger.debug(
            "Converting active PDF document page %s on: %s",
            pagenum if pagenum is not None else "<all>",
            self.active_pdf_document.path,
        )
        rsrcmgr = PDFResourceManager()
        if not self.ctx.convert_settings:
            self.set_convert_settings()
        laparams = pdfminer.layout.LAParams(**self.ctx.convert_settings)
        device = Converter(
            self.active_pdf_document,
            rsrcmgr,
            laparams=laparams,
            trim=trim,
            logger=self.logger,
            # Also explicitly set by us when iterating pages for processing.
            pageno=pagenum if pagenum is not None else 1,
        )
        interpreter = pdfminer.pdfinterp.PDFPageInterpreter(rsrcmgr, device)

        # Look at all (nested) objects on each page.
        source_parser = PDFParser(self.active_pdf_document.fileobject)
        source_document = PDFDocument(source_parser)
        source_pages = PDFPage.create_pages(source_document)
        for idx, page in enumerate(source_pages, start=1):
            # Process relevant pages only if instructed like so.
            # (`pagenum` starts from 1 as well)
            if pagenum is None or idx == pagenum:
                if idx not in converted_pages:
                    # Skipping converted pages will leave this counter un-incremented,
                    # therefore we increment it explicitly.
                    device.pageno = idx
                    interpreter.process_page(page)
                    converted_pages.add(idx)

        device.close()

    @classmethod
    def _decode_field(
        cls, binary: Optional[bytes], *, encoding
    ) -> Optional[Union[str, bytes]]:
        if not (binary and hasattr(binary, "decode")):
            return binary

        try:
            return binary.decode(encoding)
        except UnicodeDecodeError:
            return binary.decode(cls.FIELDS_ENCODING)

    @keyword
    def get_input_fields(
        self,
        source_path: Optional[str] = None,
        replace_none_value: bool = False,
        encoding: str = FIELDS_ENCODING,
    ) -> dict:
        """Get input fields in the PDF.

        Stores input fields internally so that they can be used without parsing the PDF
        again.

        :param source_path: Filepath to source, if not given use the currently active
            PDF.
        :param replace_none_value: Enable this to conveniently visualize the fields. (
            replaces the null value with field's name)
        :param encoding: Use an explicit encoding for field name/value parsing. (
            defaults to "iso-8859-1" but "utf-16" might work for you)
        :returns: A dictionary with all the found fields. Use their key names when
            setting values into them.
        :raises KeyError: If no input fields are enabled in the PDF.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            Example Keyword
                ${fields} =     Get Input Fields    form.pdf
                Log Dictionary    ${fields}

        **Python**

        .. code-block:: python

            from RPA.PDF import PDF

            pdf = PDF()

            def example_keyword():
                fields = pdf.get_input_fields("form.pdf")
                print(fields)

            example_keyword()
        """
        self.ctx.switch_to_pdf(source_path)
        active_document = self.active_pdf_document

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
                % self.active_pdf_document.path
            ) from err

        record_fields = {}
        for miner_field in fields:
            field = pdfminer.pdftypes.resolve1(miner_field)
            if field is None:
                continue

            name, value, raw_rect, label = (
                self._decode_field(field.get("T"), encoding=encoding),
                self._decode_field(field.get("V"), encoding=encoding),
                field.get("Rect"),
                self._decode_field(field.get("TU"), encoding=encoding),
            )
            if value is None and replace_none_value:
                value = name
            parsed_field = {
                "value": value or "",
                "rect": iterable_items_to_ints(raw_rect),
                "label": label or None,
            }
            record_fields[name] = parsed_field

        self.active_pdf_document.fields = record_fields or None
        return record_fields

    @keyword
    def set_field_value(
        self, field_name: str, value: Any, source_path: str = None
    ) -> None:
        """Set value for field with given name on the active document.

        Tries to match with field's identifier directly or its label.

        :param field_name: Field to update.
        :param value: New value for the field.
        :param source_path: Source PDF file path.
        :raises ValueError: When field can't be found or more than one field matches
            the given `field_name`.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

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
        """
        fields = self.get_input_fields(source_path=source_path)
        if not fields:
            raise ValueError("Document does not have input fields")

        if field_name in fields.keys():
            fields[field_name]["value"] = value  # pylint: disable=E1136
        else:
            label_matches = 0
            field_key = None
            for key in fields.keys():
                # pylint: disable=E1136
                if fields[key]["label"] == field_name:
                    label_matches += 1
                    field_key = key
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

        :param source_path: Source PDF with fields to update.
        :param output_path: Updated target PDF.
        :param newvals: New values when updating many at once.
        :param use_appearances_writer: For some PDF documents the updated
            fields won't be visible, try to set this to `True` if you
            encounter problems. (viewing the output PDF in browser might display the
            field values then)

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

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
        """
        # NOTE:
        # The resulting PDF will be a mutated version of the original PDF,
        # and it won't necessarily show correctly in all document viewers.
        # It also won't show anymore as having fields at all.
        # The tests will XFAIL for the time being.
        self.ctx.switch_to_pdf(source_path)
        reader = self.active_pdf_document.reader
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
        elif self.active_pdf_document.fields:
            self.logger.debug("Updating form fields with PDF values for all pages")
            updated_fields = {
                k: v["value"] or ""
                for (k, v) in self.active_pdf_document.fields.items()
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
            output_path = self.active_pdf_document.path
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
