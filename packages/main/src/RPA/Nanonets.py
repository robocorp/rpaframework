import base64
import logging
import mimetypes
from typing import Dict, Hashable, List, Optional, Union

import requests

from RPA.RobotLogListener import RobotLogListener

JSONValue = Optional[Union[str, int, float, bool]]
JSONType = Union[Dict[Hashable, JSONValue], List[JSONValue], JSONValue]


class Nanonets:
    """Library to support `nanonets <https://nanonets.com/>`_ service for intelligent
    document processing (IDP).

    Service supports identifying fields in the documents, which can be given to the
    service in multiple different file formats and via URL.

    **Robot Framework example usage**

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Nanonets
        Library   RPA.Robocorp.Vault

        *** Tasks ***
        Identify document
            ${secrets}=   Get Secret  nanonets-auth
            Set Nanonets Authorization  ${secrets}[apikey]
            ${results}=  OCR Fulltext
            ...   invoice.pdf
            ...   ${CURDIR}${/}invoice.pdf
            FOR  ${result}  IN  @{results}
                Log To Console  Filename: ${result}[filename]
                FOR  ${pagenum}  ${page}  IN ENUMERATE  @{result.pagedata}   start=1
                    Log To Console  Page ${pagenum} raw Text: ${page}[raw_text]
                END
            END

    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://app.nanonets.com/api/v2"
        self._request_headers = {"Content-Type": "application/json"}
        self.api_key = None
        listener = RobotLogListener()
        listener.register_protected_keywords(
            ["RPA.Nanonets.set_nanonets_authorization"]
        )

    def _get_file_base64_and_mimetype(self, file_path: str):
        with open(file_path, "rb") as image_file:
            encoded_content = base64.b64encode(image_file.read())
        return encoded_content.decode("utf-8"), mimetypes.guess_type(file_path)[0]

    def set_nanonets_authorization(self, api_key: str) -> None:
        """Set Nanonets request headers with key related to API.

        :param api_key: key related to the API
        """
        self.api_key = api_key

    def ocr_fulltext(self, filename: str, file_path: str) -> List:
        """OCR fulltext a given file. Returns words and full text.

        Filename and file_path needs to be given separately.

        :param filename: name of the file
        :param file_path: path of the file
        :return: the result in a list format
        """
        _, mime = self._get_file_base64_and_mimetype(file_path)

        # pylint: disable=R1732
        files = [("file", (filename, open(file_path, "rb"), mime))]

        headers = {}
        response = requests.request(
            "POST",
            f"{self.base_url}/OCR/FullText",
            headers=headers,
            files=files,
            auth=requests.auth.HTTPBasicAuth(self.api_key, ""),
        )

        response.raise_for_status()
        return response.json()["results"]

    def get_all_models(self) -> Dict:
        """Get all available models related to the API key.

        :return: object containing available models
        """
        response = requests.request(
            "GET",
            f"{self.base_url}/ImageCategorization/Models/",
            auth=requests.auth.HTTPBasicAuth(self.api_key, ""),
        )

        response.raise_for_status()
        return response.json()

    def predict_file(self, file_path: str, model_id: str) -> Dict:
        """Get prediction result for a file by a given model id.

        :param file_path: filepath to the file
        :param model_id: id of the Nanonets model to categorize a file
        :return: the result in a list format
        """

        url = f"{self.base_url}/OCR/Model/{model_id}/LabelFile/"

        # pylint: disable=R1732
        data = {"file": open(file_path, "rb")}

        response = requests.post(
            url, auth=requests.auth.HTTPBasicAuth(self.api_key, ""), files=data
        )

        response.raise_for_status()
        return response.json()

    def get_fields_from_prediction_result(self, prediction: JSONType) -> List:
        """Helper keyword to get found fields from a prediction result.

        :param prediction: prediction result file
        :return: list of found fields
        """
        return [
            item
            for item in prediction["result"][0]["prediction"]
            if "type" in item.keys() and item["type"] == "field"
        ]

    def get_tables_from_prediction_result(self, prediction: JSONType) -> List:
        """Helper keyword to get found tables from a prediction result.

        :param prediction: prediction result file
        :return: list of found tables
        """
        tables = [
            item
            for item in prediction["result"][0]["prediction"]
            if "type" in item.keys() and item["type"] == "table"
        ]
        # arrange cell items into list of lists
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
