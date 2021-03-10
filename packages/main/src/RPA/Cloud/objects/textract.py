# pylint: skip-file
# -*- coding: utf-8 -*-
"""Top-level package for amazon-textract-response-parser."""


class BoundingBox:
    def __init__(self, width, height, left, top):
        self._width = width
        self._height = height
        self._left = left
        self._top = top

    def __repr__(self):
        return "width: {}, height: {}, left: {}, top: {}".format(
            self._width, self._height, self._left, self._top
        )

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def left(self):
        return self._left

    @property
    def top(self):
        return self._top


class Polygon:
    def __init__(self, x, y):
        self._x = x
        self._y = y

    def __repr__(self):
        return "x: {}, y: {}".format(self._x, self._y)

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y


class Geometry:
    def __init__(self, geometry):
        boundingBox = geometry["BoundingBox"]
        polygon = geometry["Polygon"]
        bb = BoundingBox(
            boundingBox["Width"],
            boundingBox["Height"],
            boundingBox["Left"],
            boundingBox["Top"],
        )
        pgs = []
        for pg in polygon:
            pgs.append(Polygon(pg["X"], pg["Y"]))

        self._boundingBox = bb
        self._polygon = pgs

    def __repr__(self):
        s = "BoundingBox: {}".format(str(self._boundingBox))
        return s

    @property
    def boundingBox(self):
        return self._boundingBox

    @property
    def polygon(self):
        return self._polygon


class Word:
    def __init__(self, block, blockMap):
        self._block = block
        self._confidence = block["Confidence"]
        self._geometry = Geometry(block["Geometry"])
        self._id = block["Id"]
        self._text = ""
        if block["Text"]:
            self._text = block["Text"]

    def __repr__(self):
        return self._text

    @property
    def confidence(self):
        return self._confidence

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def text(self):
        return self._text

    @property
    def block(self):
        return self._block


class Line:
    def __init__(self, block, blockMap):

        self._block = block
        self._confidence = block["Confidence"]
        self._geometry = Geometry(block["Geometry"])
        self._id = block["Id"]

        self._text = ""
        if block["Text"]:
            self._text = block["Text"]

        self._words = []
        if "Relationships" in block and block["Relationships"]:
            for rs in block["Relationships"]:
                if rs["Type"] == "CHILD":
                    for cid in rs["Ids"]:
                        if blockMap[cid]["BlockType"] == "WORD":
                            self._words.append(Word(blockMap[cid], blockMap))

    def __repr__(self):
        return self._text

    @property
    def confidence(self):
        return self._confidence

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def words(self):
        return self._words

    @property
    def text(self):
        return self._text

    @property
    def block(self):
        return self._block


class SelectionElement:
    def __init__(self, block, blockMap):
        self._confidence = block["Confidence"]
        self._geometry = Geometry(block["Geometry"])
        self._id = block["Id"]
        self._selectionStatus = block["SelectionStatus"]

    @property
    def confidence(self):
        return self._confidence

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def selectionStatus(self):
        return self._selectionStatus


class FieldKey:
    def __init__(self, block, children, blockMap):
        self._block = block
        self._confidence = block["Confidence"]
        self._geometry = Geometry(block["Geometry"])
        self._id = block["Id"]
        self._text = ""
        self._content = []

        t = []

        for eid in children:
            wb = blockMap[eid]
            if wb["BlockType"] == "WORD":
                w = Word(wb, blockMap)
                self._content.append(w)
                t.append(w.text)

        if t:
            self._text = " ".join(t)

    def __repr__(self):
        return self._text

    @property
    def confidence(self):
        return self._confidence

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def content(self):
        return self._content

    @property
    def text(self):
        return self._text

    @property
    def block(self):
        return self._block


class FieldValue:
    def __init__(self, block, children, blockMap):
        self._block = block
        self._confidence = block["Confidence"]
        self._geometry = Geometry(block["Geometry"])
        self._id = block["Id"]
        self._text = ""
        self._content = []

        t = []

        for eid in children:
            wb = blockMap[eid]
            if wb["BlockType"] == "WORD":
                w = Word(wb, blockMap)
                self._content.append(w)
                t.append(w.text)
            elif wb["BlockType"] == "SELECTION_ELEMENT":
                se = SelectionElement(wb, blockMap)
                self._content.append(se)
                self._text = se.selectionStatus

        if t:
            self._text = " ".join(t)

    def __repr__(self):
        return self._text

    @property
    def confidence(self):
        return self._confidence

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def content(self):
        return self._content

    @property
    def text(self):
        return self._text

    @property
    def block(self):
        return self._block


