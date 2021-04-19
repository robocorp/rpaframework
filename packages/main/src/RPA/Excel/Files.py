import logging
import pathlib
from collections import defaultdict
from contextlib import contextmanager
from io import BytesIO

import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException

import xlrd
import xlwt
from xlutils.copy import copy as xlutils_copy
from PIL import Image

from RPA.Tables import Tables, Table


def get_column_index(column):
    """Get column index from name, e.g. A -> 1, D -> 4, AC -> 29.
    Reverse of `get_column_letter()`
    """
    column = str(column).lower()

    col = 0
    for digit, char in enumerate(column[::-1]):
        value = ord(char) - 96
        col += (26 ** digit) * value

    return col


def ensure_unique(values):
    """Ensures that each string value in the list is unique.
    Adds a suffix to each value that has duplicates,
    e.g. [Banana, Apple, Lemon, Apple] -> [Banana, Apple, Lemon, Apple_2]
    """

    def to_unique(values):
        output = []
        seen = defaultdict(int)
        for value in values:
            if seen[value] and isinstance(value, str):
                output.append("%s_%d" % (value, seen[value] + 1))
            else:
                output.append(value)
            seen[value] += 1
        return output

    # Repeat process until each column is unique
    output = to_unique(values)
    while True:
        verify = to_unique(output)
        if output == verify:
            break
        output = verify

    return output


