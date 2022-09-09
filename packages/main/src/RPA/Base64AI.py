import base64
import json
import logging
import mimetypes
import re
from typing import Any, List, Optional, Union

import requests

from RPA.RobotLogListener import RobotLogListener


class Base64AI:
    """Library to support `Base64.ai <https://base64.ai/>`_ service for intelligent document processing (IDP).

    Service supports identifying fields in the documents, which can be given to the service in multiple
    different file formats and via URL.

    **Robot Framework example usage**

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Base64AI
        Library   RPA.Robocorp.Vault

        *** Tasks ***
        Identify document
            ${secrets}=   Get Secret  base64ai-auth
            Set Base64AI Authorization  ${secrets}[email-address]   ${secrets}[apikey]
            ${results}=  Scan Document File
            ...   ${CURDIR}${/}invoice.pdf
            model_types=finance/check/usa,finance/invoice/usa
            # Scan response contains list of detected models in the document
            FOR  ${result}  IN  @{results}
                Log To Console  Model: ${result}[model]
                Log To Console  Field keys: ${{','.join($result['fields'].keys())}}
                Log To Console  Fields: ${result}[fields]
                Log To Console  Text (OCR): ${result}[ocr]
            END

    """

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        scan = "mock/scan" if "mock" in args else "scan"
        self.base_url = "https://base64.ai/api"
        self.scan_endpoint = f"{self.base_url}/{scan}"
        self.logger.info(f"endpoint {self.scan_endpoint} is set for scanning")
        self._request_headers = {"Content-Type": "application/json"}
        listener = RobotLogListener()
        listener.register_protected_keywords(["RPA.Base64AI.set_authorization"])

    def _get_file_base64_and_mimetype(self, file_path: str):
        with open(file_path, "rb") as image_file:
            encoded_content = base64.b64encode(image_file.read())
        return encoded_content.decode("utf-8"), mimetypes.guess_type(file_path)[0]

    def set_base64ai_authorization(self, api_email: str, api_key: str):
        """_summary_

        :param api_email: _description_
        :type api_email: str
        :param api_key: _description_
        :type api_key: str
        """
        self._request_headers["Authorization"] = f"ApiKey {api_email}:{api_key}"

    def scan_document_file(
        self, file_path: str, model_types: Optional[Union[str, List[str]]] = None
    ):
        """_summary_

        :param file_path: _description_
        :type file_path: str
        """
        base64string, mime = self._get_file_base64_and_mimetype(file_path)
        payload = {"image": f"data:{mime};base64,{base64string}"}
        if model_types:
            req_model_types = (
                model_types if isinstance(model_types, list) else model_types.split(",")
            )
            payload["modelTypes"] = req_model_types

        response = requests.request(
            "POST",
            self.scan_endpoint,
            headers=self._request_headers,
            data=json.dumps(payload),
        )
        response.raise_for_status()
        return response.json()

    def scan_document_url(self, url: str):
        """_summary_

        :param url: _description_
        :type url: str
        """
        payload = json.dumps({"url": url})
        response = requests.request(
            "POST", self.scan_endpoint, headers=self._request_headers, data=payload
        )
        response.raise_for_status()
        self.logger.warning(response.text)
        return response.json()

    def get_document_fields_and_text(self, document: List):
        """_summary_

        :param document: _description_
        :type document: Any
        """
        response = []
        for dt in document:
            response.append(
                {key: dt[key] for key in dt.keys() & {"model", "fields", "ocr"}}
            )
        return response

    def get_user_data(self):
        response = requests.request(
            "GET",
            f"{self.base_url}/auth/user",
            headers=self._request_headers,
        )
        response.raise_for_status()
        json_response = response.json()
        spent_on_documents = (
            json_response["numberOfCreditsSpentOnDocuments"]
            if "numberOfCreditsSpentOnDocuments" in json_response.keys()
            else 0
        )
        spent_on_face_detection = (
            json_response["numberOfCreditsSpentOnFaceDetection"]
            if "numberOfCreditsSpentOnFaceDetection" in json_response.keys()
            else 0
        )
        spent_on_face_recognition = (
            json_response["numberOfCreditsSpentOnFaceRecognition"]
            if "numberOfCreditsSpentOnFaceRecognition" in json_response.keys()
            else 0
        )
        remainingCredits = (
            json_response["numberOfCredits"]
            - spent_on_documents
            - spent_on_face_detection
            - spent_on_face_recognition
        )
        json_response["remainingCredits"] = remainingCredits
        return json_response
