import base64
import logging
import mimetypes
from typing import Dict, List

import requests

from RPA.JSON import JSONType
from RPA.RobotLogListener import RobotLogListener


class Nanonets:
    """Library to support `Nanonets <https://nanonets.com/>`_ service for intelligent document processing (IDP).

    Added with `rpaframework` version **19.0.0**.

    Service supports identifying fields in the documents, which can be given to the
    service in multiple different file formats and via URL.

    **Robot Framework example usage**

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.DocumentAI.Nanonets
        Library   RPA.Robocorp.Vault

        *** Tasks ***
        Identify document
            ${secrets}=   Get Secret  nanonets-auth
            Set Authorization    ${secrets}[apikey]
            ${result}=    Predict File
            ...  ${CURDIR}${/}files${/}eckero.jpg
            ...  ${secrets}[receipts-model-id]
            ${fields}=    Get Fields From Prediction Result    ${result}
            FOR    ${field}    IN    @{fields}
                Log To Console    Label:${field}[label] Text:${field}[ocr_text]
            END
            ${tables}=    Get Tables From Prediction Result    ${result}
            FOR    ${table}    IN    @{tables}
                FOR    ${rows}    IN    ${table}[rows]
                    FOR    ${row}    IN    @{rows}
                        ${cells}=    Evaluate    [cell['text'] for cell in $row]
                        Log To Console    ROW:${{" | ".join($cells)}}
                    END
                END
            END


    **Python example usage**

    .. code-block:: python

        from RPA.DocumentAI.Nanonets import Nanonets
        from RPA.Robocorp.Vault import Vault

        secrets = Vault().get_secret("nanonets-auth")
        nanolib = Nanonets()
        nanolib.set_authorization(secrets["apikey"])
        result = nanolib.predict_file(file_to_scan, secrets["receipts-model-id"])
        fields = nanolib.get_fields_from_prediction_result(result)
        for field in fields:
            print(f"Label: {field['label']} Text: {field['ocr_text']}")
        tables = nanolib.get_tables_from_prediction_result(result)
        for table in tables:
            rpatable = Tables().create_table(table["rows"])
            for row in table["rows"]:
                cells = [cell["text"] for cell in row]
                print(f"ROW: {' | '.join(cells)}")
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://app.nanonets.com/api/v2"
        self._request_headers = {"Content-Type": "application/json"}
        self.apikey = None
        listener = RobotLogListener()
        listener.register_protected_keywords(
            ["RPA.DocumentAI.Nanonets.set_authorization"]
        )

    def _get_file_base64_and_mimetype(self, file_path: str):
        with open(file_path, "rb") as image_file:
            encoded_content = base64.b64encode(image_file.read())
        return encoded_content.decode("utf-8"), mimetypes.guess_type(file_path)[0]

    def set_authorization(self, apikey: str) -> None:
        """Set Nanonets request headers with key related to API.

        :param apikey: key related to the API

        Robot Framework example:

        .. code-block:: robotframework

            ${secrets}=   Get Secret  nanonets-auth
            Set Authorization    ${secrets}[apikey]

        Python example:

        .. code-block:: python

            secrets = Vault().get_secret("nanonets-auth")
            nanolib = Nanonets()
            nanolib.set_authorization(secrets["apikey"])
        """
        self.apikey = apikey

    def ocr_fulltext(self, filename: str, filepath: str) -> List:
        """OCR fulltext a given file. Returns words and full text.

        Filename and filepath needs to be given separately.

        :param filename: name of the file
        :param filepath: path of the file
        :return: the result in a list format

        Robot Framework example:

        .. code-block:: robotframework

            ${results}=  OCR Fulltext
            ...   invoice.pdf
            ...   ${CURDIR}${/}invoice.pdf
            FOR  ${result}  IN  @{results}
                Log To Console  Filename: ${result}[filename]
                FOR  ${pagenum}  ${page}  IN ENUMERATE  @{result.pagedata}   start=1
                    Log To Console  Page ${pagenum} raw Text: ${page}[raw_text]
                END
            END

        Python example:

        .. code-block:: python

            results = nanolib.ocr_fulltext("IMG_8277.jpeg", "./IMG_8277.jpeg")
            for result in results:
                print(f"FILENAME: {result['filename']}")
                for page in result["page_data"]:
                    print(f"Page {page['page']+1}: {page['raw_text']}")
        """
        _, mime = self._get_file_base64_and_mimetype(filepath)

        # pylint: disable=R1732
        files = [("file", (filename, open(filepath, "rb"), mime))]

        response = requests.request(
            "POST",
            f"{self.base_url}/OCR/FullText",
            files=files,
            auth=requests.auth.HTTPBasicAuth(self.apikey, ""),
        )

        response.raise_for_status()
        return response.json()["results"]

    def get_all_models(self) -> Dict:
        """Get all available models related to the API key.

        :return: object containing available models

        Robot Framework example:

        .. code-block:: robotframework

            ${models}=  Get All Models
            FOR  ${model}  IN  @{models}
                Log To Console  Model ID: ${model}[model_id]
                Log To Console  Model Type: ${model}[model_type]
            END

        Python example:

        .. code-block:: python

            models = nanolib.get_all_models()
            for model in models:
                print(f"model id: {model['model_id']}")
                print(f"model type: {model['model_type']}")
        """
        response = requests.request(
            "GET",
            f"{self.base_url}/ImageCategorization/Models/",
            auth=requests.auth.HTTPBasicAuth(self.apikey, ""),
        )

        response.raise_for_status()
        return response.json()

    def predict_file(self, filepath: str, model_id: str) -> JSONType:
        """Get prediction result for a file by a given model id.

        :param filepath: filepath to the file
        :param model_id: id of the Nanonets model to categorize a file
        :return: the result in a list format

        Robot Framework example:

        .. code-block:: robotframework

            ${result}=  Predict File  ./document.pdf   ${MODEL_ID}
            ${fields}=    Get Fields From Prediction Result    ${result}
            FOR    ${field}    IN    @{fields}
                Log To Console    Label:${field}[label] Text:${field}[ocr_text]
            END
            ${tables}=    Get Tables From Prediction Result    ${result}
            FOR    ${table}    IN    @{tables}
                FOR    ${rows}    IN    ${table}[rows]
                    FOR    ${row}    IN    @{rows}
                        ${cells}=    Evaluate    [cell['text'] for cell in $row]
                        Log To Console    ROW:${{" | ".join($cells)}}
                    END
                END
            END

        Python example:

        .. code-block:: python

            result = nanolib.predict_file("./docu.pdf", secrets["receipts-model-id"])
            fields = nanolib.get_fields_from_prediction_result(result)
            for field in fields:
                print(f"Label: {field['label']} Text: {field['ocr_text']}")
            tables = nanolib.get_tables_from_prediction_result(result)
            for table in tables:
                for row in table["rows"]:
                    cells = [cell["text"] for cell in row]
                    print(f"ROW: {' | '.join(cells)}")
        """

        url = f"{self.base_url}/OCR/Model/{model_id}/LabelFile/"

        # pylint: disable=R1732
        data = {"file": open(filepath, "rb")}

        response = requests.post(
            url,
            headers={},
            auth=requests.auth.HTTPBasicAuth(self.apikey, ""),
            files=data,
        )

        response.raise_for_status()
        return response.json()

    def get_fields_from_prediction_result(self, prediction: JSONType) -> List:
        """Helper keyword to get found fields from a prediction result.

        For example. see ``Predict File`` keyword

        :param prediction: prediction result dictionary
        :return: list of found fields
        """
        return [
            item
            for item in prediction["result"][0]["prediction"]
            if "type" in item.keys() and item["type"] == "field"
        ]

    def get_tables_from_prediction_result(self, prediction: JSONType) -> List:
        """Helper keyword to get found tables from a prediction result.

        For another example. see ``Predict File`` keyword

        :param prediction: prediction result dictionary
        :return: list of found tables

        Robot Framework example:

        .. code-block:: robotframework

            # It is possible to create ``RPA.Tables`` compatible tables from the result
            ${tables}=    Get Tables From Prediction Result    ${result}
            FOR    ${table}    IN    @{tables}
                ${rpatable}=    Create Table    ${table}[rows]
                FOR    ${row}    IN    @{rpatable}
                    Log To Console    ${row}
                END
            END

        Python example:

        .. code-block:: python

            # It is possible to create ``RPA.Tables`` compatible tables from the result
            tables = nanolib.get_tables_from_prediction_result(result)
            for table in tables:
                rpatable = Tables().create_table(table["rows"])
                for row in rpatable:
                    print(row)
        """
        tables = [
            item
            for item in prediction["result"][0]["prediction"]
            if "type" in item.keys() and item["type"] == "table"
        ]
        for table in tables:
            table["rows"] = []
            row = []
            last_row = 1
            for cell in table["cells"]:
                if len(row) == 0 or last_row == cell["row"]:
                    row.append(cell)
                elif last_row != cell["row"]:
                    table["rows"].append(row)
                    row = [cell]
                last_row = cell["row"]
            if len(row) > 0:
                table["rows"].append(row)
        return tables
