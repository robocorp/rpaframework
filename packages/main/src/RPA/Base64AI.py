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

    Added on **rpaframework** version: 17.0.1

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
            Set Authorization  ${secrets}[email-address]   ${secrets}[apikey]
            ${results}=  Scan Document File
            ...   ${CURDIR}${/}invoice.pdf
            ...   model_types=finance/check/usa,finance/invoice/usa
            # Scan response contains list of detected models in the document
            FOR  ${result}  IN  @{results}
                Log To Console  Model: ${result}[model]
                Log To Console  Field keys: ${{','.join($result['fields'].keys())}}
                Log To Console  Fields: ${result}[fields]
                Log To Console  Text (OCR): ${result}[ocr]
            END


    **Python example usage**

    .. code-block:: python

        from RPA.Base64AI import Base64AI
        from RPA.Robocorp.Vault import Vault

        secrets = Vault().get_secret("base64ai-auth")
        baselib = Base64AI()
        baselib.set_authorization(secrets["email-address"], secrets["apikey"])
        result = baselib.scan_document_file(
            "invoice.pdf",
            model_types="finance/invoice,finance/check/usa",
        )
        for r in result:
            print(f"Model: {r['model']}")
            for key, props in r["fields"].items():
                print(f"FIELD {key}: {props['value']}")
            print(f"Text (OCR): {r['ocr']}")
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://base64.ai/api"
        self._request_headers = {"Content-Type": "application/json"}
        listener = RobotLogListener()
        listener.register_protected_keywords(["RPA.Base64AI.set_authorization"])

    def _get_file_base64_and_mimetype(self, file_path: str):
        with open(file_path, "rb") as image_file:
            encoded_content = base64.b64encode(image_file.read())
        return encoded_content.decode("utf-8"), mimetypes.guess_type(file_path)[0]

    def set_authorization(self, api_email: str, api_key: str) -> None:
        """Set Base64 AI request headers with email and key related to API.

        :param api_email: email address related to the API
        :param api_key: key related to the API

        Robot Framework example:

        .. code-block:: robotframework

            ${secrets}=   Get Secret  base64ai-auth
            Set Authorization    ${secrets}[email-address]    ${secrets}[apikey]

        Python example:

        .. code-block:: python

            secrets = Vault().get_secret("base64ai-auth")
            baselib = Base64AI()
            baselib.set_authorization(secrets["email-address"], secrets["apikey"])
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

        Robot Framework example:

        .. code-block:: robotframework

            ${results}=    Scan Document File
            ...    ${CURDIR}${/}files${/}IMG_8277.jpeg
            ...    model_types=finance/check/usa,finance/invoice
            FOR    ${result}    IN    @{results}
                Log To Console    Model: ${result}[model]
                Log To Console    Fields: ${result}[fields]
                Log To Console    Text (OCR): ${result}[ocr]
            END

        Python example:

        .. code-block:: python

            result = baselib.scan_document_file(
                "./files/Invoice-1120.pdf",
                model_types="finance/invoice,finance/check/usa",
            )
            for r in result:
                print(f"Model: {r['model']}")
                for key, val in r["fields"].items():
                    print(f"{key}: {val['value']}")
                print(f"Text (OCR): {r['ocr']}")
        """
        scan = "mock/scan" if mock else "scan"
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

        Robot Framework example:

        .. code-block:: robotframework

            ${results}=    Scan Document URL
            ...    https://base64.ai/static/content/features/data-extraction/models//2.png
            FOR    ${result}    IN    @{results}
                Log To Console    Model: ${result}[model]
                Log To Console    Fields: ${result}[fields]
                Log To Console    Text (OCR): ${result}[ocr]
            END

        Python example:

        .. code-block:: python

            result = baselib.scan_document_url(
                "https://base64.ai/static/content/features/data-extraction/models//2.png"
            )
            for r in result:
                print(f"Model: {r['model']}")
                for key, props in r["fields"].items():
                    print(f"FIELD {key}: {props['value']}")
                print(f"Text (OCR): {r['ocr']}")
        """  # noqa: E501
        scan = "mock/scan" if mock else "scan"
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

    def get_user_data(self) -> Dict:
        """Get user data including details on credits used and credits remaining
        for the Base64 service.

        Returned user data contains following keys:

            - givenName
            - familyName
            - email
            - hasWorkEmail
            - companyName
            - numberOfCredits
            - numberOfPages
            - numberOfUploads
            - numberOfCreditsSpentOnDocuments (visible if used)
            - numberOfCreditsSpentOnFaceDetection (visible if used)
            - numberOfCreditsSpentOnFaceRecognition (visible if used)
            - hasActiveAwsContract
            - subscriptionType
            - subscriptionPeriod
            - tags
            - ccEmails
            - status
            - remainingCredits (calculated by the keyword)

        :return: object containing details on the API user

        Robot Framework example:

        .. code-block:: robotframework

            ${userdata}=   Get User Data
            Log To Console  I have still ${userdata}[remainingCredits] credits left

        Python example:

        .. code-block:: python

            userdata = baselib.get_user_data()
            print(f"I have still {userdata['remainingCredits']} credits left")
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
