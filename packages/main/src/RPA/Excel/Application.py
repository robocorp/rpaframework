import atexit
import logging
import platform
import struct
from itertools import count
from pathlib import Path
from typing import Any
from contextlib import contextmanager

if platform.system() == "Windows":
    import win32api
    import win32com.client
    import pywintypes
else:
    logging.getLogger(__name__).warning(
        "RPA.Excel.Application library works only on Windows platform"
    )


def _to_unsigned(val):
    return struct.unpack("L", struct.pack("l", val))[0]


@contextmanager
def catch_com_error():
    """Try to convert COM errors to human readable format."""
    try:
        yield
    except pywintypes.com_error as err:  # pylint: disable=no-member
        if err.excepinfo:
            try:
                msg = win32api.FormatMessage(_to_unsigned(err.excepinfo[5]))
            except Exception:  # pylint: disable=broad-except
                msg = err.excepinfo[2]
        else:
            try:
                msg = win32api.FormatMessage(_to_unsigned(err.hresult))
            except Exception:  # pylint: disable=broad-except
                msg = err.strerror
        raise RuntimeError(msg) from err


class Application:
    """`Excel.Application` is a library for controlling an Excel application.

    *Note*. Library works only Windows platform.

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

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self, autoexit: bool = True) -> None:
        self.logger = logging.getLogger(__name__)
        self.app = None
        self.workbook = None
        self.worksheet = None

        if platform.system() != "Windows":
            self.logger.warning(
                "Excel application library requires Windows dependencies to work."
            )
        if autoexit:
            atexit.register(self.quit_application)

    def open_application(
        self, visible: bool = False, display_alerts: bool = False
    ) -> None:
        """Open the Excel application.

        :param visible: show window after opening
        :param display_alerts: show alert popups
        """
        with catch_com_error():
            self.app = win32com.client.gencache.EnsureDispatch("Excel.Application")
            self.logger.debug("Opened application: %s", self.app)

            if hasattr(self.app, "Visible"):
                self.app.Visible = visible

            # Show eg. file overwrite warning or not
            if hasattr(self.app, "DisplayAlerts"):
                self.app.DisplayAlerts = display_alerts

    def close_document(self, save_changes: bool = False) -> None:
        """Close the active document (if open)."""
        if not self.workbook:
            return

        with catch_com_error():
            self.workbook.Close(save_changes)

        self.workbook = None
        self.worksheet = None

    def quit_application(self, save_changes: bool = False) -> None:
        """Quit the application."""
        if not self.app:
            return

        self.close_document(save_changes)
        with catch_com_error():
            self.app.Quit()

        self.app = None

    def add_new_workbook(self) -> None:
        """Adds new workbook for Excel application"""
        if not self.app:
            raise ValueError("Excel application is not open")

        with catch_com_error():
            self.workbook = self.app.Workbooks.Add()

    def open_workbook(self, filename: str) -> None:
        """Open Excel by filename

        By default sets active worksheet to sheet number 1

        :param filename: path to filename
        """
        if not self.app:
            self.open_application()

        path = str(Path(filename).resolve())
        self.logger.info("Opening workbook: %s", path)

        with catch_com_error():
            try:
                self.workbook = self.app.Workbooks(path)
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.debug(str(exc))
                self.logger.info("Trying to open workbook by another method")
                self.workbook = self.app.Workbooks.Open(path)

        self.set_active_worksheet(sheetnumber=1)
        self.logger.debug("Current workbook: %s", self.workbook)

    def set_active_worksheet(
        self, sheetname: str = None, sheetnumber: int = None
    ) -> None:
        """Set active worksheet by either its sheet number or name

        :param sheetname: name of Excel sheet, defaults to None
        :param sheetnumber: index of Excel sheet, defaults to None
        """
        if not self.workbook:
            raise ValueError("No workbook open")

        with catch_com_error():
            if sheetnumber:
                self.worksheet = self.workbook.Worksheets(int(sheetnumber))
            elif sheetname:
                self.worksheet = self.workbook.Worksheets(sheetname)

    def add_new_sheet(
        self, sheetname: str, tabname: str = None, create_workbook: bool = True
    ) -> None:
        """Add new worksheet to workbook. Workbook is created by default if
        it does not exist.

        :param sheetname: name for sheet
        :param tabname: name for tab (deprecated)
        :param create_workbook: create workbook if True, defaults to True
        :raises ValueError: error is raised if workbook does not exist and
            `create_workbook` is False
        """
        if tabname:
            sheetname = tabname
            self.logger.warning(
                "Argument 'tabname' is deprecated, "
                "and will be removed in a future version"
            )

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
        # Note: keep return type for backward compability for now
        # return cell[0] if cell else None
        return cell

    def find_first_available_cell(
        self, worksheet: Any = None, row: int = 1, column: int = 1
    ) -> Any:
        """Find first available free cell

        :param worksheet: worksheet to handle, defaults to active worksheet if None
        :param row: starting row for search, defaults to 1
        :param column: starting column for search, defaults to 1
        :return: tuple (row, column) or (None, None) if not found
        """
        if not self.workbook:
            raise ValueError("No workbook open")

        if worksheet:
            self.set_active_worksheet(worksheet)

        with catch_com_error():
            for current_row in count(int(row)):
                cell = self.worksheet.Cells(current_row, column)
                if cell.Value is None:
                    return current_row, column

        return None, None

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
        if not self.workbook:
            raise ValueError("No workbook open")

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
        if not self.workbook:
            raise ValueError("No workbook open")

        if row is None or column is None:
            raise ValueError("No cell was given")

        if worksheet:
            self.set_active_worksheet(worksheet)

        with catch_com_error():
            cell = self.worksheet.Cells(int(row), int(column))
            return cell.Value

    def save_excel(self) -> None:
        """Saves Excel file"""
        if not self.workbook:
            raise ValueError("No workbook open")

        with catch_com_error():
            self.workbook.Save()

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
        if not self.workbook:
            # Doesn't raise error for backwards compatibility
            self.logger.warning("No workbook open")
            return

        with catch_com_error():
            if autofit:
                self.worksheet.Rows.AutoFit()
                self.worksheet.Columns.AutoFit()

            path = str(Path(filename).resolve())

            if file_format is not None:
                self.workbook.SaveAs(path, FileFormat=file_format)
            else:
                self.workbook.SaveAs(path)

    def run_macro(self, macro_name: str, *args: Any):
        """Run Excel macro with given name

        :param macro_name: macro to run
        :param args: arguments to pass to macro
        """
        if not self.app:
            raise ValueError("Excel application is not open")

        if not self.workbook:
            raise ValueError("No workbook open")

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
                raise ValueError("No workbook open. Can't export PDF.")
        with catch_com_error():
            path = str(Path(pdf_filename).resolve())
            self.workbook.ExportAsFixedFormat(0, path)
