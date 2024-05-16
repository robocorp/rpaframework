from dataclasses import dataclass
from enum import Enum
import functools
from itertools import count
from random import randint
from typing import Any, Dict, List, Union

from RPA.application import (
    BaseApplication,
    catch_com_error,
    to_path,
    to_str_path,
    constants,
)
from RPA.Tables import Table


def requires_workbook(func):
    """Ensures a workbook is open."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.workbook is None:
            raise ValueError("No workbook open")
        return func(self, *args, **kwargs)

    return wrapper


class SearchOrder(Enum):
    """Enumeration for search order."""

    ROWS = "ROWS"
    COLUMNS = "COLUMNS"


@dataclass
class PivotField:
    """Data class for pivot field parameters."""

    data_column: str
    operation: str
    numberformat: str


def to_pivot_operation(operation_name: str):
    result = None
    if operation_name.upper() == "SUM":
        result = constants.xlSum
    elif operation_name.upper() == "AVERAGE":
        result = constants.xlAverage
    elif operation_name.upper() == "MAX":
        result = constants.xlMax
    elif operation_name.upper() == "MIN":
        result = constants.xlMin
    elif operation_name.upper() == "COUNT":
        result = constants.xlCount
    elif operation_name.upper() == "DISTINCT COUNT":
        result = constants.xlDistinctCount
    return result


def to_look_in(look_in: str):
    result = None
    if look_in.upper() == "FORMULAS":
        result = constants.xlFormulas
    elif look_in.upper() == "VALUES":
        result = constants.xlValues
    elif look_in.upper() == "COMMENTS":
        result = constants.xlComments
    elif look_in.upper() == "COMMENTS THREADED":
        result = constants.xlCommentsThreaded
    return result


def _split_rows_into_range_blocks(rows, ranges):
    range_blocks = []
    start = 0
    for r in ranges:
        end = start + r.Columns.Count
        range_blocks.append((start, end))
        start = end
    return [[row[i:j] for row in rows] for i, j in range_blocks]


def _get_rows_from_table(table_object: Table):
    rows = []
    for index in table_object.index:
        row = []
        for column in table_object._columns:  # pylint: disable=protected-access
            row.append(table_object.get_cell(index, column))
        rows.append(row)
    return rows


class Application(BaseApplication):
    """`Excel.Application` is a library for controlling the Excel application.

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library             RPA.Excel.Application
        Task Setup          Open Application
        Task Teardown       Quit Application

        *** Tasks ***
        Manipulate Excel application
            Open Workbook           workbook.xlsx
            Set Active Worksheet    sheetname=new stuff
            Write To Cells          row=1
            ...                     column=1
            ...                     value=my data
            Save Excel

        Run Excel Macro
            Open Workbook   orders_with_macro.xlsm
            Run Macro       Sheet1.CommandButton1_Click

        Export Workbook as PDF
            Open Workbook           workbook.xlsx
            Export as PDF           workbook.pdf

    **Python**

    .. code-block:: python

        from RPA.Excel.Application import Application

        app = Application()

        app.open_application()
        app.open_workbook('workbook.xlsx')
        app.set_active_worksheet(sheetname='new stuff')
        app.write_to_cells(row=1, column=1, value='new data')
        app.save_excel()
        app.quit_application()
    """

    APP_DISPATCH = "Excel.Application"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.workbook = None
        self.worksheet = None

    @property
    def _active_document(self):
        return self.workbook

    def _deactivate_document(self):
        self.workbook = None
        self.worksheet = None

    def add_new_workbook(self) -> None:
        """Adds new workbook for Excel application"""
        with catch_com_error():
            self.workbook = self.app.Workbooks.Add()

    def open_workbook(self, filename: str) -> None:
        """Open Excel by filename

        By default sets active worksheet to sheet number 1

        :param filename: path to filename
        """
        if not self._app:
            self.open_application()

        if filename.startswith("http"):
            workbook_path = filename
        else:
            workbook_path = to_path(filename)
            if not workbook_path.is_file():
                raise FileNotFoundError(f"{str(workbook_path)!r} doesn't exist")
            workbook_path = str(workbook_path)
        self.logger.info("Opening workbook: %s", workbook_path)

        with catch_com_error():
            try:
                self.workbook = self.app.Workbooks(workbook_path)
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.debug(str(exc))
                self.logger.info("Trying to open workbook by another method...")
                self.workbook = self.app.Workbooks.Open(workbook_path)

        self.set_active_worksheet(sheetnumber=1)
        self.logger.debug("Current workbook: %s", self.workbook)

    @requires_workbook
    def set_active_worksheet(
        self, sheetname: str = None, sheetnumber: int = None
    ) -> None:
        """Set active worksheet by either its sheet number or name

        :param sheetname: name of Excel sheet, defaults to None
        :param sheetnumber: index of Excel sheet, defaults to None
        """
        with catch_com_error():
            if sheetnumber:
                self.worksheet = self.workbook.Worksheets(int(sheetnumber))
            elif sheetname:
                self.worksheet = self.workbook.Worksheets(sheetname)

    def add_new_sheet(self, sheetname: str, create_workbook: bool = True) -> None:
        """Add new worksheet to workbook. Workbook is created by default if
        it does not exist.

        :param sheetname: name for sheet
        :param create_workbook: create workbook if True, defaults to True
        :raises ValueError: error is raised if workbook does not exist and
            `create_workbook` is False
        """
        if not self.workbook:
            if not create_workbook:
                raise ValueError("No workbook open")
            self.add_new_workbook()

        self.logger.info("Adding sheet: %s", sheetname)
        with catch_com_error():
            last = self.app.Worksheets(self.app.Worksheets.Count)
            self.worksheet = self.app.Worksheets.Add(After=last)
            self.worksheet.Name = sheetname

    def find_first_available_row(
        self, worksheet: Any = None, row: int = 1, column: int = 1
    ) -> Any:
        """Find first available free row

        :param worksheet: worksheet to handle, defaults to active worksheet if None
        :param row: starting row for search, defaults to 1
        :param column: starting column for search, defaults to 1
        :return: row or None
        """
        cell = self.find_first_available_cell(worksheet, row, column)
        return cell

    @requires_workbook
    def find_first_available_cell(
        self, worksheet: Any = None, row: int = 1, column: int = 1
    ) -> Any:
        """Find first available free cell

        :param worksheet: worksheet to handle, defaults to active worksheet if None
        :param row: starting row for search, defaults to 1
        :param column: starting column for search, defaults to 1
        :return: tuple (row, column) or (None, None) if not found
        """
        if worksheet:
            self.set_active_worksheet(worksheet)

        with catch_com_error():
            for current_row in count(int(row)):
                cell = self.worksheet.Cells(current_row, column)
                if cell.Value is None:
                    return current_row, column

        return None, None

    @requires_workbook
    def write_to_cells(
        self,
        worksheet: Any = None,
        row: int = None,
        column: int = None,
        value: str = None,
        number_format: str = None,
        formula: str = None,
    ) -> None:
        """Write value, number_format and/or formula into cell.

        :param worksheet: worksheet to handle, defaults to active worksheet if None
        :param row: target row, defaults to None
        :param column: target row, defaults to None
        :param value: possible value to set, defaults to None
        :param number_format: possible number format to set, defaults to None
        :param formula: possible format to set, defaults to None
        :raises ValueError: if cell is not given
        """
        if row is None or column is None:
            raise ValueError("No cell was given")

        if worksheet:
            self.set_active_worksheet(worksheet)

        with catch_com_error():
            cell = self.worksheet.Cells(int(row), int(column))

            if number_format:
                cell.NumberFormat = number_format
            if value:
                cell.Value = value
            if formula:
                cell.Formula = formula

    @requires_workbook
    def read_from_cells(
        self,
        worksheet: Any = None,
        row: int = None,
        column: int = None,
    ) -> str:
        """Read value from cell.

        :param worksheet: worksheet to handle, defaults to active worksheet if None
        :param row: target row, defaults to None
        :param column: target row, defaults to None
        :raises ValueError: if cell is not given
        """
        if row is None or column is None:
            raise ValueError("No cell was given")

        if worksheet:
            self.set_active_worksheet(worksheet)

        with catch_com_error():
            cell = self.worksheet.Cells(int(row), int(column))
            return cell.Value

    @requires_workbook
    def save_excel(self) -> None:
        """Saves Excel file"""
        with catch_com_error():
            self.workbook.Save()

    @requires_workbook
    def save_excel_as(
        self, filename: str, autofit: bool = False, file_format=None
    ) -> None:
        """Save Excel with name if workbook is open

        :param filename: where to save file
        :param autofit: autofit cell widths if True, defaults to False
        :param file_format: format of file

        **Note:** Changing the file extension for the path does not
        affect the actual format. To use an older format, use
        the ``file_format`` argument with one of the following values:

        https://docs.microsoft.com/en-us/office/vba/api/excel.xlfileformat

        Examples:

        .. code-block:: robotframework

            # Save workbook in modern format
            Save excel as    orders.xlsx

            # Save workbook in Excel 97 format (format from above URL)
            Save excel as    legacy.xls   file_format=${56}
        """
        with catch_com_error():
            if autofit:
                self.worksheet.Rows.AutoFit()
                self.worksheet.Columns.AutoFit()

            path = to_str_path(filename)
            if file_format is not None:
                self.workbook.SaveAs(path, FileFormat=file_format)
            else:
                self.workbook.SaveAs(path)

    @requires_workbook
    def run_macro(self, macro_name: str, *args: Any) -> None:
        """Run Excel macro with given name

        :param macro_name: macro to run
        :param args: arguments to pass to macro
        """
        with catch_com_error():
            self.app.Application.Run(f"'{self.workbook.Name}'!{macro_name}", *args)

    def export_as_pdf(self, pdf_filename: str, excel_filename: str = None) -> None:
        """Export Excel as PDF file

        If Excel filename is not given, the currently open workbook
        will be exported as PDF.

        :param pdf_filename: PDF filename to save
        :param excel_filename: Excel filename to open
        """
        if excel_filename:
            self.open_workbook(excel_filename)
        else:
            if not self.workbook:
                raise ValueError("No workbook open, can't export PDF")
        with catch_com_error():
            pdf_path = to_str_path(pdf_filename)
            self.workbook.ExportAsFixedFormat(0, pdf_path)

    def create_pivot_field(
        self,
        data_column: str,
        operation: str,
        numberformat: str = None,
    ) -> PivotField:
        """Create pivot field object parameters.

        *Note.* At the moment operation "DISTINCT COUNT" is not
        supported as there seems to be issues in the COM interface,
        which have not been resolved yet (regarding this library
        implementation).

        Python example:

        .. code-block:: python

            field_count = excel.create_pivot_field("price", "count", "#")
            field_avg = excel.create_pivot_field("price", "average", "#0,#0")

        Robot Framework example:

        .. code-block:: robotframework

            ${field_sum}=    Create Pivot Field    price    sum    #,#0
            ${field_max}=    Create Pivot Field    price    max    #,#0

        :param data_column: name of the data column
        :param operation: name of the possible operations
         (SUM, AVERAGE, MAX, MIN, COUNT)
        :param numberformat: Excel cell number format, by default
         number format is not set for the field
        :return: field object
        """
        return PivotField(data_column, operation, numberformat)

    def create_pivot_table(
        self,
        source_worksheet: str,
        pivot_worksheet: str,
        rows: List[str],
        fields: List[PivotField],
        sort_field: PivotField = None,
        sort_direction: str = "descending",
        data_range: Any = None,
        pivot_name: str = "PivotTable1",
        collapse_rows: bool = True,
        show_grand_total: bool = True,
    ) -> Any:
        """Create a pivot table in the specified worksheet.

        This is a initial implementation of the pivot table creation,
        which might not work in all cases. The alternative way
        of creating pivot tables is to use a macro an run it.

        Python example:

        .. code-block:: python

            rows = ["products", "expense_type"]
            field_count = excel.create_pivot_field("price", "count", "#")
            field_avg = excel.create_pivot_field("price", "average", "#0,#0")
            pivottable = excel.create_pivot_table(
                source_worksheet="data",
                pivot_worksheet="test!R5C5",
                rows=rows,
                fields=[field_count, field_avg]
            )

        Robot Framework example:

        .. code-block:: robotframework

            @{rows}=    Create List    products    expense_type
            ${field_sum}=    Create Pivot Field    price    sum    #,#0
            ${field_max}=    Create Pivot Field    price    max    #,#0
            @{fields}=   Create List   ${field_sum}    ${field_max}
            ${pivottable}=    Create Pivot Table
            ...    source_worksheet=data
            ...    pivot_worksheet=test!R5C5
            ...    rows=${rows}
            ...    fields=${fields}

        :param source_worksheet: name of the source worksheet
        :param pivot_worksheet: name of the pivot worksheet, can
         be the same as the source worksheet but then cell location
         of the pivot table needs to be given in the format "R1C1"
         (R is a column numbe and C is a row number, e.g. "R1C1" is A1)
        :param rows: columns in the `source_worksheet` which are used
         as pivot table rows
        :param fields: columns for the pivot table data fields
        :param sort_field: field to sort the pivot table by (one of the
         `fields`)
        :param sort_direction: sort direction (ascending or descending),
         default is descending
        :param data_range: source data range, if not given then
         the whole used range of `source_worksheet` will be used
        :param pivot_name: name of the pivot table, if not given
         then the name is "PivotTable1"
        :param collapse_rows: if `True` then the first row will be collapsed
        :param show_grand_total: if `True` then the grand total will be shown
         for the columns
        :return: created `PivotTable` object
        """

        self.set_active_worksheet(source_worksheet)
        if data_range:
            excel_range = (
                self.get_range(data_range)
                if isinstance(data_range, str)
                else data_range
            )
        else:
            excel_range = self.worksheet.UsedRange

        # Grab the pivot table source data
        pivot_cache = self.workbook.PivotCaches().Create(
            SourceType=constants.xlDatabase,
            SourceData=excel_range,
            Version=constants.xlPivotTableVersion15,
        )

        # Create the pivot table object
        table_destination = (
            f"{pivot_worksheet}!R1C1" if "!" not in pivot_worksheet else pivot_worksheet
        )

        pivot_table = pivot_cache.CreatePivotTable(
            TableDestination=table_destination,
            TableName=pivot_name,
            ReadData=True,
            DefaultVersion=constants.xlPivotTableVersion15,
        )

        for index, row in enumerate(rows):
            row_field = pivot_table.PivotFields(row)
            row_field.Orientation = constants.xlRowField
            row_field.Position = index + 1

        if len(rows) > 0 and collapse_rows:
            pivot_table.PivotFields(rows[0]).ShowDetail = False

        for pt_field in fields:
            self.logger.info(pt_field)
            pivot_operation = to_pivot_operation(pt_field.operation)

            # Access the field from the PivotFields collection
            field = pivot_table.PivotFields(pt_field.data_column)
            # Add the field to the values area
            data_field = pivot_table.AddDataField(field)
            data_field.Orientation = constants.xlDataField
            with catch_com_error():
                data_field.Name = f"{pt_field.data_column}_{randint(1000,9999)}"
                data_field.Function = pivot_operation
                if pt_field.numberformat:
                    data_field.NumberFormat = pt_field.numberformat

        if sort_field:

            def to_sort_direction(sort_direction: str):
                if sort_direction.upper() == "ASCENDING":
                    return constants.xlAscending
                else:
                    return constants.xlDescending

            # Access the pivot field (row or column) you want to sort
            pivot_field = pivot_table.PivotFields(rows[0])

            # Access the data field (value field) you want to sort by
            item_name = (
                f"{sort_field.operation.capitalize()} of {sort_field.data_column}"
            )
            data_field = pivot_table.DataPivotField.PivotItems(item_name)

            field_sort_direction = to_sort_direction(sort_direction)
            # Sort the pivot field in descending order based on the data field
            pivot_field.AutoSort(Order=field_sort_direction, Field=data_field.Name)

        # Visiblity True or Valse
        pivot_table.ShowValuesRow = False
        pivot_table.ColumnGrand = show_grand_total
        pivot_table.RefreshTable()
        return pivot_table

    def find(
        self,
        search_string: str,
        search_range: Any = None,
        max_results: int = None,
        search_order: SearchOrder = SearchOrder.ROWS,
        match_case: bool = False,
        search_type: str = None,
        search_after: str = None,
        exact: bool = False,
    ) -> List[Any]:
        """Keyword for finding text in the current worksheet.

        Wildcard can be used in a search string. The asterisk (*) represents
        any series of characters, and the question mark (?) represents a single
        character.

        Python example:

        .. code-block:: python

            ranges = excel.find("32.145.???.1", "IP!E1:E9999", 6)
            for r in ranges:
                print(f"ADDR = {r.Address} VALUE = {r.Value}")
                r.Value = r.Value.replace("32.145.", "192.168.")
                r.BorderAround()

        Robot Framework example:

        .. code-block:: robotframework

            ${ranges}=    Find
            ...    search_string=32.145.*
            ...    search_range=IP!A1:A9999
            ...    max_results=6
            ...    search_order=COLUMNS

            FOR    ${ranges}    IN    @{ranges}
                ${value}=    Set Variable    ${range.Value}
                Log to console    ADDR = ${range.Address} VALUE = ${value}
                ${new_value}=    Replace String    ${value}    32.145.    192.168.
                Set Object Property    ${range}    Value    ${new_value}
                Call Method    ${range}    BorderAround
            END

        :param search_string: what to search for
        :param search_range: if not given will search the current
         worksheet
        :param max_results: can be used to limit number of results
        :param search_order: by default search is executed by ROWS,
         can be changed to COLUMNS
        :param match_case: if `True` then the search is case sensitive
        :param search_type: can be FORMULAS, VALUES, COMMENTS or COMMENTS THREADED
        :param search_after: search after this cell
        :param exact: if `True` then the search is expected to be a exact match
        :return: list of `Range` objects
        """
        parameters = {
            "SearchOrder": (
                constants.xlByRows
                if search_order == SearchOrder.ROWS
                else constants.xlByColumns
            ),
            "MatchCase": match_case,
            "What": search_string,
        }
        if search_type:
            parameters["LookIn"] = to_look_in(search_type)
        if search_after:
            parameters["After"] = search_after
        results = []
        if search_range:
            search_area = (
                self._app.Range(search_range)
                if isinstance(search_range, str)
                else search_range
            )
        else:
            search_area = self.worksheet.UsedRange  # self.worksheet.Cells
        found = search_area.Find(**parameters)
        if not found:
            self.logger.info(
                f"Did not find the '{search_string}' in the current "
                f"{self.worksheet.Name}' worksheet"
            )
            return results
        addresses = set()
        while found:
            if max_results and len(results) >= max_results:
                break
            if found.Address in addresses:
                break
            addresses.add(found.Address)
            if found:
                expected = search_string if match_case else search_string.lower()
                actual = found.Value if match_case else found.Value.lower()
                if (exact and actual == expected) or not exact:
                    results.append(found)
            found = search_area.FindNext(found)
        return results

    def create_table(self, table_name: str, table_range: Any = None) -> None:
        """Create a table in the current worksheet.

        :param table_name: name for the table
        :param table_range: source table range, if not given then
         the whole used range of `source_worksheet` will be used
        """
        if table_range:
            excel_range = (
                self.get_range(table_range)
                if isinstance(table_range, str)
                else table_range
            )
        else:
            excel_range = self.worksheet.UsedRange

        self.worksheet.ListObjects.Add(
            SourceType=constants.xlSrcRange,
            Source=excel_range,
            XlListObjectHasHeaders=constants.xlYes,
        ).Name = table_name

    def list_tables(self) -> List[str]:
        """Return tables in the current worksheet.

        :return: list of table names
        """
        return [table.Name for table in self.worksheet.ListObjects]

    def get_range(self, table_range: str) -> Any:
        """Get range object for the given range address.

        These object properties and methods can be then called.

        Python example:

        .. code-block:: python

            source = excel.get_range('A1:B2')
            for r in source:
                print(f"ADDR = {r.Address} VAL = {r.Value}")
                r.BorderAround()
            source.Merge()
            # Creating a formula and copying it to another range
            excel.get_range("E4").Formula = "=SUM(C4:D4)"
            destination = excel.get_range("E5:E10")
            excel.get_range("E4").Copy(destination)

        Robot Framework example:

        .. code-block:: robotframework

            ${range}=    Get Range    data!A1:A4
            FOR    ${r}    IN    @{range}
                Log To Console    ADDR = ${r.Address} VAL = ${r.Value}
                Call Method  ${r}    BorderAround
            END
            Call Method    ${range}    Merge

        :param table_range: range to return
        :return: range object
        """
        return self.worksheet.Range(table_range)

    def get_pivot_tables(
        self, pivot_table_name: str = None, as_list: bool = True
    ) -> Dict[str, Any]:
        """Return pivot tables in the current worksheet.

        Python example:

        .. code-block:: python

            from RPA.Tables import Tables

            pivot_tables = excel.get_pivot_tables()

            for tbl_name, tbl_list in pivot_tables.items():
                print(f"TABLE NAME: {tbl_name}")
                table = Tables().create_table(data=tbl_list[1:], columns=tbl_list[0])
                print(table)

        Robot Framework example:

        .. code-block:: robotframework

            ${pivots}=    Get Pivot Tables
            FOR    ${tablename}    ${pivot}    IN    &{pivots}
                Log To Console    ${tablename}
                ${table}=    RPA.Tables.Create Table
                ...   data=${{$pivot[1:]}}
                ...   columns=${{$pivot[0]}}
                Log To Console    ${table}
            END

        :param pivot_table_name: name of the pivot table to return,
         will return by default all pivot tables
        :param as_list: if `True` then the pivot table data is returned as list
         of lists, if `False` then the data is returned as list of `Range` objects
        :return: dictionary of pivot tables (names as keys and table data as values)
        """
        pivot_tables = {}
        tables = self.worksheet.PivotTables()
        for table in tables:
            data = []
            if as_list:
                previous_row = -1
                row = []
                for r in table.TableRange1:
                    if previous_row == -1 or previous_row != r.Row:
                        if len(row) > 0:
                            data.append(row)
                        row = [r.Value]
                        previous_row = r.Row
                    else:
                        row.append(r.Value)
            else:
                data = table.TableRange1
            if pivot_table_name and table.Name != pivot_table_name:
                continue
            pivot_tables[table.Name] = data
        return pivot_tables

    def write_data_to_range(
        self,
        target_range: Any,
        values: Union[Table, List[List]],
        log_warnings: bool = True,
    ):
        """Writes data to the specified range(s) in the Excel worksheet.

        The range width should match the number of columns in the data.

        Multiple ranges can be specified by separating them with a semicolon, but
        still the total width of ranges should match the number of columns in the data.

        Python example:

        .. code-block:: python

            from RPA.Tables import Tables
            from RPA.Excel.Application import Application

            excel = Application()

            table = Tables().read_table_from_csv("input.csv", header=True)
            excel.open_workbook("result.xslx)
            excel.write_data_to_range("A2:P100", table)

        Robot Framework example:

        .. code-block:: robotframework

            ${input_table}=    Read table from CSV    input.csv    header=True
            Open Workbook      result.xlsx
            Write Data To Range    A2:L21    ${input_table}   # Single range
            Write Data To Range    C2:E21;G2:I21    ${input_table}   # Multiple ranges

        :param target_range: A1 string presentation of the range(s) to write or
         Range object.
        :param values: `Table` or list of lists to write to the range(s).
        :param log_warnings: on `False` will suppress logging warning, default
         is `True` (warnings are logged)
        """
        try:
            if isinstance(target_range, str):
                target_ranges = target_range.split(";")
                ranges = [self.worksheet.Range(range) for range in target_ranges]
            else:
                ranges = [target_range]
        except Exception as err:
            raise AttributeError(
                "Unable to form valid Excel range(s) from "
                f"incoming 'target_range': f{str(err)}"
            ) from err
        rows = _get_rows_from_table(values) if isinstance(values, Table) else values
        datas = _split_rows_into_range_blocks(rows, ranges)
        row_columns = len(rows[0])
        self.logger.info(f"Data contains {len(rows)} rows and {row_columns} columns.")
        range_columns = 0
        for range_, data in zip(ranges, datas):
            columns = range_.Columns.Count
            range_columns += columns
            self.logger.info(
                f"Range contains {range_.Rows.Count} rows and {columns} columns."
            )
            range_.Value = data
        if log_warnings and range_columns != row_columns:
            self.logger.warning(
                f"Total range column count {range_columns} "
                f"is different from data to write column count {row_columns}"
            )

    def remove_hidden_columns_and_rows(
        self, initial_range: Any, worksheet: str = None
    ) -> Any:
        """Removes hidden columns and rows from a range and returns a new range.

        :param initial_range: range of cells to remove hidden columns and rows from
        :param worksheet: set active worksheet (name) before removing hidden
         columns and rows
        :return: new range or initial range if no hidden cells found
        """
        initial_range = (
            self.get_range(initial_range)
            if isinstance(initial_range, str)
            else initial_range
        )
        if worksheet:
            self.set_active_worksheet(worksheet)
        try:
            visible_range = initial_range.SpecialCells(constants.xlCellTypeVisible)
            return visible_range
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error(f"No visible cells found or an error occurred:f{str(e)}")
        return initial_range

    def unmerge_range(self, initial_range: Any) -> None:
        """Unmerges a range of cells.

        :param initial_range: range of cells to unmerge
        """
        initial_range = (
            self.get_range(initial_range)
            if isinstance(initial_range, str)
            else initial_range
        )
        initial_range.UnMerge()

    def merge_range(self, initial_range: Any) -> None:
        """Merges a range of cells.

        :param initial_range: range of cells to merge
        """
        initial_range = (
            self.get_range(initial_range)
            if isinstance(initial_range, str)
            else initial_range
        )
        initial_range.Merge()
