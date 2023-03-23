import logging
import os
from collections import OrderedDict
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from robot.api.deco import keyword, library
from robot.utils.robottime import parse_time, timestr_to_secs

from smartsheet import Smartsheet as SmartSDK
from smartsheet.models import (
    Attachment,
    Cell,
    Column,
    IndexResult,
    Row,
    ServerInfo,
    Sheet,
    SheetFilter,
    User,
)

# isort: off
# isort is not capable of sorting the try block correctly
from RPA.Robocorp.utils import PathType, get_output_dir
from RPA.version import __version__

try:
    from RPA.Tables import Table

    TABLES = True
except ImportError:
    TABLES = False
# isort: on


CommaListType = Union[str, List[Any]]
ColumnType = Union[Dict, Column]
RowType = Union[OrderedDict, Row]
if TABLES:
    TableType = Table
else:
    TableType = Any


class SmartsheetError(Exception):
    """Base error class for Smartsheet library."""


class SmartsheetAuthenticationError(SmartsheetError):
    """Error when authenticated Smartsheet instance does not exist."""


class SmartsheetNoSheetSelectedError(SmartsheetError):
    """Error when no sheet was selected to on which to perform the operation."""


def _require_auth(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.smart is None:
            raise SmartsheetAuthenticationError(
                "Authentication was not completed. "
                "Please use the Set access token keyword to authenticate."
            )
        return func(self, *args, **kwargs)

    return wrapper


@library(scope="GLOBAL", doc_format="REST")
class Smartsheet:
    """*Smartsheet* is a library for accessing Smartsheet using the
    `Smartsheet API 2.0`_. It extends `smartsheet-python-sdk`_.

    .. _Smartsheet API 2.0: https://smartsheet.redoc.ly/
    .. _smartsheet-python-sdk: https://github.com/smartsheet/smartsheet-python-sdk

    Getting started
    ===============

    To use this library, you need to have a Smartsheet account and an API token.
    You can get your API token from the `Smartsheet Developer Portal`_.
    This library currently only supports raw token authentication. Once
    obtained, you can configure the access token using the ``Set Access Token``
    keyword or via the ``access_token`` argument in the library import.

    .. _Smartsheet Developer Portal: https://smartsheet-platform.github.io/api-docs/

    Working on a sheet
    ==================

    The library supports working on a single sheet at a time. To select a sheet
    to work on, use the ``Select Sheet`` keyword. This will set the sheet as
    the active sheet for all subsequent operations. Some operations
    update the sheet, but this will not necessarily be reflected in the active
    sheet. To refresh the active sheet, use the ``Refresh Sheet`` keyword.

    Native Smartsheet objects
    =========================

    You can retrieve the native Smartsheet object from many keywords by
    specifying the ``native`` argument. The default will return a more
    common Python object, such as a dictionary or list. The native object
    is a class from the `smartsheet-python-sdk`_ library and will have
    additional methods and attributes. The most important attributes
    available for most native objects are (some may be unavailable
    for some objects):

    - ``id``: the unique identifier of the object
    - ``name``: the name of the object
    - ``title``: the title of a column
    - ``permalink``: the URL to the object
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
        ``Set access token``.

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

    # *** AUTH AND CONFIG ***
    def _set_token(self, access_token: Optional[str] = None):
        # The env var is used by the underlying client library if it exists. The
        # underlying library will throw an error if the env var is missing and no
        # access token was passed in.
        if (
            os.environ.get("SMARTSHEET_ACCESS_TOKEN", None) is None
            and access_token is None
        ):
            self.smart = None
        else:
            self.smart = SmartSDK(
                access_token=access_token,
                user_agent=f"rpaframework/{__version__}",
                max_retry_time=self.max_retry_time,
            )
            self.smart.errors_as_exceptions(True)
            # TODO: consider if this properly connects the logs.
            for handler in logging.getLogger("smartsheet").handlers:
                self.logger.addHandler(handler)

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

        Example:

        .. code-block:: robotframework

            Set Access Token  ${access_token}

        .. code-block:: python

            smartsheet = Smartsheet(access_token=access_token)
            # or
            smartsheet.set_access_token(access_token)
        """
        self._set_token(access_token)

    @keyword
    def set_max_retry_time(self, max_retry_time: Union[str, int]) -> Optional[int]:
        """Sets the max retry time to use when sending requests to the
        Smartsheet API. Returns the current max retry time.

        :param max_retry_time: Maximum time to allow retries of API
         calls. Can be provided as a time string or int.
        """
        old_time = self.max_retry_time
        self.max_retry_time = int(timestr_to_secs(max_retry_time, round_to=None))
        if self.smart is not None:
            # pylint: disable=protected-access
            # might be affected by smart's def of __getattr__ ... this is a patch
            # to allow modification of the calculated backoff time after init.
            self.smart._user_calc_backoff._max_retry_time = self.max_retry_time
        return old_time

    # *** UTILITY ***
    def _parse_comma_list_type(
        self, comma_list: Optional[CommaListType] = None
    ) -> Optional[List[str]]:
        if comma_list is None:
            return None
        elif isinstance(comma_list, str):
            return [s.strip() for s in comma_list.split(",")]
        elif isinstance(comma_list, list):
            return [str(s) for s in comma_list]
        else:
            raise TypeError(
                "Invalid type supplied as comma list, either provide a "
                "list object or a string of comma-separated values."
            )

    def _unpack_index_result(
        self, index_result: Optional[IndexResult] = None
    ) -> Optional[List[object]]:
        """Unpacks the provided IndexResult object into a list of the
        underlying type.
        """
        return index_result.data if index_result else None

    def _parse_include(
        self, include_type: Dict, include: Optional[CommaListType] = None
    ) -> Optional[List[str]]:
        """Parses the include parameter based on the provided include type."""
        include = self._parse_comma_list_type(include)
        if include is not None:
            includes = []
            for i in include:
                if str(i).upper() == "ALL":
                    includes = [str(k) for k in include_type]
                    break
                elif i in include_type:
                    includes.append(str(i))
                else:
                    raise ValueError(
                        f"Invalid or not implemented value(s) for include: {i}"
                    )
        else:
            includes = None
        return includes

    def _parse_exclude(
        self, exclude_type: List, exclude: CommaListType = None
    ) -> Optional[List[str]]:
        """Parses the exclude parameter based on the provided exclude type."""
        exclude = self._parse_comma_list_type(exclude)
        if exclude is not None and any(i not in exclude_type for i in exclude):
            raise ValueError("Invalid or not implemented value(s) for exclude.")
        return exclude

    def _parse_scope(
        self, scope_type: List, scope: Optional[CommaListType] = None
    ) -> List[str]:
        """Parses the scope parameter based on the provided scope type."""
        scope = self._parse_comma_list_type(scope)
        if scope is not None and any(i not in scope_type for i in scope):
            raise ValueError("Invalid or not implemented value(s) for scope.")
        return scope

    @keyword
    @_require_auth
    def get_application_constants(self) -> ServerInfo:
        """Gets application constants from the server. This is not
        necessary for most automation scenarios, but may be useful for
        debugging or for other advanced scenarios.
        """
        self.app_constants = self.smart.Server.server_info()
        return self.app_constants

    # *** SHEETS ***
    @property
    def sheets(self) -> List[Sheet]:
        """Full list of cached sheets."""
        if len(self._sheets) == 0:
            self._refresh_sheets()
        return self._sheets

    @_require_auth
    def _refresh_sheets(self):
        """Refreshes the ``sheets`` property."""
        self._sheets = self.smart.Sheets.list_sheets(include_all=True).data

    def _find_sheet(self, name: str) -> Optional[IndexResult]:
        """Finds a sheet by name and returns the ``IndexResult``, which
        can be used to pull sheet data with its ``id`` attribute.
        """
        for sheet in self.sheets:
            if sheet.name == name:
                return sheet
        return None

    def _parse_sheet_id(
        self, sheet_id: Optional[int] = None, sheet_name: Optional[str] = None
    ) -> Optional[int]:
        """Gets the sheet ID between the provided ID and/or Name."""
        if sheet_id is not None and sheet_name is not None:
            raise ValueError("You cannot provide both sheet_id and sheet_name.")
        if sheet_id is None and sheet_name is None:
            raise ValueError("You must provide either sheet_id or sheet_name.")
        if sheet_id is not None:
            return sheet_id
        if sheet_name is not None:
            try:
                return self._find_sheet(sheet_name).id
            except AttributeError as e:
                raise ValueError(f"Sheet '{sheet_name}' not found.") from e
        return None

    @keyword
    @_require_auth
    def list_sheets(self, use_cache: bool = True) -> List[Sheet]:
        """Lists all sheets available for the authenticated account. Uses
        cached lists if available unless ``use_cache`` is set to ``False``.

        The cached lists is used for other keywords, so if you need to
        refresh the cache for other keywords to use, you must do so
        via this keyword.

        :param use_cache: Defaults to ``True``. You can set to ``False``
         to force a reload of the cached list of sheets.

        Example:

        .. code-block:: robotframework

            ${sheets}=  List Sheets
            FOR  ${sheet}  IN  @{sheets}
                Log  ${sheet.name}

        .. code-block:: python

            ss = SmartsheetLibrary(account_token=account_token)
            sheets = ss.list_sheets()
            for sheet in sheets:
                print(sheet.name)
        """
        if not use_cache:
            self._refresh_sheets()

        return self.sheets

    @keyword
    def unselect_current_sheet(self) -> None:
        """Resets the current sheet to `None`."""
        self.current_sheet = None

    @keyword
    @_require_auth
    def get_sheet(
        self,
        sheet_id: Optional[int] = None,
        sheet_name: Optional[str] = None,
        include: Optional[CommaListType] = None,
        row_ids: Optional[CommaListType] = None,
        row_numbers: Optional[CommaListType] = None,
        column_ids: Optional[CommaListType] = None,
        filter_id: Optional[int] = None,
        native: bool = False,
        download_path: Optional[PathType] = None,
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
         ``rowPermalink``, or ``ALL``. Note that ``attachmentFiles``
         will only download files if you do not set ``native`` to
         ``True``.
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
        :param download_path: Defaults to ``None``. Can be set when
         ``attachmentFiles`` is included in the ``include`` parameter.
         All attachments will be downloaded to the provided directory.

        Example:

        .. code-block:: robotframework

            ${sheet}=  Get Sheet  sheet_name=My Sheet
            FOR  ${row}  IN  &{sheet}
                FOR  ${column}  ${value}  IN  &{row}
                    Log  The column ${column} has the value ${value}
                END
            END

        .. code-block:: python

            ss = Smartsheet(access_token=access_token)
            sheet = ss.get_sheet(sheet_name="My Sheet", native=True)
            for row in sheet:
                for cell in row:
                    print(f"The column {cell.column_id} has the value {cell.value}")
        """
        sheet_id = self._parse_sheet_id(sheet_id, sheet_name)
        # Smartsheet class defines a `__getattr__` which makes the below work, just
        # doesn't help with intellisense autocompletion.
        includes = self._parse_include(self.SHEET_INCLUDES, include)
        sheet = self.smart.Sheets.get_sheet(
            sheet_id,
            include=includes,
            row_ids=self._parse_comma_list_type(row_ids),
            row_numbers=self._parse_comma_list_type(row_numbers),
            exclude="filteredOutRows",
            column_ids=self._parse_comma_list_type(column_ids),
            filter_id=filter_id,
        )
        sheet.selected_includes = includes
        if download_path is not None:
            sheet.download_path = download_path
        self.current_sheet = sheet
        if native:
            return sheet
        else:
            return self.convert_sheet_to_table(sheet)

    @keyword
    def convert_sheet_to_table(self, sheet: Optional[Sheet] = None) -> Table:
        """Converts the current sheet to table. You can provide a differnt
        native sheet object to be converted via the ``sheet`` parameter.

        This keyword attempts to return the sheet as a table via
        ``RPA.Tables``, but if that library is not available in this
        context, the sheet is returned as its native data model (e.g.,
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
                elif hasattr(row, key_or_func):
                    row_data.append(getattr(row, key_or_func, None))

            table_data.append(row_data)

        table = Table(table_data, columns=headers)

        return table

    @keyword
    def refresh_sheet(self, native: bool = False) -> Union[TableType, Sheet]:
        """Refreshes the current sheet from the API and returns it
        either as a Table or native data model depending on the
        ``native`` argument.
        """
        self._require_current_sheet()
        sheet = self.smart.Sheets.get_sheet(self.current_sheet.id)
        self.current_sheet = sheet
        if native:
            return sheet
        else:
            return self.convert_sheet_to_table(sheet)

    @keyword
    def get_sheet_owner(
        self, sheet_id: Optional[int] = None, sheet_name: Optional[str] = None
    ) -> Tuple[str, int]:
        """Returns the owner's username and ID for the current sheet."""
        sheet_id = self._parse_sheet_id(sheet_id, sheet_name)
        sheet = self.smart.Sheets.get_sheet(sheet_id, include=["ownerInfo"])
        return sheet.owner, sheet.owner_id

    @keyword
    def list_sheet_filters(
        self, sheet_id: Optional[int] = None, sheet_name: Optional[str] = None
    ) -> Optional[List[SheetFilter]]:
        """Returns a list of available filters for the current sheet. You
        can specify a different sheet via the ``sheet_id`` or
        ``sheet_name`` parameters.

        The returned list of filters can be used with the ``filter_id``
        argument of the ``get_sheet`` keyword.

        Example:

        .. code-block:: robotframework

            ${filters}=  List Sheet Filters
            FOR  ${filter}  IN  @{filters}
                ${filtered_sheet}=  Get Sheet
                ...  sheet_name=My sheet
                ...  filter_id=${filter.id}
                Log  There are ${len(filtered_sheet)} rows in the filtered sheet
            END

        .. code-block:: python

            ss = Smartsheet(access_token=access_token)
            my_sheet_id = 123456789
            filters = ss.list_sheet_filters()
            for filter in filters:
                filtered_sheet = ss.get_sheet(
                    sheet_id=my_sheet_id,
                    filter_id=filter.id,
                    native=True,
                )
                print(
                    f"There are {len(filtered_sheet.rows)} rows in the "
                    f"filtered sheet"
                )
        """
        self._require_current_sheet()
        sheet_id = self._parse_sheet_id(sheet_id, sheet_name)
        filter_result = self.smart.Sheets.list_filters(
            sheet_id or self.current_sheet.id, include_all=True
        )
        return self._unpack_index_result(filter_result)

    @keyword
    @_require_auth
    def create_sheet(
        self,
        name: str,
        columns: Optional[List[ColumnType]] = None,
        from_sheet_id: Optional[Union[int, str]] = None,
    ) -> Sheet:
        """Creates a new sheet with the given name and columns, then sets
        the current sheet to the new sheet and returns it as a native
        Smartsheet object.

        :param name: Name of the new sheet.
        :param columns: List of columns to create in the new sheet.
        :param from_sheet_id: Sheet ID to use as a template for the new
         sheet.

        Example:

        .. code-block:: robotframework

            ${columns}=  Create List  Name  Email
            ${sheet}=  Create Sheet  My new sheet  ${columns}

        .. code-block:: python

            ss = Smartsheet(access_token=access_token)
            columns = [
                {"title": "Name", "type": "TEXT_NUMBER"},
                {"title": "Email", "type": "TEXT_NUMBER"},
            ]
            sheet = ss.create_sheet("My new sheet", columns)
        """
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
    @_require_auth
    def search(
        self,
        query: str,
        location: Optional[str] = None,
        modified_since: Optional[Union[str, int]] = None,
        include: Optional[CommaListType] = None,
        scopes: Optional[CommaListType] = None,
    ) -> List[Sheet]:
        """Searches for all sheets for text matching the query. Returns
        a list of native Smartsheet Sheet objects. You can use the
        additional parameters to filter the search and increase speed.

        :param query: The text to search for.
        :param location: The location to search. When specified with
         a value of ``personalWorkspace``, the search will be limited
         to the current user's personal workspace.
        :param modified_since: The date to search from. This can be
         either a string or an integer. If an integer is provided, it
         will be interpreted as a Unix timestamp. If a string is
         provided, it will be parsed via the Robot Framework time
         utilities, so you can provided it using keywords like
         ``NOW - 1 day``.
        :param include: When specified with the value of ``favoriteFlag``,
         results will either include a ``favorite`` attribute or
         ``parentObjectFavorite`` attribute depending on the type of
         object found by the search engine.
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


        Example:

        .. code-block:: robotframework

            ${sheets}=  Search  my search query
            FOR  ${sheet}  IN  @{sheets}
                Log  ${sheet.name}

        .. code-block:: python

            ss = Smartsheet(access_token=access_token)
            sheets = ss.search("my search query")
            for sheet in sheets:
                print(sheet.name)
        """
        include = self._parse_include(self.SEARCH_INCLUDES, include)
        scopes = self._parse_scope(self.SEARCH_SCOPES, scopes)
        if isinstance(modified_since, str):
            modified_since = parse_time(modified_since)
        if modified_since is not None:
            modified_since = datetime.fromtimestamp(modified_since)
        return self.smart.Search.search(
            query, include, location, modified_since, scopes
        ).results

    # *** COLUMNS ***
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
        raise ValueError(f"Column '{column!r}' not found.")

    def _parse_column(self, column: ColumnType) -> Column:
        """Parses a column and returns a Column object."""
        if isinstance(column, Column):
            return column
        elif isinstance(column, dict):
            new_column = Column()
            for key, value in column.items():
                try:
                    if key == "column_type":
                        key = "type"
                    setattr(new_column, key, value)
                except AttributeError:
                    self.logger.warning(
                        f"Unable to set attribute '{key}' for column: {column}"
                    )
            return new_column
        else:
            raise TypeError(
                f"Invalid column type. Received {type(column)}, "
                f"expected dict or Column."
            )

    def _parse_columns(self, columns: List[ColumnType]) -> List[Column]:
        """Parses a list of columns and returns a list of Column objects."""
        new_columns = []
        for column in columns:
            new_columns.append(self._parse_column(column))
        return new_columns

    @keyword
    def list_columns(
        self, sheet_id: Optional[int] = None, sheet_name: Optional[str] = None
    ) -> Optional[List[Column]]:
        """Returns a list of columns for the current sheet.

        :param sheet_id: The ID of the sheet to get columns from.
        :param sheet_name: The name of the sheet to get columns from.
        """
        sheet_id = self._parse_sheet_id(sheet_id, sheet_name)
        column_result = self.smart.Sheets.get_columns(sheet_id, include_all=True)
        return self._unpack_index_result(column_result)

    @keyword
    def add_columns(
        self,
        columns: List[ColumnType] = None,
    ) -> List[Column]:
        """Adds columns to the current sheet. Columns must be defined as
        a list of dictionaries or Column objects. Dictionaries can have
        additional keys set, see ``Add Column`` keyword for more information.

        Column types must be supported by the `Smartsheet API`_

        .. _Smartsheet API: https://smartsheet.redoc.ly/tag/columnsRelated#section/Column-Types

        :param columns: Columns as a list of dictionaries or Column
         objects.
        """  # noqa: E501
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
        format_string: Optional[str] = None,
        locked: bool = False,
        options: Optional[List[str]] = None,
        symbol: Optional[str] = None,
        validation: bool = False,
        width: Optional[int] = None,
    ):
        """Adds a column to the current sheet.

        :param title: Column title.
        :param column_type: Column type, must be a `supported type`_.
         Defaults to ``TEXT_NUMBER``.
        :param formula: Formula for the column (e.g., ``=data@row``).
         Defaults to ``None``.
        :param hidden: Whether the column is hidden. Defaults to ``False``.
        :param index: Index of the column. You can insert a column into
         and existing sheet by setting this index. Index is zero-based.
         Defaults to ``None`` which will add the column to the end of
         the sheet.
        :param description: Column description. Defaults to ``None``.
        :param primary: Whether the column is considered the primary
         key for indexing and searching. Defaults to ``False``.
        :param format_string: Column format using a `format descriptor`_
         string. Defaults to ``None``.
        :param locked: Whether the column is locked. Defaults to ``False``.
        :param options: List of options for a ``PICKLIST`` or
         ``MULTI_PICKLIST`` column. Defaults to ``None``.
        :param symbol: When a ``CHECKBOX`` or ``PICKLIST`` column has a
         display symbol, you can set the type of symbols by selected an
         appropriate string from the `symbol columns`_ definitions.
         Defaults to ``None``.
        :param validation: Whether validation has been enabled. Defaults
         to ``False``.
        :param width: Column width in pixels. Defaults to ``None``.

        .. _symbol columns: https://smartsheet.redoc.ly/tag/columnsRelated/#section/Column-Types/Symbol-Columns
        .. _format descriptor: https://smartsheet.redoc.ly/#section/API-Basics/Formatting
        .. _supported type: https://smartsheet.redoc.ly/tag/columnsRelated/#section/Column-Types

        Example:

        .. code-block:: robotframework

            Add Column  Title  TEXT_NUMBER
            Add Column  Description  TEXT_NUMBER  description=This is a description
            Add Column  Formula  TEXT_NUMBER  formula==data@row

        .. code-block:: python

            ss = Smartsheet(access_token=access_token)
            ss.add_column(title="Title", column_type="TEXT_NUMBER")
            ss.add_column(title="Description", column_type="TEXT_NUMBER", description="This is a description")
            ss.add_column(title="Formula", column_type="TEXT_NUMBER", formula="=data@row")
        """  # noqa: E501
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
                    "format": format_string,
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
        """Updates a column in the current sheet. See the ``Add Column`` keyword
        for a list of supported attributes.

        :param column: Column ID or title.
        :param kwargs: Column attributes to update. See ``Add Column`` keyword
         for a list of supported attributes.
        """
        self._require_current_sheet()
        column_id = self._get_column_id(column)
        column = self.smart.Sheets.get_column(self.current_sheet.id, column_id)
        for key, value in kwargs.items():
            try:
                setattr(column, key, value)
            except AttributeError:
                self.logger.warning(f"Unable to set attribute '{key}' for column.")
        column_response = self.smart.Sheets.update_column(column)
        return column_response.result

    # *** ROWS ***
    def _parse_row_id(self, row: Union[int, Row]) -> int:
        """Returns the row ID from a row object or an integer. This
        function will search the current sheet for the row ID if an
        integer is provided, if it is not found, it will treat the
        row as a row number and search the sheet for the row ID. If
        not found there, it will return the row as an ID, assuming
        it is a valid but unknown row.
        """
        if isinstance(row, int):
            if row not in [r.id for r in self.current_sheet.rows]:
                return self._get_row_from_number(row)
            else:
                return row
        elif isinstance(row, Row):
            return row.id
        else:
            raise ValueError("Invalid row type.")

    def _create_row_from_dict(self, row_dict: Dict) -> Row:
        """Creates a row object from a dictionary."""
        row = Row()
        for key, value in row_dict.items():
            cell = Cell()
            if key in ["rowId", "row_id", "id"]:
                row.id = value
            elif key in ["rowNumber", "row_number"]:
                row.id = self._get_row_from_number(value)
            else:
                cell.column_id = self._get_column_id(key)
                cell.value = value
                row.cells.append(cell)
        return row

    def _get_row_from_number(self, row_number: int) -> int:
        """Returns the row ID from a row number. If not found, it
        assumes the provided row_number may have been an ID and
        returns it.
        """
        self._require_current_sheet()
        for row in self.current_sheet.rows:
            if row.row_number == row_number:
                return row.id
        return row_number

    def _create_row_from_list(self, row_list: List[Dict]) -> Row:
        """Creates a row object from a list."""
        row = Row()
        for cell_dict in row_list:
            if cell_dict.get("title") == "rowId":
                row.id = cell_dict.get("value")
            elif cell_dict.get("title") == "rowNumber":
                row.id = self._get_row_from_number(cell_dict.get("value"))
            else:
                cell = self._convert_dict_to_cell(cell_dict)
                row.cells.append(cell)
        return row

    def _convert_data_to_row(self, data: Union[Dict, List, Row]) -> Row:
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
    ) -> Union[Row, OrderedDict]:
        """Returns a single row from the current sheet.

        You can provide the row as a native ``Row`` object or as an
        integer representing the row ID.
        """
        self._require_current_sheet()
        include = self._parse_include(self.ROW_INCLUDES, include)
        exclude = self._parse_exclude(self.ROW_EXCLUDES, exclude)
        row_id = self._parse_row_id(row)
        row = self.smart.Sheets.get_row(
            self.current_sheet.id, row_id, include=include, exclude=exclude
        )
        if native:
            return row
        else:
            return self.convert_row_to_dict(row)

    @keyword
    def set_rows(
        self,
        data: Union[List, Table],
        native: bool = False,
    ) -> List[RowType]:
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

        Examples:

        *Robot Framework:*

        .. code-block:: robotframework

            ${row1}=  Create Dictionary  rowId=123  column1=value1  column2=value2
            ${row2}=  Create Dictionary  rowId=456  column1=value3  column2=value4
            ${row3}=  Create Dictionary  rowId=789  column1=value5  column2=value6
            ${data} =  Create List  ${row1}  ${row2}  ${row3}
            Set Rows  ${data}

            # Or work with native row objects to update them.
            ${row1}=  Get Row  123
            FOR  ${cell}  IN  @{row1.cells}
                IF  ${cell.column_id} == 123
                    ${cell.value}=  Set Variable  New Value
                END
            END
            ${data}=  Create List  ${row1}
            Set Rows  ${data}

        *Python:*

        .. code-block:: python

            ss = Smartsheet(access_token=access_token)
            row1 = {"rowId": 123, "column1": "value1", "column2": "value2"}
            row2 = {"rowId": 456, "column1": "value3", "column2": "value4"}
            row3 = {"rowId": 789, "column1": "value5", "column2": "value6"}
            data = [row1, row2, row3]
            ss.set_rows(data)

            # or work with native row objects to update them.
            row1 = ss.get_row(123)
            for cell in row1.cells:
                if cell.column_id == 123:
                    cell.value = "New Value"
            data = [row1]
            ss.set_rows(data)
        """  # noqa: E501
        self._require_current_sheet()
        new_rows = []
        # The Table will iterate as dictionaries
        for row in data:
            new_rows.append(self._convert_data_to_row(row))
        if len(new_rows) == len(self.current_sheet.rows):
            for i, row in enumerate(self.current_sheet.rows):
                new_rows[i].id = row.id
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
        data: Union[Dict, List[Dict], Row] = None,
        native: bool = False,
    ) -> Union[Dict, Row]:
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

        For examples, see ``Set Rows``.
        """  # noqa: E501
        self._require_current_sheet()
        if isinstance(row, Row) and data is None:
            data = row
        row_id = self._parse_row_id(row)
        new_row = self._convert_data_to_row(data)
        new_row.id = row_id
        return self.set_rows([new_row], native=native)[0]

    @keyword
    def add_rows(self, data: Union[List, Table], native: bool = False) -> List[RowType]:
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

        Examples:

        *Robot Framework:*

        .. code-block:: robotframework

            ${row1}=  Create Dictionary  column1=value1  column2=value2
            ${row2}=  Create Dictionary  column1=value3  column2=value4
            ${row3}=  Create Dictionary  column1=value5  column2=value6
            ${data} =  Create List  ${row1}  ${row2}  ${row3}
            Add Rows  ${data}

        *Python:*

        .. code-block:: python

            ss = Smartsheet(access_token=access_token)
            row1 = {"column1": "value1", "column2": "value2"}
            row2 = {"column1": "value3", "column2": "value4"}
            row3 = {"column1": "value5", "column2": "value6"}
            data = [row1, row2, row3]
            ss.set_rows(data)
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

    # *** CELLS ***
    def _convert_dict_to_cell(self, cell: Dict) -> Cell:
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

    @keyword
    def get_cell_history(
        self, row: Union[int, Row], column: Union[int, str, Column]
    ) -> Optional[List[Cell]]:
        """Retrieves the history of a cell in a row of the current sheet.

        :param row: The row ID, row number, or a Row object.
        :param column: The column ID or title.

        Examples:

        *Robot Framework:*

        .. code-block:: robotframework

            ${cell_history}=  Get Cell History  1  Approval
            FOR  ${revision} IN  @{cell_history}
                Log  Modified by ${revision.modified_by.email}
            END

        *Python:*

        .. code-block:: python

            ss = Smartsheet(access_token=access_token)
            cell_history = ss.get_cell_history(1, "Approval")
            for revision in cell_history:
                print(f"Modified by {revision.modified_by.email}")
        """
        self._require_current_sheet()
        row_id = self._parse_row_id(row)
        column_id = self._get_column_id(column)
        cell_history = self.smart.Cells.get_cell_history(
            self.current_sheet.id, row_id, column_id, include_all=True
        )
        return self._unpack_index_result(cell_history)

    # *** ATTACHMENTS ***
    def _download_row_attachments(
        self, row: Union[int, Row], download_path: PathType = None
    ) -> List[Path]:
        """Downloads all attachments from a row, saves them locally and
        returns a list of Paths to those attachements. Defaults to
        saving in the robot's ``OUTPUT_DIR``, but can be specified.
        Requires a current sheet.

        If ``download_path`` is not set, it will attempt to use the
        attribute ``download_path`` set to the ``current_sheet``.

        :param row: The row ID, row number, or a Row object.
        :param download_path: The path to save the attachments to.
        """
        self._require_current_sheet()
        attachment_result = self.smart.Attachments.list_row_attachments(
            self.current_sheet.id, self._parse_row_id(row), include_all=True
        )
        attachments = self._unpack_index_result(attachment_result)
        download_path = Path(
            download_path
            or getattr(self.current_sheet, "download_path", None)
            or get_output_dir()
        )
        return [self.download_attachment(a, download_path) for a in attachments]

    def _download_attachment_by_id(
        self, attachment_id: int, download_path: Path = None
    ) -> Path:
        """Downloads the provided attachment using it's ID, requires
        a current sheet be selected. If ``download_path`` is not set,
        it will attempt to use the attribute ``download_path`` set to
        the ``current_sheet``.
        """
        self._require_current_sheet()
        attachment = self.smart.Attachments.get_attachment(
            self.current_sheet.id, attachment_id
        )
        download_result = self.smart.Attachments.download_attachment(
            attachment,
            str(
                download_path
                or getattr(self.current_sheet, "download_path", None)
                or get_output_dir()
            ),
        )
        return Path(download_result.download_directory) / download_result.filename

    @keyword
    def list_attachments(self) -> Optional[List[Attachment]]:
        """Gets a list of all attachments from the currently selected sheet.

        This will include attachments to the sheet, rows, and discussions.

        Examples:

        *Robot Framework:*

        .. code-block:: robotframework

            ${attachments}=  List Attachments
            FOR  ${attachment} IN  @{attachments}
                Log  ${attachment.name}
            END

        *Python:*

        .. code-block:: python

            ss = Smartsheet(access_token=access_token)
            attachments = ss.list_attachments()
            for attachment in attachments:
                print(attachment.name)
        """
        self._require_current_sheet()
        attachment_result = self.smart.Attachments.list_all_attachments(
            self.current_sheet.id, include_all=True
        )
        return self._unpack_index_result(attachment_result)

    @keyword
    @_require_auth
    def download_attachment(
        self,
        attachment: Union[int, str, Dict, Attachment],
        download_path: Optional[Union[str, Path]] = None,
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
        :param download_path: The path to save the attachment to.

        Examples:

        *Robot Framework:*

        .. code-block:: robotframework

            ${attachment}=  Get Attachment  123456789
            ${path}=  Download Attachment  ${attachment}
            Log  ${path}

        *Python:*

        .. code-block:: python

            ss = Smartsheet(access_token=access_token)
            attachment = ss.get_attachment(123456789)
            path = ss.download_attachment(attachment)
            print(path)
        """
        download_path = Path(download_path or get_output_dir()).expanduser().resolve()
        download_path.mkdir(parents=True, exist_ok=True)

        if isinstance(attachment, (int, str)):
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
                f"expected 'int', 'str', 'dict' or 'Attachment'."
            )

    # *** USERS ***
    @keyword
    @_require_auth
    def get_current_user(self) -> User:
        """Gets the current authenticated user, which is also set in
        the library's memory as the current user. Call this again
        if you switch user or begin to impersonate a user.
        """
        self.current_user = self.smart.Users.get_current_user()
        return self.current_user
