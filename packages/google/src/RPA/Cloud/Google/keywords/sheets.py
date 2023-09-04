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
    def create_spreadsheet(self, title: str) -> str:
        """Create empty sheet with a title

        :param title: name as string
        :return: created `spreadsheet_id`

        **Examples**

        **Python**

        .. code-block:: python

            result = GOOGLE.create_spreadsheet("name of the spreadsheet")

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
        spreadsheet_id: str,
        sheet_range: str,
        values: list,
        major_dimension: str = "COLUMNS",
        value_input_option: str = "USER_ENTERED",
    ) -> Dict:
        """Insert values into sheet cells

        :param spreadsheet_id: target spreadsheet
        :param sheet_range: target sheet range
        :param values: list of values to insert into sheet
        :param major_dimension: major dimension of the values, default `COLUMNS`
        :param value_input_option: controls whether input strings are parsed or not,
         default `USER_ENTERED`
        :return: operation result

        **Examples**

        **Python**

        .. code-block:: python

            values = [[11, 12, 13], ['aa', 'bb', 'cc']]
            result = GOOGLE.insert_sheet_values(spreadsheet_id, "A:C", values)

        **Robot Framework**

        .. code-block:: robotframework

            ${values}   Evaluate   [[11, 12, 13], ['aa', 'bb', 'cc']]
            ${result}=  Insert Sheet Values   ${SPREADSHEET_ID}  A:B  ${values}
            ${result}=  Insert Sheet Values   ${SPREADSHEET_ID}  A:B  ${values}  ROWS
        """
        resource = {"majorDimension": major_dimension, "values": values}
        return (
            self.service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=sheet_range,
                body=resource,
                valueInputOption=value_input_option,
            )
            .execute()
        )

    @keyword(tags=["sheets"])
    def update_sheet_values(
        self,
        spreadsheet_id: str,
        sheet_range: str,
        values: list,
        major_dimension: str = "COLUMNS",
        value_input_option: str = "USER_ENTERED",
    ) -> Dict:
        """Insert values into sheet cells

        :param spreadsheet_id: target spreadsheet
        :param sheet_range: target sheet range
        :param values: list of values to insert into sheet
        :param major_dimension: major dimension of the values, default `COLUMNS`
        :param value_input_option: controls whether input strings are parsed or not,
         default `USER_ENTERED`
        :return: operation result

        **Examples**

        **Python**

        .. code-block:: python

            row_data = [[11, 12, 13], ['aa', 'bb', 'cc']]
            result = GOOGLE.update_sheet_values(
                spreadsheet_id,
                "A1:C1",
                row_data,
                "ROWS
                )

        **Robot Framework**

        .. code-block:: robotframework

            ${row}  Evaluate   [[22, 33 ,44]]
            ${result}=  Update Sheet Values
            ...   ${SPREADSHEET_ID}
            ...   A6:C6
            ...   ${row}
            ...   ROWS
        """
        resource = {"majorDimension": major_dimension, "values": values}
        return (
            self.service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=sheet_range,
                body=resource,
                valueInputOption=value_input_option,
            )
            .execute()
        )

    @keyword(tags=["sheets"])
    def get_sheet_values(
        self,
        spreadsheet_id: str,
        sheet_range: str = None,
        value_render_option: str = "UNFORMATTED_VALUE",
        datetime_render_option: str = "FORMATTED_STRING",
    ) -> List:
        """Get values from the range in the spreadhsheet

        :param spreadsheet_id: target spreadsheet
        :param sheet_range: target sheet range
        :param value_render_option: how values should be represented
         in the output defaults to "UNFORMATTED_VALUE"
        :param datetime_render_option: how dates, times, and durations should be
         represented in the output, defaults to "FORMATTED_STRING"
        :return: operation result

        **Examples**

        **Python**

        .. code-block:: python

            result = GOOGLE.get_sheet_values(spreadsheet_id, "A1:C1")

        **Robot Framework**

        .. code-block:: robotframework

            ${values}=  Get Sheet Values  ${SPREADSHEET_ID}  A1:C1
        """  # noqa: E501
        parameters = {
            "spreadsheetId": spreadsheet_id,
            "range": sheet_range,
            "valueRenderOption": value_render_option,
            "dateTimeRenderOption": datetime_render_option,
        }

        return self.service.spreadsheets().values().get(**parameters).execute()

    @keyword(tags=["sheets"])
    def get_all_sheet_values(
        self,
        spreadsheet_id: str,
        sheet_name: str = None,
        value_render_option: str = "UNFORMATTED_VALUE",
        datetime_render_option: str = "FORMATTED_STRING",
    ) -> List:
        """Get values from the range in the spreadsheet

        :param spreadsheet_id: target spreadsheet
        :param sheet_name: target sheet (default first sheet)
        :param value_render_option: how values should be represented
         in the output defaults to "UNFORMATTED_VALUE"
        :param datetime_render_option: how dates, times, and durations should be
         represented in the output, defaults to "FORMATTED_STRING"
        :return: operation result

        **Examples**

        **Python**

        .. code-block:: python

            result = GOOGLE.get_all_sheet_values(spreadsheet_id)

        **Robot Framework**

        .. code-block:: robotframework

            ${values}=  Get All Sheet Values  ${SHEET_ID}  sheet1
        """  # noqa: E501
        parameters = {
            "spreadsheetId": spreadsheet_id,
            "valueRenderOption": value_render_option,
            "dateTimeRenderOption": datetime_render_option,
        }
        sheet_info = self.get_spreadsheet_basic_information(spreadsheet_id)
        if sheet_name:
            sheet_match = list(
                filter(lambda sheet: sheet["title"] == sheet_name, sheet_info["sheets"])
            )
            if len(sheet_match) != 1:
                raise KeyError(f"Sheet {sheet_name} not found")
            found_sheet = sheet_match[0]
        else:
            found_sheet = sheet_info["sheets"][0]

        sheet_title = found_sheet["title"]
        target_column = self.to_column_letter(found_sheet["columns"])
        rows = found_sheet["rows"]
        parameters["range"] = f"{sheet_title}!A1:{target_column}{rows}"

        return self.service.spreadsheets().values().get(**parameters).execute()

    @keyword(tags=["sheets"])
    def clear_sheet_values(self, spreadsheet_id: str, sheet_range: str) -> Dict:
        """Clear cell values for range of cells within a spreadsheet

        :param spreadsheet_id: target spreadsheet
        :param sheet_range: target sheet range
        :return: operation result

        **Examples**

        **Python**

        .. code-block:: python

            result = GOOGLE.clear_sheet_values(spreadsheet_id, "A1:C1")

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=  Clear Sheet Values  ${SPREADSHEET_ID}  A1:C1
        """
        return (
            self.service.spreadsheets()
            .values()
            .clear(
                spreadsheetId=spreadsheet_id,
                range=sheet_range,
            )
            .execute()
        )

    @keyword(tags=["sheets"])
    def copy_spreadsheet(self, spreadsheet_id: str, target_spreadsheet_id: str) -> Dict:
        """Copy spreadsheet to target spreadsheet

        *NOTE:* service account user must have access
        also to target spreadsheet

        :param spreadsheet_id: ID of the spreadsheet to copy
        :param target_spreadsheet_id: ID of the target spreadsheet
        :return: operation result

        **Examples**

        **Python**

        .. code-block:: python

            result = GOOGLE.copy_spreadsheet(
                spreadsheet_id,
                source_spreadsheet_id,
                target_spreadsheet_id)

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=  Copy Spreadsheet   ${SPREADSHEET_ID}  ${ANOTHER_SPREADSHEET_ID}
        """
        body = {
            "destination_spreadsheet_id": target_spreadsheet_id,
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

    @keyword(tags=["sheets"])
    def get_spreadsheet_basic_information(self, spreadsheet_id: str) -> List:
        """Get title, id, url and sheets information
        from the spreadsheet.

        :param spreadsheet_id: ID of the spreadsheet
        :return: operation result as an dictionary
        """
        result = self.get_spreadsheet_details(spreadsheet_id)
        sheet_info = [
            {
                "title": sheet["properties"]["title"],
                "id": sheet["properties"]["sheetId"],
                "rows": sheet["properties"]["gridProperties"]["rowCount"],
                "columns": sheet["properties"]["gridProperties"]["columnCount"],
            }
            for sheet in result["sheets"]
        ]
        return {
            "title": result["properties"]["title"],
            "id": result["spreadsheetId"],
            "url": result["spreadsheetUrl"],
            "sheets": sheet_info,
        }

    @keyword(tags=["sheets"])
    def get_spreadsheet_details(self, spreadsheet_id: str) -> Dict:
        """Returns spreadsheet information as a dictionary.

        :param spreadsheet_id: ID of the spreadsheet
        :return: operation result as an dictionary
        """
        return self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    @keyword(tags=["sheets"])
    def to_column_letter(self, number: int):
        """
        Convert a column number into a column letter(s).

        :param number: column number to convert
        :return: column letter(s)
        """
        if number < 1:
            raise ValueError("Number must be greater than 0")

        column_letter = ""
        while number > 0:
            remainder = (number - 1) % 26
            column_letter = chr(65 + remainder) + column_letter
            number = (number - 1) // 26
        return column_letter

    @keyword(tags=["sheets"])
    def copy_sheet(
        self,
        spreadsheet_id: str,
        source_sheet_name: str,
        new_sheet_name: str,
        insertSheetIndex: int = None,
    ):
        """Copy sheet into the spreadsheet as new sheet

        :param spreadsheet_id: id of the spreadsheet
        :param source_sheet_name: name of the source sheet
        :param new_sheet_name: name for the new sheet
        :param insertSheetIndex: zero based index where the new
         sheet should be inserted, defaults to None
        :return: operation result as an dictionary

        **Examples**

        **Python**

        .. code-block:: python

            result = GOOGLE.copy_sheet(
                spreadsheet_id,
                "Existing sheet",
                "Copy of existing sheet"
                )

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=    Copy Sheet
            ...   ${SPREADSHEET_ID}
            ...   Existing sheet
            ...   Copy of existing sheet
        """
        found_sheet = self.get_sheet_by_name(spreadsheet_id, source_sheet_name)

        body = {
            "requests": {
                "duplicateSheet": {
                    "sheetId": found_sheet["id"],
                    "title": new_sheet_name,
                }
            }
        }
        if insertSheetIndex:
            body["requests"]["duplicateSheet"]["insertSheetIndex"] = insertSheetIndex

        return self.generic_spreadsheet_batch_update(spreadsheet_id, body)

    @keyword(tags=["sheets"])
    def create_sheet(self, spreadsheet_id: str, sheet_name: str):
        """Create sheet into the spreadsheet

        :param spreadsheet_id: id of the spreadsheet
        :param sheet_name: name for the new sheet
        :return: operation result as an dictionary

        **Examples**

        **Python**

        .. code-block:: python

            result = GOOGLE.create_sheet(spreadsheet_id, "New sheet")

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=    Create Sheet    ${SPREADSHEET_ID}    New sheet
        """
        body = {"requests": {"addSheet": {"properties": {"title": sheet_name}}}}
        return self.generic_spreadsheet_batch_update(spreadsheet_id, body)

    @keyword(tags=["sheets"])
    def rename_sheet(self, spreadsheet_id: str, sheet_name: str, new_sheet_name: str):
        """Rename sheet in the spreadsheet

        :param spreadsheet_id: id of the spreadsheet
        :param sheet_name: existing name of the sheet
        :param new_sheet_name: name for the new sheet
        :return: operation result as an dictionary

        **Examples**

        **Python**

        .. code-block:: python

            result = GOOGLE.rename_sheet(spreadsheet_id, "Sheet1", "New name")

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=    Rename Sheet    ${SPREADSHEET_ID}    Sheet1   New name
        """
        found_sheet = self.get_sheet_by_name(spreadsheet_id, sheet_name)

        body = {
            "requests": {
                "updateSheetProperties": {
                    "fields": "title",
                    "properties": {
                        "sheetId": found_sheet["id"],
                        "title": new_sheet_name,
                    },
                }
            }
        }
        return self.generic_spreadsheet_batch_update(spreadsheet_id, body)

    @keyword(tags=["sheets"])
    def delete_sheet(self, spreadsheet_id: str, sheet_name: str):
        """Delete a sheet from the spreadsheet.

        :param spreadsheet_id: id of the spreadsheet
        :param sheet_name: name of the sheet to delete
        :return: operation result as an dictionary

        **Examples**

        **Python**

        .. code-block:: python

            result = GOOGLE.delete_sheet(spreadsheet_id, "Sheet1")

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=    Delete Sheet    ${SPREADSHEET_ID}    Sheet1
        """
        found_sheet = self.get_sheet_by_name(spreadsheet_id, sheet_name)

        body = {"requests": {"deleteSheet": {"sheetId": found_sheet["id"]}}}
        return self.generic_spreadsheet_batch_update(spreadsheet_id, body)

    def get_sheet_by_name(self, spreadsheet_id: str, sheet_name: str):
        sheet_info = self.get_spreadsheet_basic_information(spreadsheet_id)

        sheet_match = list(
            filter(lambda sheet: sheet["title"] == sheet_name, sheet_info["sheets"])
        )
        if len(sheet_match) != 1:
            raise KeyError(f"Sheet '{sheet_name}' not found")
        return sheet_match[0]

    @keyword(tags=["sheets"])
    def generic_spreadsheet_batch_update(self, spreadsheet_id: str, body: Dict):
        """This keyword allows to do generic batch update to the spreadsheet.

        For more information on the batch update:
        https://googleapis.github.io/google-api-python-client/docs/dyn/sheets_v4.spreadsheets.html#create

        List of possible requests actions (body can contain multiple at the same time):

            - addBanding
            - addChart
            - addConditionalFormatRule
            - addDataSource
            - addDimensionGroup
            - addFilterView
            - addNamedRange
            - addProtectedRange
            - addSheet (keyword ``Create sheet``)
            - addSlicer
            - appendCells
            - appendDimension
            - autoFill
            - autoResizeDimensions
            - clearBasicFilter
            - copyPaste
            - createDeveloperMetadata
            - cutPaste
            - deleteBanding
            - deleteConditionalFormatRule
            - deleteDataSource
            - deleteDeveloperMetadata
            - deleteDimension
            - deleteDimensionGroup
            - deleteDuplicates
            - deleteEmbeddedObject
            - deleteFilterView
            - deleteNamedRange
            - deleteProtectedRange
            - deleteRange
            - deleteSheet (keyword ``Delete sheet``)
            - duplicateFilterView
            - duplicateSheet (keyword ``Copy sheet``)
            - findReplace
            - insertDimension
            - insertRange
            - mergeCells
            - moveDimension
            - pasteData
            - randomizeRange
            - refreshDataSource
            - repeatCell
            - setBasicFilter
            - setDataValidation
            - sortRange
            - textToColumns
            - trimWhitespace
            - unmergeCells
            - updateBanding
            - updateBorders
            - updateCells
            - updateChartSpec
            - updateConditionalFormatRule
            - updateDataSource
            - updateDeveloperMetadata
            - updateDimensionGroup
            - updateDimensionProperties
            - updateEmbeddedObjectBorder
            - updateEmbeddedObjectPosition
            - updateFilterView
            - updateNamedRange
            - updateProtectedRange
            - updateSheetProperties (keyword ``Rename sheet``)
            - updateSlicerSpec
            - updateSpreadsheetProperties

        :param spreadsheet_id: id of the spreadsheet
        :param body: body of the batch update request
        :return: operation result as an dictionary

        **Examples**

        **Python**

        .. code-block:: python

            body = {"requests": {"deleteSheet": {"sheetId": "333555666"}}}
            result = GOOGLE.generic_spreadsheet_batch_update(spreadsheet_id, body)

        **Robot Framework**

        .. code-block:: robotframework

            ${body}=    Evaluate    {"requests": {"deleteSheet": {"sheetId": "333555666"}}}
            ${result}=    Generic Spreadsheet Batch Update    ${SPREADSHEET_ID}    ${body}
        """  # noqa: E501
        return (
            self.service.spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body,
            )
            .execute()
        )