class Field:
    def __init__(self, block, blockMap):
        self._key = None
        self._value = None

        for item in block["Relationships"]:
            if item["Type"] == "CHILD":
                self._key = FieldKey(block, item["Ids"], blockMap)
            elif item["Type"] == "VALUE":
                for eid in item["Ids"]:
                    vkvs = blockMap[eid]
                    if "VALUE" in vkvs["EntityTypes"]:
                        if "Relationships" in vkvs:
                            for vitem in vkvs["Relationships"]:
                                if vitem["Type"] == "CHILD":
                                    self._value = FieldValue(
                                        vkvs, vitem["Ids"], blockMap
                                    )

    def __repr__(self):
        return str({self._key: self._value})

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value


class Form:
    def __init__(self):
        self._fields = []
        self._fieldsMap = {}

    def addField(self, field):
        self._fields.append(field)
        self._fieldsMap[field.key.text] = field

    def __repr__(self):
        return str(self._fields)

    @property
    def fields(self):
        return self._fields

    def getFieldByKey(self, key):
        field = None
        if key in self._fieldsMap:
            field = self._fieldsMap[key]
        return field

    def searchFieldsByKey(self, key):
        searchKey = key.lower()
        results = []
        for field in self._fields:
            if field.key and searchKey in field.key.text.lower():
                results.append(field)
        return results


class Cell:
    def __init__(self, block, blockMap):
        self._block = block
        self._confidence = block["Confidence"]
        self._rowIndex = block["RowIndex"]
        self._columnIndex = block["ColumnIndex"]
        self._rowSpan = block["RowSpan"]
        self._columnSpan = block["ColumnSpan"]
        self._geometry = Geometry(block["Geometry"])
        self._id = block["Id"]
        self._content = []
        self._text = ""
        if "Relationships" in block and block["Relationships"]:
            for rs in block["Relationships"]:
                if rs["Type"] == "CHILD":
                    for cid in rs["Ids"]:
                        blockType = blockMap[cid]["BlockType"]
                        if blockType == "WORD":
                            w = Word(blockMap[cid], blockMap)
                            self._content.append(w)
                            self._text = self._text + w.text + " "
                        elif blockType == "SELECTION_ELEMENT":
                            se = SelectionElement(blockMap[cid], blockMap)
                            self._content.append(se)
                            self._text = self._text + se.selectionStatus + ", "

    def __repr__(self):
        return self._text

    @property
    def confidence(self):
        return self._confidence

    @property
    def rowIndex(self):
        return self._rowIndex

    @property
    def columnIndex(self):
        return self._columnIndex

    @property
    def rowSpan(self):
        return self._rowSpan

    @property
    def columnSpan(self):
        return self._columnSpan

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def content(self):
        return self._content

    @property
    def text(self):
        return self._text

    @property
    def block(self):
        return self._block


class Row:
    def __init__(self):
        self._cells = []

    def __repr__(self):
        return str(self._cells)

    @property
    def cells(self):
        return self._cells


class Table:
    def __init__(self, block, blockMap):

        self._block = block

        self._confidence = block["Confidence"]
        self._geometry = Geometry(block["Geometry"])

        self._id = block["Id"]
        self._rows = []

        ri = 1
        row = Row()
        cell = None
        if "Relationships" in block and block["Relationships"]:
            for rs in block["Relationships"]:
                if rs["Type"] == "CHILD":
                    for cid in rs["Ids"]:
                        cell = Cell(blockMap[cid], blockMap)
                        if cell.rowIndex > ri:
                            self._rows.append(row)
                            row = Row()
                            ri = cell.rowIndex
                        row.cells.append(cell)
                    if row and row.cells:
                        self._rows.append(row)

    def __repr__(self):
        return str(self._rows)

    @property
    def confidence(self):
        return self._confidence

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id

    @property
    def rows(self):
        return self._rows

    @property
    def block(self):
        return self._block


