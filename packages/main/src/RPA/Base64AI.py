import base64
import json
import logging
import mimetypes
from typing import List, Optional, Union, Dict

import requests

from RPA.RobotLogListener import RobotLogListener


class Base64AI:
    """Library to support `Base64.ai <https://base64.ai/>`_ service for intelligent
    document processing (IDP).

    Service supports identifying fields in the documents, which can be given to the
    service in multiple different file formats and via URL.

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

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://base64.ai/api"
        self._request_headers = {"Content-Type": "application/json"}
        listener = RobotLogListener()
        listener.register_protected_keywords(
            ["RPA.Base64AI.set_base64ai_authorization"]
        )

    def _get_file_base64_and_mimetype(self, file_path: str):
        with open(file_path, "rb") as image_file:
            encoded_content = base64.b64encode(image_file.read())
        return encoded_content.decode("utf-8"), mimetypes.guess_type(file_path)[0]

    def set_base64ai_authorization(self, api_email: str, api_key: str) -> None:
        """Set Base64 AI request headers with email and key related to API.

        :param api_email: email address related to the API
        :param api_key: key related to the API
        """
        self._request_headers["Authorization"] = f"ApiKey {api_email}:{api_key}"

    def scan_document_file(
        self,
        file_path: str,
        model_types: Optional[Union[str, List[str]]] = None,
        mock: bool = False,
    ) -> Dict:
        """Scan a document file. Can be given a ``model_types`` to
        specifically target certain models.

        :param file_path: filepath to the file
        :param model_types: single model type or list of model types
        :param mock: set to True to use /mock/scan endpoint instead of /scan
        :return: result of the document scan
        """
        scan = "mock/scan" if "mock" in mock else "scan"
        scan_endpoint = f"{self.base_url}/{scan}"
        self.logger.info(f"endpoint {scan_endpoint} is set for scanning")
        base64string, mime = self._get_file_base64_and_mimetype(file_path)
        payload = {"image": f"data:{mime};base64,{base64string}"}
        if model_types:
            req_model_types = (
                model_types if isinstance(model_types, list) else model_types.split(",")
            )
            payload["modelTypes"] = req_model_types

        response = requests.request(
            "POST",
            scan_endpoint,
            headers=self._request_headers,
            data=json.dumps(payload),
        )
        response.raise_for_status()
        return response.json()

    def scan_document_url(
        self,
        url: str,
        model_types: Optional[Union[str, List[str]]] = None,
        mock: bool = False,
    ) -> Dict:
        """Scan a document URL. Can be given a ``model_types`` to
        specifically target certain models.

        :param url: valid url to a file
        :param model_types: single model type or list of model types
        :param mock: set to True to use /mock/scan endpoint instead of /scan
        :return: result of the document scan
        """
        scan = "mock/scan" if "mock" in mock else "scan"
        scan_endpoint = f"{self.base_url}/{scan}"
        self.logger.info(f"endpoint {scan_endpoint} is set for scanning")
        payload = {"url": url}
        if model_types:
            req_model_types = (
                model_types if isinstance(model_types, list) else model_types.split(",")
            )
            payload["modelTypes"] = req_model_types

        response = requests.request(
            "POST",
            scan_endpoint,
            headers=self._request_headers,
            data=json.dumps(payload),
        )
        response.raise_for_status()
        self.logger.warning(response.text)
        return response.json()

    def get_document_model_fields_and_text(self, document: List) -> List:
        """Helper keyword to get model, fields and text for a scan a result.

        :param document: scan result object
        :return: results in a list
        """
        response = []
        for dt in document:
            response.append(
                {key: dt[key] for key in dt.keys() & {"model", "fields", "ocr"}}
            )
        return response

    def get_user_data(self) -> Dict:
        """Get user data including details on credits used and credits remaining
        for the Base64 service.

        :return: object containing details on the API user
        """
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
