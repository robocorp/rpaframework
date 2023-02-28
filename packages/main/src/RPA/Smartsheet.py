# builtin imports
import logging
import os
from typing import Union, Optional, Any
from pathlib import Path

# Robot imports
from robot.api.deco import keyword, library
from robot.utils.robottime import timestr_to_secs
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
from smartsheet import Smartsheet as smart_sdk
from smartsheet.models import (
    Sheet,
    Column,
    Row,
    Attachment,
    IndexResult,
    SheetFilter,
    User,
    ServerInfo,
)

CommaListType = Union[str, list[Any]]
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

    # Only implemented includes are available, others exist for the API
    ROW_METADATA = {
        "attachments": "attachments",
        "attachmentFiles": None,  # function must be set in __init__
        "discussions": "discussions",
        "rowPermalink": "permalink",
    }
    """List of supported additional objects to ask for via ``include`` 
    parameters for sheets and rows.
    """

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
        self.ROW_METADATA["attachmentFiles"] = self._download_row_attachments
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
        include = self._parse_comma_list_type(include)
        if include is not None and "ALL" not in include:
            if [i not in self.ROW_METADATA.keys() for i in include]:
                raise ValueError("Invalid or not implemented value(s) for include.")
        elif include is not None and "ALL" in include:
            includes = [str(k) for k in self.ROW_METADATA.keys()]
        else:
            includes = include
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
            for _, key_or_func in includes:
                if callable(key_or_func):
                    row_data.append(key_or_func(row))
                elif getattr(row, key_or_func, False):
                    row_data.append(
                        getattr(row, key_or_func, None)
                    )  # TODO: Check if it returns lists of the expected objects or not.

            table_data.append(row_data)

        table = Table(table_data, columns=headers)

        return table

    @keyword
    def get_sheet_owner(
        self, sheet_id: int = None, sheet_name: int = None, native=False
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
