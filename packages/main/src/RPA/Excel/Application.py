import functools
from itertools import count
from typing import Any

from RPA.application import BaseApplication, catch_com_error, to_path, to_str_path


def requires_workbook(func):
    """Ensures a workbook is open."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.workbook is None:
            raise ValueError("No workbook open")
        return func(self, *args, **kwargs)

    return wrapper


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

        path = to_path(filename)
        if not path.is_file():
            raise FileNotFoundError(f"{str(path)!r} doesn't exist")
        path = str(path)
        self.logger.info("Opening workbook: %s", path)

        with catch_com_error():
            try:
                self.workbook = self.app.Workbooks(path)
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.debug(str(exc))
                self.logger.info("Trying to open workbook by another method...")
                self.workbook = self.app.Workbooks.Open(path)

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
    def run_macro(self, macro_name: str, *args: Any):
        """Run Excel macro with given name

        :param macro_name: macro to run
        :param args: arguments to pass to macro
        """
        with catch_com_error():
            self.app.Application.Run(f"'{self.workbook.Name}'!{macro_name}", *args)

    def export_as_pdf(self, pdf_filename: str, excel_filename: str = None):
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
