from typing import Dict, List, Optional

from . import (
    LibraryContext,
    keyword,
)


class SheetsKeywords(LibraryContext):
    """Keywords for Google Sheets operations"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword(tags=["init", "sheets"])
    def init_sheets(
        self,
        service_account: str = None,
        credentials: str = None,
        use_robocorp_vault: Optional[bool] = None,
        scopes: list = None,
        token_file: str = None,
    ) -> None:
        """Initialize Google Sheets client

        :param service_account: file path to service account file
        :param credentials: file path to credentials file
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param scopes: list of extra authentication scopes
        :param token_file: file path to token file
        """
        sheets_scopes = ["drive", "drive.file", "spreadsheets"]
        if scopes:
            sheets_scopes += scopes
        self.service = self.init_service(
            service_name="sheets",
            api_version="v4",
            scopes=sheets_scopes,
            service_account_file=service_account,
            credentials_file=credentials,
            use_robocorp_vault=use_robocorp_vault,
            token_file=token_file,
        )

    @keyword(tags=["sheets"])
    def create_sheet(self, title: str) -> str:
        """Create empty sheet with a title

        :param title: name as string
        :return: created `sheet_id`

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=  Create Sheet   Example Sheet
        """
        if not title:
            raise KeyError("title is required for kw: create_sheet")

        data = {"properties": {"title": title}}
        spreadsheet = (
            self.service.spreadsheets()
            .create(body=data, fields="spreadsheetId")
            .execute()
        )
        return spreadsheet.get("spreadsheetId")

    @keyword(tags=["sheets"])
    def insert_sheet_values(
        self,
        sheet_id: str,
        sheet_range: str,
        values: list,
        major_dimension: str = "COLUMNS",
        value_input_option: str = "USER_ENTERED",
    ) -> Dict:
        """Insert values into sheet cells

        :param sheet_id: target sheet
        :param sheet_range: target sheet range
        :param values: list of values to insert into sheet
        :param major_dimension: major dimension of the values, default `COLUMNS`
        :param value_input_option: controls whether input strings are parsed or not,
         default `USER_ENTERED`
        :return: operation result

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${values}   Evaluate   [[11, 12, 13], ['aa', 'bb', 'cc']]
            ${result}=  Insert Sheet Values   ${SHEET_ID}  A:B  ${values}
            ${result}=  Insert Sheet Values   ${SHEET_ID}  A:B  ${values}  ROWS
        """
        resource = {"majorDimension": major_dimension, "values": values}
        return (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=sheet_id,
                range=sheet_range,
                body=resource,
                valueInputOption=value_input_option,
            )
            .execute()
        )

    @keyword(tags=["sheets"])
    def update_sheet_values(
        self,
        sheet_id: str,
        sheet_range: str,
        values: list,
        major_dimension: str = "COLUMNS",
        value_input_option: str = "USER_ENTERED",
    ) -> Dict:
        """Insert values into sheet cells

        :param sheet_id: target sheet
        :param sheet_range: target sheet range
        :param values: list of values to insert into sheet
        :param major_dimension: major dimension of the values, default `COLUMNS`
        :param value_input_option: controls whether input strings are parsed or not,
         default `USER_ENTERED`
        :return: operation result

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${row}  Evaluate   [[22, 33 ,44]]
            ${result}=  Update Sheet Values  ${SHEET_ID}  A6:C6  ${row}   ROWS
        """
        resource = {"majorDimension": major_dimension, "values": values}
        return (
            self.service.spreadsheets()
            .values()
            .update(
                spreadsheetId=sheet_id,
                range=sheet_range,
                body=resource,
                valueInputOption=value_input_option,
            )
            .execute()
        )

    @keyword(tags=["sheets"])
    def get_sheet_values(
        self,
        sheet_id: str,
        sheet_range: str,
        value_render_option: str = "UNFORMATTED_VALUE",
        datetime_render_option: str = "FORMATTED_STRING",
    ) -> List:
        """Get values from the range in the sheet

        :param sheet_id: target sheet
        :param sheet_range: target sheet range
        :param value_render_option: how values should be represented
         in the output defaults to "UNFORMATTED_VALUE"
        :param datetime_render_option: how dates, times, and durations should be
         represented in the output, defaults to "FORMATTED_STRING"
        :return: operation result

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${values}=  Get Sheet Values  ${SHEET_ID}  A1:C1
        """  # noqa: E501
        return (
            self.service.spreadsheets()
            .values()
            .get(
                spreadsheetId=sheet_id,
                range=sheet_range,
                valueRenderOption=value_render_option,
                dateTimeRenderOption=datetime_render_option,
            )
            .execute()
        )

    @keyword(tags=["sheets"])
    def clear_sheet_values(self, sheet_id: str, sheet_range: str) -> Dict:
        """Clear cell values for range of cells within a sheet

        :param sheet_id: target sheet
        :param sheet_range: target sheet range
        :return: operation result

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=  Clear Sheet Values  ${SHEET_ID}  A1:C1
        """
        return (
            self.service.spreadsheets()
            .values()
            .clear(
                spreadsheetId=sheet_id,
                range=sheet_range,
            )
            .execute()
        )

    @keyword(tags=["sheets"])
    def copy_sheet(self, sheet_id: str, target_sheet_id: str) -> Dict:
        """Copy spreadsheet to target spreadsheet

        *NOTE:* service account user must have access to
        target sheet also

        :param sheet_id: ID of the sheet to copy
        :param target_sheet_id: ID of the target sheet
        :return: operation result

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=  Copy Sheet   ${SHEET_ID}  ${NEW_SHEET}
        """
        body = {
            "destination_spreadsheet_id": target_sheet_id,
        }
        return (
            self.service.spreadsheets()
            .sheets()
            .copyTo(
                spreadsheetId=sheet_id,
                sheetId=0,
                body=body,
            )
            .execute()
        )
