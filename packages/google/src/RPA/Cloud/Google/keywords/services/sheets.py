from RPA.Cloud.Google.keywords import LibraryContext, keyword


class SheetsKeywords(LibraryContext):
    """Keywords for Google Sheets operations"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword
    def init_sheets(
        self,
        service_account: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Sheets client

        :param service_credentials_file: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        self.service = self.init_service(
            "sheets", "v4", scopes, service_account, use_robocloud_vault
        )

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

    @keyword
    def copy_sheet(self, spreadsheet_id, target_sheet_id):
        """Copy spreadsheet to target spreadsheet

        *NOTE:* service account user must have access to
        target sheet also

        :param spreadsheet_id: ID of the sheet to copy
        :param target_sheet_id: ID of the target sheet
        :return: request response
        """
        body = {
            "destination_spreadsheet_id": target_sheet_id,
        }
        return (
            self.service.spreadsheets()
            .sheets()
            .copyTo(
                spreadsheetId=spreadsheet_id,
                sheetId=0,
                body=body,
            )
            .execute()
        )

    def _sheet_values_action(
        self,
        sheet_id,
        sheet_range,
        values=None,
        major_dimension="COLUMNS",
        value_input_option="USER_ENTERED",
        value_render_option="UNFORMATTED_VALUE",
        datetime_render_option="FORMATTED_STRING",
        default_value_for_empty=None,
        action="insert",
    ) -> None:
        """Insert values into sheet cells

        :param sheet_id: target sheet
        :param sheet_range: target sheet range
        :param values: list of values to insert into sheet
        :param major_dimension: major dimension of the values, default `COLUMNS`
        :param value_input_option: controls whether input strings are parsed or not,
         default `USER_ENTERED`
        :param value_render_option: how values should be represented
         in the output defaults to "UNFORMATTED_VALUE"
        :param datetime_render_option: how dates, times, and durations should be
         represented in the output, defaults to "FORMATTED_STRING"
        """
        if action in ["insert", "update"] and not values:
            raise ValueError("Please provide list of values to insert into sheet")

        returnable = None

        sheet_values = self.service.spreadsheets().values()
        if action == "insert":
            resource = {"majorDimension": major_dimension, "values": values}
            returnable = sheet_values.append(
                spreadsheetId=sheet_id,
                range=sheet_range,
                body=resource,
                valueInputOption=value_input_option,
            ).execute()
        elif action == "update":
            resource = {"majorDimension": "ROWS", "values": values}
            returnable = sheet_values.update(
                spreadsheetId=sheet_id,
                range=sheet_range,
                body=resource,
                valueInputOption=value_input_option,
            ).execute()
        elif action == "get":
            self.logger.info(
                "Default value for empty (type): %s" % type(default_value_for_empty)
            )
            returnable = sheet_values.get(
                spreadsheetId=sheet_id,
                range=sheet_range,
                valueRenderOption=value_render_option,
                dateTimeRenderOption=datetime_render_option,
            ).execute()
            max_len = max(len(item) for item in returnable["values"])
            for item in returnable["values"]:
                if len(item) < max_len:
                    item.extend([default_value_for_empty] * (max_len - len(item)))
        elif action == "clear":
            returnable = sheet_values.clear(
                spreadsheetId=sheet_id,
                range=sheet_range,
            ).execute()
        else:
            raise AttributeError('Unsupported Google Sheets action: "%s"' % action)

        return returnable
