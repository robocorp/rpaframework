import logging
from pathlib import Path
from typing import Any
from RPA.core.msoffice import OfficeApplication


class Application(OfficeApplication):
    """Library for manipulating Excel application."""

    def __init__(self) -> None:
        OfficeApplication.__init__(self, application_name="Excel")
        self.logger = logging.getLogger(__name__)
        self.workbook = None
        self.workbook_name = None
        self.active_worksheet = None

    def add_new_workbook(self) -> None:
        """Adds new workbook for Excel application
        """
        self.workbook = self.app.Workbooks.Add()

    def open_workbook(self, filename: str) -> None:
        """Open Excel by filename

        :param filename: path to filename
        """
        if self.app is None:
            self.open_application()
        excel_filepath = str(Path(filename).resolve())
        self.workbook_name = Path(filename).name
        self.logger.info("Opening workbook: %s", excel_filepath)
        self.workbook = self.app.Workbooks.Open(excel_filepath)
        self.logger.debug("Workbook: %s", self.workbook)

    def set_active_worksheet(
        self, sheetname: str = None, sheetnumber: int = None
    ) -> None:
        """Set active worksheet by either its sheet number or name

        :param sheetname: name of Excel sheet, defaults to None
        :param sheetnumber: index of Excel sheet, defaults to None
        """
        if sheetnumber:
            self.active_worksheet = self.workbook.Worksheets(int(sheetnumber))
        elif sheetname:
            self.active_worksheet = self.workbook.Worksheets(sheetname)

    def add_new_sheet(
        self, sheetname: str, tabname: str = None, create_workbook: bool = True
    ) -> None:
        """Add new worksheet to workbook. Workbook is created by default if
        it does not exist.

        :param sheetname: name for sheet
        :param tabname: name for tab, defaults to None
        :param create_workbook: create workbook if True, defaults to True
        :raises ValueError: error is raised if workbook does not exist and
            `create_workbook` is False
        """
        self.logger.info("Adding sheet: %s", sheetname)
        if self.workbook is None:
            if not create_workbook:
                raise ValueError("No workbook open")
            self.add_new_workbook()
        self.active_worksheet = self.app.Worksheets(sheetname)
        if tabname:
            self.active_worksheet.Name = tabname

    def find_first_available_row(
        self, worksheet: Any = None, row: int = 1, column: int = 1
    ) -> Any:
        """Find first available free row and cell

        :param worksheet: worksheet to handle, defaults to active worksheet if None
        :param row: starting row for search, defaults to 1
        :param column: starting column for search, defaults to 1
        :return: tuple (row, column) or (None, None) if not found
        """
        empty_found = False
        worksheet = worksheet if worksheet else self.active_worksheet

        while empty_found is False:
            cell_value = worksheet.Cells(row, column).Value
            if cell_value is None:
                empty_found = True
                return (row, column)
            row += 1
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
        worksheet = worksheet if worksheet else self.active_worksheet
        if row is None and column is None:
            raise ValueError("No cell was given")
        else:
            row = int(row)
            column = int(column)
        if number_format:
            worksheet.Cells(row, column).NumberFormat = number_format
        if value:
            worksheet.Cells(row, column).Value = value
        if formula:
            worksheet.Cells(row, column).Formula = formula

    def save_excel(self) -> None:
        """Saves Excel file
        """
        self.workbook.Save()

    def save_excel_as(self, filename: str, autofit: bool = False) -> None:
        """Save Excel with name if workbook is open

        :param filename: where to save file
        :param autofit: autofit cell widths if True, defaults to False
        """
        if self.workbook:
            if autofit:
                self.active_worksheet.Rows.AutoFit()
                self.active_worksheet.Columns.AutoFit()
            excel_filepath = str(Path(filename).resolve())
            self.workbook.SaveAs(excel_filepath)

    def run_macro(self, macro_name: str = None):
        """Run Excel macro with given name

        :param macro_name: macro to run
        """
        if self.app is None:
            raise ValueError(
                "Open Excel file with macros first, e.g. `Open Workbook <filename>`"
            )
        self.app.Application.Run(f"{self.workbook_name}!{macro_name}")
