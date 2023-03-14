# builtin imports
import logging
import os
from typing import Union, Optional, Any
from pathlib import Path
from collections import OrderedDict

# Robot imports
from robot.api.deco import keyword, library
from robot.utils.robottime import timestr_to_secs, parse_time
from robot.api import logger
from robot.running.context import EXECUTION_CONTEXTS

# package imports
from RPA.version import __version__
from RPA.Robocorp.utils import get_output_dir

try:
    from RPA.Tables import Table

    TABLES = True
except ImportError:
    TABLES = False

# Library specific imports
from smartsheet import Smartsheet as smart_sdk, types as smart_types
from smartsheet.models import (
    Sheet,
    Column,
    Row,
    Cell,
    Attachment,
    IndexResult,
    SheetFilter,
    User,
    ServerInfo,
)

CommaListType = Union[str, list[Any]]
ColumnType = Union[dict, Column]
if TABLES:
    TableType = Table
else:
    TableType = Any


class SmartsheetError(Exception):
    "Base error class for Smartsheet library."


class SmartsheetAuthenticationError(SmartsheetError):
    "Error when authenticated Smartsheet instance does not exist."


class SmartsheetNoSheetSelectedError(SmartsheetError):
    "Error when no sheet was selected to on which to perform the operation."


@library(scope="Global", doc_format="REST")
class Smartsheet:
    """*Smartsheet* is a library for accessing Smartsheet using the
    `Smartsheet API 2.0`_. It extends `smartsheet-python-sdk`_.

    .. _Smartsheet API 2.0: https://smartsheet.redoc.ly/
    .. _smartsheet-python-sdk: https://github.com/smartsheet/smartsheet-python-sdk

    """

    # TODO: ADD LOGGING THROUGHOUT

    # Only implemented includes are available, others exist for the API
    SHEET_INCLUDES = {
        "rowId": None,  # function must be set in __init__
        "attachments": "attachments",
        "attachmentFiles": None,  # function must be set in __init__
        "discussions": "discussions",
        "rowPermalink": "permalink",
    }
    """Dictionary of supported additional objects to ask for via ``include`` 
    parameters for sheets. Key is the name of the option, value is the 
    API attribute or function to call.
    """
    ROW_INCLUDES = {
        "rowId": None,  # function must be set in __init__
        "attachments": "attachments",
        "attachmentFiles": None,  # function must be set in __init__
        "discussions": "discussions",
        "rowPermalink": "permalink",
        "filters": "filteredOut",
    }
    """Dictionary of supported additional objects to ask for via ``include``
    parameters for rows. Key is the name of the option, value is the 
    API attribute or function to call.
    """
    ROW_EXCLUDES = [
        "filteredOutRows",
        "linkInFromCellDetails",
        "linksOutToCellsDetails",
        "nonexistentCells",
    ]
    """List of supported options to remove cells from rows."""
    SEARCH_INCLUDES = {"favoriteFlag": None}
    """Dictionary of supported additional objects to ask for via ``include``
    parameters for searches. Key is the name of the option, value is the
    API attribute or function to call.
    """
    SEARCH_SCOPES = [
        "attachments",
        "cellData",
        "comments",
        "folderNames",
        "reportNames",
        "sheetNames",
        "sightNames",
        "summaryFields",
        "templateNames",
        "workspaceNames",
    ]

    def __init__(self, access_token: str = None, max_retry_time: Union[str, int] = 30):
        """If you do not initialize the library with an access token,
        it will attempt to load the environment variable
        ``SMARTSHEET_ACCESS_TOKEN``, otherwise, use the keyword
        `Set access token`.

        :param access_token: The access token created for your
         Smartsheet user.
        :param max_retry_time: Maximum time to allow retries of API
         calls. Can be provided as a time string or int.
        """
        self.logger = logging.getLogger(__name__)
        # Sets log level for the SDK to debug, we will redirect their logs here
        # and let Robot Framework handle logging levels once here.
        os.environ["LOG_CFG"] = "DEBUG"
        self.smart = None
        self.max_retry_time = None
        self.set_max_retry_time(max_retry_time)
        self._set_token(access_token)
        # sheet init
        self._sheets = []
        self.current_sheet = None
        # sets the function for this key
        self.SHEET_INCLUDES["attachmentFiles"] = self._download_row_attachments
        self.SHEET_INCLUDES["rowId"] = self._parse_row_id
        self.ROW_INCLUDES["attachmentFiles"] = self._download_row_attachments
        self.ROW_INCLUDES["rowId"] = self._parse_row_id
        # user init
        self.current_user = None
        # Server init
        self.app_constants = None

    ## AUTH AND CONFIG
    def _set_token(self, access_token: str = None):
        if (
            os.environ.get("SMARTSHEET_ACCESS_TOKEN", None) is None
            and access_token is None
        ):
            self.smart = None
        else:
            self.smart = smart_sdk(
                access_token=access_token,
                user_agent=f"rpaframework/{__version__}",
                max_retry_time=self.max_retry_time,
            )
            self.smart.errors_as_exceptions(True)
            # TODO: consider if this properly connects the logs.
            for handler in logging.getLogger("smartsheet").handlers:
                self.logger.addHandler(handler)

    def _require_auth(self) -> None:
        if self.smart is None:
            raise SmartsheetAuthenticationError("Authentication was not completed.")

    def _require_current_sheet(self) -> None:
        if self.current_sheet is None:
            raise SmartsheetNoSheetSelectedError(
                "You must select a sheet before performing this operation."
            )

    @keyword
    def set_access_token(self, access_token: str) -> None:
        """Sets the access token to be used when accessing the
        Smartsheet API.

        Learn more about authenticating to Smartsheets
        `here <https://smartsheet.redoc.ly/#section/API-Basics/Raw-Token-Requests>`_.

        :param access_token: The access token created for your
         Smartsheet user.
        """
        self._set_token(access_token)

    @keyword
    def set_max_retry_time(self, max_retry_time: Union[str, int]) -> int:
        """Sets the max retry time to use when sending requests to the
        Smartsheet API. Returns the current max retry time.

        :param max_retry_time: Maximum time to allow retries of API
         calls. Can be provided as a time string or int.
        """
        old_time = self.max_retry_time
        self.max_retry_time = int(timestr_to_secs(max_retry_time, round_to=None))
        if self.smart is not None:
            # might be affected by smart's def of __getattr__
            self.smart._user_calc_backoff._max_retry_time = self.max_retry_time
        return old_time

    ## UTILITY
    def _parse_comma_list_type(
        self, comma_list: Optional[CommaListType] = None
    ) -> Optional[list[str]]:
        if isinstance(comma_list, str):
            return [s.strip() for s in comma_list.split(",")]
        elif isinstance(comma_list, list):
            return [str(s) for s in comma_list]
        elif comma_list is not None:
            raise TypeError(
                "Invalid type supplied as comma list, either provide a "
                "list object or a string of comma-separated values."
            )
        else:
            return None

    def _unpack_index_result(
        self, index_result: IndexResult = None
    ) -> Optional[list[object]]:
        """Unpacks the provided IndexResult object into a list of the
        underlying type.
        """
        if index_result is not None:
            return [o for o in index_result.data]
        else:
            return None

    def _parse_include(
        self, include_type: dict, include: CommaListType = None
    ) -> list[str]:
        """Parses the include parameter based on the provided include type."""
        include = self._parse_comma_list_type(include)
        if (
            include is not None
            and "ALL" not in include
            and any([i not in include_type.keys() for i in include])
        ):
            raise ValueError("Invalid or not implemented value(s) for include.")
        elif include is not None and "ALL" in include:
            includes = [str(k) for k in include_type.keys()]
        elif include is not None:
            includes = [str(i) for i in include]
        else:
            includes = None
        return includes

    def _parse_exclude(
        self, exclude_type: list, exclude: CommaListType = None
    ) -> list[str]:
        """Parses the exclude parameter based on the provided exclude type."""
        exclude = self._parse_comma_list_type(exclude)
        if exclude is not None and any([i not in exclude_type for i in exclude]):
            raise ValueError("Invalid or not implemented value(s) for exclude.")
        return exclude

    def _parse_scope(self, scope_type: list, scope: CommaListType = None) -> list[str]:
        """Parses the scope parameter based on the provided scope type."""
        scope = self._parse_comma_list_type(scope)
        if scope is not None and any([i not in scope_type for i in scope]):
            raise ValueError("Invalid or not implemented value(s) for scope.")
        return scope

    @keyword
    def get_application_constants(self) -> ServerInfo:
        """Gets application constants from the server. This
        should not need to be called by a robot.
        """
        self._require_auth()
        self.app_constants = self.smart.Server.server_info()
        return self.app_constants

    ## SHEETS
    @property
    def sheets(self):
        """Full list of cached sheets."""
        if len(self._sheets) == 0:
            self._refresh_sheets()
        return self._sheets

    def _refresh_sheets(self):
        """Refreshes the ``sheets`` property."""
        self._require_auth()
        self._sheets = self.smart.Sheets.list_sheets(include_all=True).data

    def _find_sheet(self, name: str) -> IndexResult:
        """Finds a sheet by name and returns the ``IndexResult``, which
        can be used to pull sheet data with its ``id`` attribute.
        """
        for sheet in self.sheets:
            if sheet.name == name:
                return sheet

    def _parse_sheet_id(self, sheet_id: int = None, sheet_name: int = None) -> int:
        """Gets the sheet ID between the provided ID and/or Name."""
        if sheet_id is not None and sheet_name is not None:
            raise ValueError("You cannot provide both sheet_id and sheet_name.")
        if sheet_id is None and sheet_name is None:
            raise ValueError("You must provide either sheet_id or sheet_name.")
        if sheet_id is not None:
            return sheet_id
        if sheet_name is not None:
            return self._find_sheet(sheet_name).id

    @keyword
    def list_sheets(self, use_cache: bool = True):
        """Lists all sheets available for the authenticated account. Uses
        cached lists if available unless ``use_cache`` is set to ``False``.

        The cached lists is used for other keywords, so if you need to
        refresh the cache for other keywords to use, you must do so
        via this keyword.

        :param use_cache: Defaults to ``True``. You can set to ``False``
         to force a reload of the cached list of sheets.
        """
        self._require_auth()
        if use_cache:
            return self.sheets
        else:
            self._refresh_sheets()
            return self.sheets

    @keyword
    def unselect_current_sheet(self) -> None:
        """Resets the current sheet to None."""
        self.current_sheet = None

    @keyword
    def get_sheet(
        self,
        sheet_id: int = None,
        sheet_name: str = None,
        include: CommaListType = None,
        row_ids: CommaListType = None,
        row_numbers: CommaListType = None,
        column_ids: CommaListType = None,
        filter_id: int = None,
        native: bool = False,
    ) -> Union[TableType, Sheet]:
        """Retrieves a sheet from Smartsheet. This keyword also sets
        the currently selected sheet to the returned sheet.

        You cannot provide both a ``sheet_id`` and ``sheet_name``.

        :param sheet_id: The ID of the sheet to get. You cannot supply
         both a ``sheet_id`` and ``sheet_name``.
        :param sheet_name: The name of the sheet to get, it will return
         the first sheet name matching the provided name. You cannot supply
         both a ``sheet_id`` and ``sheet_name``.
        :param include: Additional metadata which can be retrieved with
         the table. The list can only contain the following items:
         ``attachments``, ``attachmentFiles``, ``discussions``,
         ``rowPermalink``, or ``ALL``.
        :param row_ids: A list of row IDs to include. All other rows
         will be ignored. The list can be a list object or a
         comma-separated list as a string.
        :param row_numbers: A list of row numbers to include. All other
         rows will be ignored. The list can be a list object or a
         comma-separated list as a string.
        :param column_ids: A list of column IDs to only include, others
         will not be returned. The list can be a list object or a
         comma-separated list as a string.
        :param filter_id: The ID of a filter to apply. Filtered out
         rows will not be included in the resulting table.
        :param native: Defaults to ``False``. Set to ``True`` to change
         the return type to the native Smartsheet data model. The native
         type is useful for passing to other keywords as arguments.
        """
        # TODO: add examples to docs.
        self._require_auth()
        sheet_id = self._parse_sheet_id(sheet_id, sheet_name)
        # Smartsheet class defines a `__getattr__` which makes the below work, just
        # doesn't help with intellisense autocompletion.
        # BUG: will this affect how I attempt to modify `_user_calc_backoff`?
        includes = self._parse_include(self.SHEET_INCLUDES, include)
        sheet = self.smart.Sheets.get_sheet(
            sheet_id,
            include=includes,
            row_ids=self._parse_comma_list_type(row_ids),
            row_numbers=self._parse_comma_list_type(row_numbers),
            column_ids=self._parse_comma_list_type(column_ids),
            filter_id=filter_id,
        )
        setattr(sheet, "selected_includes", includes)
        self.current_sheet = sheet
        if native:
            return sheet
        else:
            return self.convert_sheet_to_table(sheet)

    @keyword
    def convert_sheet_to_table(self, sheet: Sheet = None) -> Table:
        """Converts the current sheet to table. You can provide a differnt
        native sheet object to be converted via the ``sheet`` parameter.

        This keyword attempts to return the sheet as a table via
        ``RPA.Tables``, but if that library is not available in this
        context, the sheet is returned as it's native data model (e.g.,
        no operation is performed).

        If the sheet contains additional data from the ``include``
        argument, they will be appended to the end of the table as
        additional columns in the data model. These additional objects
        will be attached as a list of objects depending on the items
        requested.

        .. warn:

            Only the following supported additional data requests
            are supported when unpacking a Sheet object.

            * ``attachments``: The value for the cell will be a list of
            native Attachment object.
            * ``attachmentFiles``: The value for the cell will be a list of
            file paths to the local copies of each attachment. This
            operation may be resource intensive for many attachments.
            * ``discussions``: The value for the cell will be a list of
            native Discussion objects.
            * ``rowPermalink``: The value for the cell will be a single
            string representing the URL to the permalink.
        """
        if sheet is None:
            self._require_current_sheet()
            sheet = self.current_sheet
        includes = getattr(sheet, "selected_includes", []) or []
        table_data = []
        headers = []
        for column in sheet.columns:
            headers.append(column.title)
        if len(includes) > 0:
            headers.extend(includes)

        for row in sheet.rows:
            row_data = []
            for cell in row.cells:
                row_data.append(cell.value)
            for key in includes:
                key_or_func = self.SHEET_INCLUDES[key]
                if callable(key_or_func):
                    row_data.append(key_or_func(row))
                elif getattr(row, key_or_func, False):
                    row_data.append(getattr(row, key_or_func, None))

            table_data.append(row_data)

        table = Table(table_data, columns=headers)

        return table

    @keyword
    def get_sheet_owner(
        self, sheet_id: int = None, sheet_name: int = None, native: bool = False
    ) -> tuple[str, int]:
        """Returns the owner's username and id for the current sheet."""
        sheet_id = self._parse_sheet_id(sheet_id, sheet_name)
        sheet = self.smart.Sheets.get_sheet(sheet_id, include=["ownerInfo"])
        return sheet.owner, sheet.owner_id

    @keyword
    def list_sheet_filters(
        self, sheet_id: int = None, sheet_name: int = None
    ) -> list[SheetFilter]:
        """Returns a list of available filters for the current sheet."""
        # TODO: fix documentation
        self._require_current_sheet()
        filter_result = self.smart.Sheets.list_filters(
            self.current_sheet.id, include_all=True
        )
        return self._unpack_index_result(filter_result)

    @keyword
    def create_sheet(
        self,
        name: str,
        columns: list[ColumnType] = None,
        from_sheet_id: Union[int, str] = None,
    ) -> Sheet:
        """Creates a new sheet with the given name and columns, then sets
        the current sheet to the new sheet and returns it as a native
        Smartsheet object.

        :param from_sheet_id: Sheet ID to use as a template for the new
         sheet.
        """
        self._require_auth()
        if columns is not None:
            new_columns = self._parse_columns(columns)
            sheet = self.smart.Home.create_sheet(
                Sheet({"name": name, "columns": new_columns})
            )
        elif from_sheet_id is not None:
            sheet = self.smart.Home.get_sheet({"name": name, "from_id": from_sheet_id})
        else:
            raise ValueError("Either columns or from_sheet_id must be provided.")
        self.current_sheet = sheet.result
        return sheet.result

    @keyword
    def search(
        self,
        query: str,
        location: Optional[str] = None,
        modified_since: Optional[Union[str, int]] = None,
        include: Optional[CommaListType] = None,
        scopes: Optional[CommaListType] = None,
    ) -> list[Sheet]:
        """Searches for all sheets for text matching the query. Returns
        a list of native Smartsheet Sheet objects. You can use the
        additional parameters to filter the search and increase speed.

        :param query: The text to search for.
        :type query: str
        :param location: The location to search. When specified with
         a value of ``personalWorkspace``, the search will be limited
         to the current user's personal workspace.
        :type location: str
        :param modified_since: The date to search from. This can be
         either a string or an integer. If an integer is provided, it
         will be interpreted as a Unix timestamp. If a string is
         provided, it will be parsed via the Robot Framework time
         utilities, so you can provided it using keywords like
         ``NOW - 1 day``.
        :type modified_since: Union[str, int]
        :param include: When specified with the value of ``favoriteFlag``,
         results will either include a ``favorite`` attribute or
         ``parentObjectFavorite`` attribute depending on the type of
         object found by the search engine.
        :type include: Union[str, list[str]]
        :param scopes: If search fails, try using an array for each type
         of this comma-separated list of search filters. The following
         strings can be used to filter the search results:

            * ``attachments``: Search in attachments.
            * ``cellData``: Search in cell data.
            * ``comments``: Search in comments.
            * ``folderNames``: Search in folder names.
            * ``reportNames``: Search in report names.
            * ``sheetNames``: Search in sheet names.
            * ``sightNames``: Search in sight names.
            * ``summaryFields``: Search in summary fields.
            * ``templateNames``: Search in template names.
            * ``workspaceNames``: Search in workspace names.

        :type scopes: Union[str, list[str]]
        """
        self._require_auth()
        include = self._parse_include(self.SEARCH_INCLUDES, include)
        scopes = self._parse_scope(self.SEARCH_SCOPES, scopes)
        return self.smart.Search.search(
            query, include, location, modified_since, scopes
        ).results

    ## COLUMNS
    def _get_column_id(self, column: Union[int, str, Column]) -> int:
        """Returns the column ID for a column name. Can accept a
        column ID and will simply return it.
        """
        self._require_current_sheet()

        if isinstance(column, int):
            return column
        elif isinstance(column, str):
            for sheet_col in self.current_sheet.columns:
                if sheet_col.title == column:
                    return sheet_col.id
        elif isinstance(column, Column):
            return column.id
        else:
            raise TypeError(
                f"Invalid column type. Received {type(column)}, expected int or str."
            )
        raise ValueError(f"Column '{column}' not found.")

    def _parse_columns(self, columns: list[ColumnType]) -> list[Column]:
        """Parses a list of columns and returns a list of Column objects."""
        new_columns = []
        for column in columns:
            if isinstance(column, Column):
                new_columns.append(column)
            elif isinstance(column, dict):
                new_column = Column()
                for key, value in column.items():
                    try:
                        if key == "column_type":
                            key = "type"
                        setattr(new_column, key, value)
                    except AttributeError:
                        self.logger.warn(
                            f"Unable to set attribute '{key}' for column: {column}"
                        )
                new_columns.append(new_column)
            else:
                raise TypeError(
                    f"Invalid column type. Received {type(column)}, expected dict or Column."
                )
        return new_columns

    @keyword
    def list_columns(
        self, sheet_id: int = None, sheet_name: int = None
    ) -> list[Column]:
        """Returns a list of columns for the current sheet."""
        sheet_id = self._parse_sheet_id(sheet_id, sheet_name)
        column_result = self.smart.Sheets.get_columns(sheet_id, include_all=True)
        return self._unpack_index_result(column_result)

    @keyword
    def add_columns(
        self,
        columns: list[ColumnType] = None,
    ) -> list[Column]:
        """Adds columns to the current sheet. Columns must be defined as
        a list of dictionaries or Column objects. Dictionaries can have
        additional keys set, see `Add Column` keyword for more information.

        Column types must be supported by the `Smartsheet API`_

        .. _Smartsheet API: https://smartsheet.redoc.ly/tag/columnsRelated#section/Column-Types

        :param columns: Columns as a list of dictionaries or Column
         objects.
        :type columns: dict
        """
        self._require_current_sheet()

        new_columns = self._parse_columns(columns)
        column_response = self.smart.Sheets.add_columns(
            self.current_sheet.id, new_columns
        )
        return column_response.result

    @keyword
    def add_column(
        self,
        title: str,
        column_type: str = "TEXT_NUMBER",
        formula: Optional[str] = None,
        hidden: bool = False,
        index: Optional[int] = None,
        description: Optional[str] = None,
        primary: bool = False,
        format: Optional[str] = None,
        locked: bool = False,
        options: Optional[list[str]] = None,
        symbol: Optional[str] = None,
        validation: bool = False,
        width: Optional[int] = None,
    ):
        """Adds a column to the current sheet.

        :param title: Column title.
        :type title: str
        :param column_type: Column type, must be a `supported type`_.
         Defaults to ``TEXT_NUMBER``.
        :type column_type: str
        :param formula: Formula for the column (e.g., ``=data@row``).
         Defaults to ``None``.
        :type formula: str
        :param hidden: Whether the column is hidden. Defaults to ``False``.
        :type hidden: bool
        :param index: Index of the column. You can insert a column into
         and existing sheet by setting this index. Index is zero-based.
         Defaults to ``None`` which will add the column to the end of
         the sheet.
        :type index: int
        :param description: Column description. Defaults to ``None``.
        :type description: str
        :param primary: Whether the column is considered the primary
         key for indexing and searching. Defaults to ``False``.
        :param format: Column format using a `format descriptor`_
         string. Defaults to ``None``.
        :type format: str
        :param locked: Whether the column is locked. Defaults to ``False``.
        :type locked: bool
        :param options: List of options for a ``PICKLIST`` or
         ``MULTI_PICKLIST`` column. Defaults to ``None``.
        :param symbol: When a ``CHECKBOX`` or ``PICKLIST`` column has a
         display symbol, you can set the type of symbols by selected an
         appropriate string from the `symbol columns`_ definitions.
         Defaults to ``None``.
        :type symbol: str
        :param validation: Whether validation has been enabled. Defaults
         to ``False``.
        :type validation: bool
        :param width: Column width in pixels. Defaults to ``None``.
        :type width: int

        .. _symbol columns: https://smartsheet.redoc.ly/tag/columnsRelated/#section/Column-Types/Symbol-Columns
        .. _format descriptor: https://smartsheet.redoc.ly/#section/API-Basics/Formatting
        .. _supported type: https://smartsheet.redoc.ly/tag/columnsRelated/#section/Column-Types
        """
        self._require_current_sheet()
        return self.add_columns(
            [
                {
                    "title": title,
                    "type": column_type,
                    "formula": formula,
                    "hidden": hidden,
                    "index": index,
                    "description": description,
                    "primary": primary,
                    "format": format,
                    "locked": locked,
                    "options": options,
                    "symbol": symbol,
                    "validation": validation,
                    "width": width,
                }
            ]
        )

    @keyword
    def update_column(self, column: Union[int, str, Column], **kwargs) -> Column:
        """Updates a column in the current sheet.

        :param column: Column ID or title.
        :type column: int or str
        :param kwargs: Column attributes to update. See `Add Column` keyword
         for a list of supported attributes.
        :type kwargs: dict
        """
        self._require_current_sheet()
        column_id = self._get_column_id(column)
        column = self.smart.Sheets.get_column(self.current_sheet.id, column_id)
        for key, value in kwargs.items():
            try:
                setattr(column, key, value)
            except AttributeError:
                self.logger.warn(f"Unable to set attribute '{key}' for column.")
        column_response = self.smart.Sheets.update_column(column)
        return column_response.result

    ## ROWS
    def _parse_row_id(self, row: Union[int, Row]) -> int:
        """Returns the row ID from a row object or an integer."""
        if isinstance(row, int):
            return row
        elif isinstance(row, Row):
            return row.id
        else:
            raise ValueError("Invalid row type.")

    def _create_row_from_dict(self, row_dict: dict) -> Row:
        """Creates a row object from a dictionary."""
        row = Row()
        for key, value in row_dict.items():
            cell = Cell()
            cell.column_id = self._get_column_id(key)
            cell.value = value
            row.cells.append(cell)
        return row

    def _create_row_from_list(self, row_list: list[dict]) -> Row:
        """Creates a row object from a list."""
        row = Row()
        for cell_dict in row_list:
            cell = self._convert_dict_to_cell(cell_dict)
            row.cells.append(cell)
        return row

    def _convert_data_to_row(self, data: Union[dict, list, Row]) -> Row:
        """Converts a dictionary or list to a row object."""
        if isinstance(data, dict):
            return self._create_row_from_dict(data)
        elif isinstance(data, list):
            return self._create_row_from_list(data)
        elif isinstance(data, Row):
            return data
        else:
            raise TypeError(
                f"Invalid row type. Received {type(data)}, expected dict, list or Row."
            )

    @keyword
    def convert_row_to_dict(self, row: Row) -> OrderedDict:
        """Converts a row object to a dictionary."""
        row_dict = OrderedDict()
        for cell in row.cells:
            row_dict[cell.column_id] = cell.value
        return row_dict

    @keyword
    def get_row(
        self,
        row: Union[int, Row],
        include: CommaListType = None,
        exclude: CommaListType = None,
        native: bool = False,
    ) -> Row:
        """Returns a single row from the current sheet.

        You can provide the row as a native ``Row`` object or as an
        integer representing the row ID.
        """
        self._require_current_sheet()
        include = self._parse_include(self.ROW_INCLUDES, include)
        exclude = self._parse_exclude(self.ROW_EXCLUDES, exclude)
        row_id = self._parse_row_id(row)
        row = self.smart.Sheets.get_row(self.current_sheet.id, row_id)
        if native:
            return row
        else:
            return self.convert_row_to_dict(row)

    @keyword
    def set_rows(
        self,
        data: Union[list, Table],
        native: bool = False,
    ) -> list[Union[OrderedDict, Row]]:
        """Updates rows of the current sheet with the provided data.

        .. note::
           In order to update rows, you must identify the rows to the
           API. You can do this by providing the ``rowId`` or ``rowNumber``
           as a column in the data. The ID must be the API ID, while the
           number is the row number per the UI. This can only be excluded
           if the length of the data matches the length of the sheet.

        You can provide the data in several ways:

        * As a list of dictionaries: each list item represents a row
          as a single dictionary. The keys of the dictionary are the
          column IDs or Titles and the values are the values for the
          cells.
        * As a list of lists of dictionaries: each sub list item is
          a row and each dictionary is a cell. The keys of the dictionary
          should match cell attributes, e.g., ``column_id``, ``title``,
          ``value``, etc. See the `smartsheet API docs`_ for more
          information. The dictionary keys must be provided in snake
          case. You must use this method to set formulas on the row.
        * As a list of native ``Row`` objects: each ``Row`` object is a
          native object from the API with new values for the cells.
        * As a ``Table`` object: the columns of the Table must either
          be the column IDs or Titles.

        .. _smartsheet API docs: https://smartsheet.redoc.ly/tag/rows#operation/update-rows
        """
        self._require_current_sheet()
        # TODO: implement using row number instead of row ID and data
        # of same length as sheet.
        new_rows = []
        # The Table will iterate as dictionaries
        for row in data:
            new_rows.append(self._convert_data_to_row(row))
        row_update_response = self.smart.Sheets.update_rows(
            self.current_sheet.id, new_rows
        )
        self.logger.info(f"Updated {len(row_update_response.result)} rows.")
        if native:
            return row_update_response.result
        else:
            return [self.convert_row_to_dict(row) for row in row_update_response.result]

    @keyword
    def set_row(
        self,
        row: Union[int, Row],
        data: Union[dict, list[dict], Row] = None,
        native: bool = False,
    ) -> Union[dict, Row]:
        """Updates a single row of the current sheet with the provided data.

        You can provide the row as a native ``Row`` object or as an
        integer representing the row ID. You may omit the ``data``
        argument if you are providing a native ``Row`` object.

        You can provide the data in several ways:

        * As a dictionary: the keys of the dictionary are the
          column IDs or Titles and the values are the values for the
          cells.
        * As a list of dictionaries: each dictionary is a cell. The keys
          of the dictionary should match cell attributes, e.g., ``column_id``,
          ``title``, ``value``, etc. See the `smartsheet API docs`_ for more
          information. The dictionary keys must be provided in snake case.
          You must use this method to set formulas on the row.
        * As a native ``Row`` object: a native object from the API with
          new values for the cells.

        .. _smartsheet API docs: https://smartsheet.redoc.ly/tag/rows#operation/update-rows
        """
        self._require_current_sheet()
        if isinstance(row, Row) and data is None:
            data = row
        row_id = self._parse_row_id(row)
        new_row = self._convert_data_to_row(data)
        new_row.id = row_id
        return self.set_rows([new_row], native=native)[0]

    @keyword
    def add_rows(
        self, data: Union[list, Table], native: bool = False
    ) -> list[Union[OrderedDict, Row]]:
        """Adds rows to the current sheet with the provided data.

        You can provide the data in several ways:

        * As a list of dictionaries: each list item represents a row
          as a single dictionary. The keys of the dictionary are the
          column IDs or Titles and the values are the values for the
          cells.
        * As a list of lists of dictionaries: each sub list item is
          a row and each dictionary is a cell. The keys of the dictionary
          should match cell attributes, e.g., ``column_id``, ``title``,
          ``value``, etc. See the `smartsheet API docs`_ for more
          information. The dictionary keys must be provided in snake
          case. You must use this method to set formulas on the row.
        * As a list of native ``Row`` objects: each ``Row`` object is a
          native object from the API with new values for the cells.
        * As a ``Table`` object: the columns of the Table must either
          be the column IDs or Titles.

        .. _smartsheet API docs: https://smartsheet.redoc.ly/tag/rows#operation/add-rows
        """
        self._require_current_sheet()
        new_rows = []
        # Table will iterate as dictionaries
        for row in data:
            new_rows.append(self._convert_data_to_row(row))
        row_update_response = self.smart.Sheets.add_rows(
            self.current_sheet.id, new_rows
        )
        self.logger.info(f"Added {len(row_update_response.result)} rows.")
        if native:
            return row_update_response.result
        else:
            return [self.convert_row_to_dict(row) for row in row_update_response.result]

    ## CELLS
    def _convert_dict_to_cell(self, cell: dict) -> Cell:
        """Converts a dictionary to a Cell object."""
        new_cell = Cell()
        if isinstance(cell, dict):
            for key, value in cell.items():
                if key == "title":
                    new_cell.column_id = self._get_column_id(value)
                else:
                    try:
                        setattr(new_cell, key, value)
                    except AttributeError as e:
                        raise KeyError(
                            f"Invalid cell dictionary key, '{key}' does not match any "
                            f"cell attributes."
                        ) from e
        else:
            raise TypeError(f"Invalid cell type. Received {type(cell)}, expected dict.")
        return new_cell

    ## ATTACHMENTS
    def _download_row_attachments(
        self, row: Row, download_path: Path = None
    ) -> list[Path]:
        """Downloads all attachments from a row, saves them locally and
        returns a list of Paths to those attachements. Defaults to
        saving in the robot's ``OUTPUT_DIR``, but can be specified.
        Requires a current sheet.
        """
        self._require_current_sheet()
        attachment_result = self.smart.Attachments.list_row_attachments(
            self.current_sheet.id, row.id, include_all=True
        )
        attachments = self._unpack_index_result(attachment_result)
        return [self.download_attachment(a, download_path) for a in attachments]

    def _download_attachment_by_id(self, id: int, download_path: Path) -> Path:
        """Downloads the provided attachment using it's ID, requires
        a current sheet be selected."""
        self._require_current_sheet()
        attachment = self.smart.Attachments.get_attachment(self.current_sheet.id, id)
        download_result = self.smart.Attachments.download_attachment(
            attachment, str(download_path)
        )
        return Path(download_result.download_directory) / download_result.filename

    @keyword
    def list_attachments(self) -> list[Attachment]:
        """Gets a list of all attachments from the currently selected sheet.

        This will include attachments to the sheet, rows, and discussions.
        """
        self._require_current_sheet()
        attachment_result = self.smart.Attachments.list_all_attachments(
            self.current_sheet.id, include_all=True
        )
        return self._unpack_index_result(attachment_result)

    @keyword
    def download_attachment(
        self, attachment: Union[int, dict, Attachment], download_path: Path = None
    ) -> Path:
        """Downloads the provided attachment from the currently selected
        sheet to the provided download_path, which defaults to
        the ``${OUTPUT_DIR}``.

        The attachment can be provided as an integer representing the
        attachments ID, a dictionary with at least the key ``id`` or as
        the native ``Attachment`` data model type.

        :param attachment: An integar representing the attachment ID, a
         dictionary with at least the key ``id``, or a native
         ``Attachment`` data model object.
        """
        # TODO: Add example to documentation
        self._require_auth()
        download_path = download_path or get_output_dir()
        if not download_path.exists():
            download_path.mkdir()
        if isinstance(attachment, int) or isinstance(attachment, str):
            try:
                return self._download_attachment_by_id(attachment, download_path)
            except TypeError as e:
                raise TypeError("Attachment ID must be an integer.") from e
        elif isinstance(attachment, dict):
            if attachment.get("id", False):
                return self._download_attachment_by_id(attachment["id"], download_path)
            else:
                raise ValueError(
                    "The provided attachment dictionary does not "
                    "contain the 'id' key."
                )
        elif isinstance(attachment, Attachment):
            try:
                return self._download_attachment_by_id(attachment.id, download_path)
            except AttributeError as e:
                raise AttributeError("Attachment object does not have an ID.") from e
        else:
            raise TypeError(
                f"Invalid attachment type: received '{type(attachment)}', "
                f"expected 'int', 'dict' or 'Attachment'."
            )

    ## Users
    @keyword
    def get_current_user(self) -> User:
        """Gets the current authenticated user, which is also set in
        the library's memory as the current user. Call this again
        if you switch user or begin to impersonate a user.
        """
        self._require_auth()
        self.current_user = self.smart.Users.get_current_user()
        return self.current_user
