from apiclient import discovery
from google.oauth2 import service_account
import os
from typing import (
    List,
    Union,
)
from RPA.Cloud.Google.keywords import (
    LibraryContext,
    keyword,
)


class SheetsKeywords(LibraryContext):
    """Keywords for Google Sheets operations"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword
    def init_sheets_client(
        self,
        service_credentials_file: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Sheets client

        :param service_credentials_file: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self._scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        service_account_file = None
        if use_robocloud_vault:
            service_account_file = self._get_service_account_from_robocloud()
        elif service_credentials_file:
            service_account_file = service_credentials_file
        try:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=self._scopes
            )
            self.service = discovery.build(
                "sheets", "v4", credentials=credentials, cache_discovery=False
            )
        except OSError as e:
            raise AssertionError from e
        finally:
            if use_robocloud_vault:
                os.remove(service_account_file)

    @keyword
    def create_sheet(self, title: str) -> str:
        """Create empty sheet with a title

        :param title: name as string
        :return: created `sheet_id`
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

    @keyword
    def insert_values(
        self,
        sheet_id: str,
        sheet_range: str,
        values: list,
        major_dimension: str = "COLUMNS",
        value_input_option: str = "USER_ENTERED",
    ) -> None:
        """Insert values into sheet cells

        :param sheet_id: target sheet
        :param sheet_range: target sheet range
        :param values: list of values to insert into sheet
        :param major_dimension: major dimension of the values, default `COLUMNS`
        :param value_input_option: controls whether input strings are parsed or not,
         default `USER_ENTERED`
        """
        if not sheet_id or not sheet_range:
            raise KeyError(
                "sheet_id and sheet_range are required for kw: insert_values"
            )
        if not values:
            raise ValueError("Please provide list of values to insert into sheet")

        datavalues = []
        for val in values:
            datavalues.append([val])
        resource = {"majorDimension": major_dimension, "values": datavalues}
        self.service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=sheet_range,
            body=resource,
            valueInputOption=value_input_option,
        ).execute()

    @keyword
    def update_values(
        self,
        sheet_id: str,
        sheet_range: str,
        values: list,
        major_dimension: str = "ROWS",
        value_input_option: str = "USER_ENTERED",
    ) -> None:
        """Insert values into sheet cells

        :param sheet_id: target sheet
        :param sheet_range: target sheet range
        :param values: list of values to insert into sheet
        :param major_dimension: major dimension of the values, default `COLUMNS`
        :param value_input_option: controls whether input strings are parsed or not,
         default `USER_ENTERED`
        """
        if not sheet_id or not sheet_range:
            raise KeyError(
                "sheet_id and sheet_range are required for kw: insert_values"
            )
        if not values:
            raise ValueError("Please provide list of values to insert into sheet")

        datavalues = []
        # for val in values:
        #    datavalues.append([val])
        resource = {"majorDimension": major_dimension, "values": values}
        self.service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=sheet_range,
            body=resource,
            valueInputOption=value_input_option,
        ).execute()

    @keyword
    def get_values(
        self,
        sheet_id: str,
        sheet_range: str,
        value_render_option: str = "UNFORMATTED_VALUE",
        datetime_render_option: str = "FORMATTED_STRING",
    ) -> list:
        """Get values from the range in the sheet

        :param sheet_id: target sheet
        :param sheet_range: target sheet range
        :param value_render_option: how values should be represented
         in the output defaults to "UNFORMATTED_VALUE"
        :param datetime_render_option: how dates, times, and durations should be
         represented in the output, defaults to "FORMATTED_STRING"
        """  # noqa: E501
        values = (
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
        return values

    @keyword
    def clear_values(self, sheet_id: str, sheet_range: str) -> None:
        """Clear cell values for range of cells within a sheet

        :param sheet_id: target sheet
        :param sheet_range: target sheet range
        """
        self.service.spreadsheets().values().clear(
            spreadsheetId=sheet_id,
            range=sheet_range,
        ).execute()