class Files:
    """The `Excel.Files` library can be used to read and write Excel
    files without the need to start the actual Excel application.

    It supports both legacy .xls files and modern .xlsx files.

    Note: To run macros or load password protected worksheets,
    please use the Excel application library.

    **Examples**

    **Robot Framework**

    A common use-case is to load an existing Excel file as a table,
    which can be iterated over later in a Robot Framework keyword or task:

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Tables
        Library    RPA.Excel.Files

        *** Keywords ***
        Read orders as table
            Open workbook    ${ORDERS_FILE}
            ${worksheet}=    Read worksheet   header=${TRUE}
            ${orders}=       Create table     ${worksheet}
            [Return]         ${orders}
            [Teardown]       Close workbook

    Processing all worksheets in the Excel file and checking row count:

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Excel.Files

        *** Variables ***
        ${EXCEL_FILE}   /path/to/excel.xlsx

        *** Tasks ***
        Rows in the sheet
            [Setup]      Open Workbook    ${EXCEL_FILE}
            @{sheets}=   List Worksheets
            FOR  ${sheet}  IN   @{sheets}
                ${count}=  Get row count in the sheet   ${sheet}
                Log   Worksheet '${sheet}' has ${count} rows
            END

        *** Keywords ***
        Get row count in the sheet
            [Arguments]      ${SHEET_NAME}
            ${sheet}=        Read Worksheet   ${SHEET_NAME}
            ${rows}=         Get Length  ${sheet}
            [Return]         ${rows}

    Creating a new Excel file with a dictionary:

    .. code-block:: robotframework

        *** Tasks ***
        Creating new Excel
            Create Workbook  my_new_excel.xlsx
            FOR    ${index}    IN RANGE    20
                &{row}=       Create Dictionary
                ...           Row No   ${index}
                ...           Amount   ${index * 25}
                Append Rows to Worksheet  ${row}  header=${TRUE}
            END
            Save Workbook

    Creating a new Excel file with a list:

    .. code-block:: robotframework

        *** Variables ***
        @{heading}   Row No   Amount
        @{rows}      ${heading}

        *** Tasks ***
        Creating new Excel
            Create Workbook  my_new_excel.xlsx
            FOR    ${index}    IN RANGE   1  20
                @{row}=         Create List   ${index}   ${index * 25}
                Append To List  ${rows}  ${row}
            END
            Append Rows to Worksheet  ${rows}
            Save Workbook

    **Python**

    The library can also be imported directly into Python.

    .. code-block:: python

        from RPA.Excel.Files import Files

        def read_excel_worksheet(path, worksheet):
            lib = Files()
            lib.open_workbook(path)
            try:
                return lib.read_worksheet(worksheet)
            finally:
                lib.close_workbook()
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.workbook = None

    def _load_workbook(self, path):
        # pylint: disable=broad-except
        path = pathlib.Path(path).resolve(strict=True)

        try:
            book = XlsxWorkbook(path)
            book.open()
            return book
        except InvalidFileException as exc:
            self.logger.debug(exc)  # Unsupported extension, silently try xlrd
        except Exception as exc:
            self.logger.info(
                "Failed to open as Office Open XML (.xlsx) format: %s", exc
            )

        try:
            book = XlsWorkbook(path)
            book.open()
            return book
        except Exception as exc:
            self.logger.info("Failed to open as Excel Binary Format (.xls): %s", exc)

        raise ValueError(
            f"Failed to open Excel file ({path}), "
            "verify that the path and extension are correct"
        )

    def create_workbook(self, path=None, fmt="xlsx"):
        """Create and open a new Excel workbook.

        Automatically also creates a new worksheet with the name "Sheet".

        :param path: Default save path for workbook
        :param fmt:  Format of workbook, i.e. xlsx or xls
        """
        if self.workbook:
            self.close_workbook()

        fmt = str(fmt).lower().strip()
        if fmt == "xlsx":
            self.workbook = XlsxWorkbook(path)
        elif fmt == "xls":
            self.workbook = XlsWorkbook(path)
        else:
            raise ValueError(f"Unknown format: {fmt}")

        self.workbook.create()
        return self.workbook

    def open_workbook(self, path):
        """Open an existing Excel workbook.

        :param path: path to Excel file
        """
        if self.workbook:
            self.close_workbook()

        self.workbook = self._load_workbook(path)
        self.logger.info("Opened workbook: %s", self.workbook)
        return self.workbook

    def close_workbook(self):
        """Close the active workbook."""
        if self.workbook:
            self.logger.info("Closing workbook: %s", self.workbook)
            self.workbook.close()
            self.workbook = None

    def save_workbook(self, path=None):
        """Save the active workbook.

        :param path: Path to save to. If not given, uses path given
                     when opened or created.
        """
        assert self.workbook, "No active workbook"

        try:
            extension = pathlib.Path(path).suffix
        except TypeError:
            extension = None

        if (
            self.workbook.extension is not None
            and extension is not None
            and self.workbook.extension != extension
        ):
            self.logger.warning(
                "Changed file extension from %s to %s",
                self.workbook.extension,
                extension,
            )

        return self.workbook.save(path)

    def list_worksheets(self):
        """List all names of worksheets in the given workbook."""
        assert self.workbook, "No active workbook"
        return self.workbook.sheetnames

    def worksheet_exists(self, name):
        """Return True if worksheet with given name is in workbook."""
        assert self.workbook, "No active workbook"
        return bool(str(name) in self.list_worksheets())

    def get_active_worksheet(self):
        """Get the name of the worksheet which is currently active."""
        assert self.workbook, "No active workbook"
        return self.workbook.active

    def set_active_worksheet(self, value):
        """Set the active worksheet.

        :param value: Index or name of worksheet
        """
        assert self.workbook, "No active workbook"
        self.workbook.active = value

    def create_worksheet(self, name, content=None, exist_ok=False, header=False):
        """Create a new worksheet in the current workbook.

        :param name:     Name of new worksheet
        :param content:  Optional content for worksheet
        :param exist_ok: If `False`, raise an error if name is already in use
        :param header:   If content is provided, write headers to worksheet
        """
        assert self.workbook, "No active workbook"
        if name in self.workbook.sheetnames and not exist_ok:
            raise ValueError(f"Sheet with name {name} already exists")

        self.workbook.create_worksheet(name)
        if content:
            self.workbook.append_worksheet(name, content, header)

    def read_worksheet(self, name=None, header=False, start=None):
        """Read the content of a worksheet into a list of dictionaries.

        Each key in the dictionary will be either values from the header row,
        or Excel-style column letters.

        :param name:   Name of worksheet to read
        :param header: If `True`, use the first row of the worksheet
                       as headers for the rest of the rows.
        """
        assert self.workbook, "No active workbook"
        return self.workbook.read_worksheet(name, header, start)

    def read_worksheet_as_table(self, name=None, header=False, trim=True, start=None):
        """Read the content of a worksheet into a Table container. Allows
        sorting/filtering/manipulating using the `RPA.Tables` library.

        :param name:   Name of worksheet to read
        :param header: If `True`, use the first row of the worksheet
                       as headers for the rest of the rows.
        :param trim:   Remove all empty rows from the end of the worksheet
        :param start:  Row index to start reading data from (1-indexed)
        """
        tables = Tables()
        sheet = self.read_worksheet(name, header, start)
        return tables.create_table(sheet, trim)

    def append_rows_to_worksheet(self, content, name=None, header=False, start=None):
        """Append values to the end of the worksheet.

        :param content: Rows of values to append
        :param name:    Name of worksheet to append to
        :param header:  Set rows according to existing header row
        :param start:   Start of data, NOTE: Only required when headers is True
        """
        assert self.workbook, "No active workbook"
        return self.workbook.append_worksheet(name, content, header, start)

    def remove_worksheet(self, name=None):
        """Remove a worksheet from the active workbook.

        :param name: Name of worksheet to remove
        """
        assert self.workbook, "No active workbook"
        self.workbook.remove_worksheet(name)

    def rename_worksheet(self, src_name, dst_name):
        """Rename an existing worksheet in the active workbook.

        :param src_name: Current name of worksheet
        :param dst_name: Future name of worksheet
        """
        assert self.workbook, "No active workbook"
        self.workbook.rename_worksheet(dst_name, src_name)

    def find_empty_row(self, name=None):
        """Find the first empty row after existing content.

        :param name:    Name of worksheet
        """
        assert self.workbook, "No active workbook"
        return self.workbook.find_empty_row(name)

    def get_worksheet_value(self, row, column, name=None):
        """Get a cell value in the given worksheet.

        :param row:     Index of row to read, e.g. 3
        :param column:  Name or index of column, e.g. C or 7
        :param name:    Name of worksheet (optional)
        """
        assert self.workbook, "No active workbook"
        return self.workbook.get_cell_value(row, column, name)

    def set_worksheet_value(self, row, column, value, name=None):
        """Set a cell value in the given worksheet.

        :param row:     Index of row to write, e.g. 3
        :param column:  Name or index of column, e.g. C or 7
        :param value:   New value of cell
        :param name:    Name of worksheet (optional)
        """
        assert self.workbook, "No active workbook"
        self.workbook.set_cell_value(row, column, value, name)

    def insert_image_to_worksheet(self, row, column, path, scale=1.0, name=None):
        """Insert an image into the given cell.

        :param row:     Index of row to write
        :param column:  Name or index of column
        :param image:   Path to image file
        :param scale:   Scale of image
        :param name:    Name of worksheet
        """
        assert self.workbook, "No active workbook"
        image = Image.open(path)

        if scale != 1.0:
            fmt = image.format
            width = int(image.width * float(scale))
            height = int(image.height * float(scale))
            image = image.resize((width, height), Image.ANTIALIAS)
            image.format = fmt

        self.workbook.insert_image(row, column, image, name)


class XlsxWorkbook:
    """Container for manipulating moden Excel files (.xlsx)"""

    def __init__(self, path=None):
        self.logger = logging.getLogger(__name__)
        self.path = path
        self._book = None
        self._extension = None
        self._active = None

    @property
    def sheetnames(self):
        return list(self._book.sheetnames)

    @property
    def active(self):
        if not self._active:
            self._active = self._book.active.title

        return self._active

    @active.setter
    def active(self, value):
        if isinstance(value, int):
            value = self.sheetnames[value]
        elif value not in self.sheetnames:
            raise ValueError(f"Unknown worksheet: {value}")

        self._book.active = self.sheetnames.index(value)
        self._active = value

    @property
    def extension(self):
        return self._extension

    def _get_sheetname(self, name=None):
        if not self.sheetnames:
            raise ValueError("No worksheets in file")

        if name is None:
            name = self.active
        elif isinstance(name, int):
            name = self.sheetnames[name]

        return name

    def _get_cellname(self, row, column):
        row = int(row)
        try:
            column = int(column)
            column = get_column_letter(column)
        except ValueError:
            pass
        return "%s%s" % (column, row)

    def _to_index(self, value):
        value = int(value) if value is not None else 1
        if value < 1:
            raise ValueError("Invalid row index")
        return value

    def create(self):
        self._book = openpyxl.Workbook()
        self._extension = None

    def open(self, path=None):
        path = path or self.path

        if not path:
            raise ValueError("No path defined for workbook")

        try:
            extension = pathlib.Path(path).suffix
        except TypeError:
            extension = None

        if extension in (".xlsm", ".xltm"):
            self._book = openpyxl.load_workbook(filename=path, keep_vba=True)
        else:
            self._book = openpyxl.load_workbook(filename=path)

        self._extension = extension

    def close(self):
        self._book.close()
        self._book = None
        self._extension = None
        self._active = None

    def save(self, path=None):
        path = path or self.path
        if not path:
            raise ValueError("No path defined for workbook")

        self._book.save(filename=path)

    def create_worksheet(self, name):
        self._book.create_sheet(title=name)
        self.active = name

    def read_worksheet(self, name=None, header=False, start=None):
        name = self._get_sheetname(name)
        sheet = self._book[name]
        start = self._to_index(start)

        if header:
            columns = [cell.value for cell in sheet[start]]
            start += 1
        else:
            columns = [get_column_letter(i + 1) for i in range(sheet.max_column)]

        columns = ensure_unique(columns)

        data = []
        for cells in sheet.iter_rows(min_row=start):
            row = {}
            for c, cell in enumerate(cells):
                column = columns[c]
                if column is not None:
                    row[column] = cell.value
            data.append(row)

        self.active = name
        return data

    def append_worksheet(self, name=None, content=None, header=False, start=None):
        content = Table(content)
        if not content:
            return

        name = self._get_sheetname(name)
        sheet = self._book[name]
        start = self._to_index(start)
        is_empty = sheet.max_row <= 1 and sheet.max_column <= 1

        if header and not is_empty:
            columns = [cell.value for cell in sheet[start]]
        else:
            columns = content.columns

        if header and is_empty:
            sheet.append(columns)

        for row in content:
            values = [""] * len(columns)
            for column, value in row.items():
                try:
                    index = columns.index(column)
                    values[index] = value
                except ValueError:
                    pass
            sheet.append(values)

        self.active = name

    def remove_worksheet(self, name=None):
        name = self._get_sheetname(name)
        sheet = self._book[name]
        self._book.remove(sheet)

    def rename_worksheet(self, title, name=None):
        title = str(title)
        name = self._get_sheetname(name)
        sheet = self._book[name]

        sheet.title = title
        self.active = title

    def find_empty_row(self, name=None):
        name = self._get_sheetname(name)
        sheet = self._book[name]

        for idx in reversed(range(sheet.max_row)):
            idx += 1  # Convert to 1-based indexing
            if any(value for value in sheet[idx]):
                return idx + 1  # Return first empty row

        return 1

    def get_cell_value(self, row, column, name=None):
        name = self._get_sheetname(name)
        sheet = self._book[name]
        cell = self._get_cellname(row, column)

        return sheet[cell].value

    def set_cell_value(self, row, column, value, name=None):
        name = self._get_sheetname(name)
        sheet = self._book[name]
        cell = self._get_cellname(row, column)

        sheet[cell] = value

    def insert_image(self, row, column, image, name=None):
        name = self._get_sheetname(name)
        sheet = self._book[name]
        cell = self._get_cellname(row, column)

        # For compatibility with openpyxl
        stream = BytesIO()
        image.save(stream, format=image.format)
        image.fp = stream

        img = openpyxl.drawing.image.Image(image)
        img.anchor = cell
        sheet.add_image(img)


class XlsWorkbook:
    """Container for manipulating legacy Excel files (.xls)"""

    def __init__(self, path=None):
        self.logger = logging.getLogger(__name__)
        self.path = path
        self._book = None
        self._extension = None
        self._active = None
        self._images = []

    @property
    def sheetnames(self):
        return [sheet.name for sheet in self._book.sheets()]

    @property
    def active(self):
        if not self._active:
            for sheet in self._book.sheets():
                if sheet.sheet_visible:
                    self._active = sheet.name
                    break
            else:
                self._active = self.sheetnames[0]

        return self._active

    @active.setter
    def active(self, value):
        if isinstance(value, int):
            value = self.sheetnames[value]
        elif value not in self.sheetnames:
            raise ValueError(f"Unknown worksheet: {value}")

        for sheet in self._book.sheets():
            match = int(sheet.name == value)
            sheet.sheet_selected = match
            sheet.sheet_visible = match

        self._active = value

    @property
    def extension(self):
        return self._extension

    def _get_sheetname(self, name):
        if self._book.nsheets == 0:
            raise ValueError("No worksheets in file")

        if name is None:
            name = self.active
        elif isinstance(name, int):
            name = self.sheetnames[name]
        elif name not in self.sheetnames:
            raise ValueError(f"Unknown worksheet: {name}")

        return name

    def _get_cell(self, row, column):
        row = int(row)
        try:
            column = int(column)
        except ValueError:
            column = get_column_index(column)
        return row - 1, column - 1

    def _to_index(self, value):
        value = (int(value) - 1) if value is not None else 0
        if value < 0:
            raise ValueError("Invalid row index")
        return value

    def create(self, sheet="Sheet"):
        fd = BytesIO()
        try:
            book = xlwt.Workbook()
            book.add_sheet(sheet)
            book.save(fd)
            fd.seek(0)
            self.open(fd)
        finally:
            fd.close()

        self._extension = None

    def open(self, path_or_file=None):
        path_or_file = path_or_file or self.path

        options = {"on_demand": True, "formatting_info": True}

        if hasattr(path_or_file, "read"):
            options["file_contents"] = path_or_file.read()
            extension = None
        else:
            options["filename"] = path_or_file
            extension = pathlib.Path(path_or_file).suffix

        self._book = xlrd.open_workbook(**options)
        self._extension = extension
        self._images = []

    def close(self):
        self._book.release_resources()
        self._book = None
        self._extension = None
        self._active = None
        self._images = []

    @contextmanager
    def _book_write(self):
        book = xlutils_copy(self._book)
        yield book

        fd = BytesIO()
        try:
            book.save(fd)
            fd.seek(0)
            self.close()
            self.open(fd)
        finally:
            fd.close()

    def save(self, path=None):
        path = path or self.path
        if not path:
            raise ValueError("No path defined for workbook")

        book = xlutils_copy(self._book)
        self._insert_images(book)
        book.save(path)

    def create_worksheet(self, name):
        with self._book_write() as book:
            book.add_sheet(name)

        self.active = name

    def read_worksheet(self, name=None, header=False, start=None):
        name = self._get_sheetname(name)
        sheet = self._book.sheet_by_name(name)
        start = self._to_index(start)

        if header:
            columns = [
                cell.value if cell.value != "" else None for cell in sheet.row(start)
            ]
            start += 1
        else:
            columns = [get_column_letter(i + 1) for i in range(sheet.ncols)]

        columns = ensure_unique(columns)

        data = []
        for r in range(start, sheet.nrows):
            row = {}
            for c in range(sheet.ncols):
                column = columns[c]
                if column is not None:
                    cell = sheet.cell(r, c)
                    row[column] = self._parse_type(cell)
            data.append(row)

        self.active = name
        return data

    def _parse_type(self, cell):
        value = cell.value

        if cell.ctype == xlrd.XL_CELL_DATE:
            value = xlrd.xldate_as_datetime(value, self._book.datemode)
        elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
            value = bool(value)
        elif cell.ctype == xlrd.XL_CELL_ERROR:
            value = xlrd.biffh.error_text_from_code.get(value, "#ERROR")
        elif cell.ctype == xlrd.XL_CELL_NUMBER and value.is_integer():
            value = int(value)

        return value

    def append_worksheet(self, name=None, content=None, header=False, start=None):
        content = Table(content)
        if not content:
            return

        name = self._get_sheetname(name)
        sheet_read = self._book.sheet_by_name(name)
        start = self._to_index(start)
        is_empty = sheet_read.ncols <= 1 and sheet_read.nrows <= 1

        if header and not is_empty:
            columns = [cell.value for cell in sheet_read.row(start)]
        else:
            columns = content.columns

        with self._book_write() as book:
            sheet_write = book.get_sheet(name)
            start_row = sheet_read.nrows

            if header and is_empty:
                for column, value in enumerate(columns):
                    sheet_write.write(0, column, value)
                start_row += 1

            for r, row in enumerate(content, start_row):
                for column, value in row.items():
                    sheet_write.write(r, columns.index(column), value)

        self.active = name

    def remove_worksheet(self, name=None):
        name = self._get_sheetname(name)

        if name == self.active:
            self.active = self.sheetnames[0]

        with self._book_write() as book:
            # This is pretty ugly, but there seems to be no other way to
            # remove sheets from the xlwt.Workbook instance
            # pylint: disable=protected-access
            book._Workbook__worksheets = [
                sheet for sheet in book._Workbook__worksheets if sheet.name != name
            ]

    def rename_worksheet(self, title, name=None):
        title = str(title)
        name = self._get_sheetname(name)

        with self._book_write() as book:
            sheet = book.get_sheet(name)
            sheet.name = title

        self.active = title

    def find_empty_row(self, name=None):
        name = self._get_sheetname(name)
        sheet = self._book.sheet_by_name(name)

        for row in reversed(range(sheet.nrows)):
            if any(cell.value for cell in sheet.row(row)):
                # Convert to 1-based indexing and
                # return first empty row
                return row + 2

        return 1

    def get_cell_value(self, row, column, name=None):
        name = self._get_sheetname(name)
        sheet = self._book.sheet_by_name(name)
        row, column = self._get_cell(row, column)

        return sheet.cell_value(row, column)

    def set_cell_value(self, row, column, value, name=None):
        name = self._get_sheetname(name)
        row, column = self._get_cell(row, column)

        with self._book_write() as book:
            sheet = book.get_sheet(name)
            sheet.write(row, column, value)

    def insert_image(self, row, column, image, name=None):
        name = self._get_sheetname(name)
        row, column = self._get_cell(row, column)
        self._images.append((name, row, column, image))

    def _insert_images(self, book):
        for name, row, column, image in self._images:
            stream = BytesIO()
            image.save(stream, format="BMP")
            bitmap = stream.getvalue()

            sheet = book.get_sheet(name)
            sheet.insert_bitmap_data(bitmap, row, column)