class Page:
    def __init__(self, blocks, blockMap):
        self._blocks = blocks
        self._text = ""
        self._lines = []
        self._form = Form()
        self._tables = []
        self._content = []

        self._parse(blockMap)

    def __repr__(self):
        return str(self._content)

    def _parse(self, blockMap):
        for item in self._blocks:
            if item["BlockType"] == "PAGE":
                self._geometry = Geometry(item["Geometry"])
                self._id = item["Id"]
            elif item["BlockType"] == "LINE":
                line = Line(item, blockMap)
                self._lines.append(line)
                self._content.append(line)
                self._text = self._text + line.text + "\n"
            elif item["BlockType"] == "TABLE":
                t = Table(item, blockMap)
                self._tables.append(t)
                self._content.append(t)
            elif item["BlockType"] == "KEY_VALUE_SET":
                if "KEY" in item["EntityTypes"]:
                    f = Field(item, blockMap)
                    if f.key:
                        self._form.addField(f)
                        self._content.append(f)
                        # TODO. report error if key can't be found
                        # print(
                        #     "WARNING: Detected K/V where key does not have content.
                        # Excluding key from output."
                        # )
                        # print(f)
                        # print(item)

    def getLinesInReadingOrder(self):
        columns = []
        lines = []
        for item in self._lines:
            column_found = False
            for index, column in enumerate(columns):
                bbox_left = item.geometry.boundingBox.left
                bbox_right = (
                    item.geometry.boundingBox.left + item.geometry.boundingBox.width
                )
                bbox_centre = (
                    item.geometry.boundingBox.left + item.geometry.boundingBox.width / 2
                )
                column_centre = column["left"] + column["right"] / 2
                if (bbox_centre > column["left"] and bbox_centre < column["right"]) or (
                    column_centre > bbox_left and column_centre < bbox_right
                ):
                    # Bbox appears inside the column
                    lines.append([index, item.text])
                    column_found = True
                    break
            if not column_found:
                columns.append(
                    {
                        "left": item.geometry.boundingBox.left,
                        "right": item.geometry.boundingBox.left
                        + item.geometry.boundingBox.width,
                    }
                )
                lines.append([len(columns) - 1, item.text])

        lines.sort(key=lambda x: x[0])
        return lines

    def getTextInReadingOrder(self):
        lines = self.getLinesInReadingOrder()
        text = ""
        for line in lines:
            text = text + line[1] + "\n"
        return text

    @property
    def blocks(self):
        return self._blocks

    @property
    def text(self):
        return self._text

    @property
    def lines(self):
        return self._lines

    @property
    def form(self):
        return self._form

    @property
    def tables(self):
        return self._tables

    @property
    def content(self):
        return self._content

    @property
    def geometry(self):
        return self._geometry

    @property
    def id(self):
        return self._id


class TextractDocument:
    def __init__(self, responsePages):
        if not isinstance(responsePages, list):
            rps = []
            rps.append(responsePages)
            responsePages = rps

        self._responsePages = responsePages
        self._pages = []

        self._parse()

    def __repr__(self):
        return str(self._pages)

    def _parseDocumentPagesAndBlockMap(self):
        blockMap = {}

        documentPages = []
        documentPage = None
        for page in self._responsePages:
            for block in page["Blocks"]:
                if "BlockType" in block and "Id" in block:
                    blockMap[block["Id"]] = block

                if block["BlockType"] == "PAGE":
                    if documentPage:
                        documentPages.append({"Blocks": documentPage})
                    documentPage = []
                    documentPage.append(block)
                else:
                    documentPage.append(block)
        if documentPage:
            documentPages.append({"Blocks": documentPage})
        return documentPages, blockMap

    def _parse(self):
        (
            self._responseDocumentPages,
            self._blockMap,
        ) = self._parseDocumentPagesAndBlockMap()
        for documentPage in self._responseDocumentPages:
            page = Page(documentPage["Blocks"], self._blockMap)
            self._pages.append(page)

    @property
    def blocks(self):
        return self._responsePages

    @property
    def pageBlocks(self):
        return self._responseDocumentPages

    @property
    def pages(self):
        return self._pages

    def getBlockById(self, blockId):
        block = None
        if self._blockMap and blockId in self._blockMap:
            block = self._blockMap[blockId]
        return block
