import base64
import json
import logging
import mimetypes
import re
from typing import Any, List, Optional, Union

import requests

from RPA.RobotLogListener import RobotLogListener


class Nanonets:
    """Library to support `nanonets <https://nanonets.com/>`_ service for intelligent document processing (IDP).

    Service supports identifying fields in the documents, which can be given to the service in multiple
    different file formats and via URL.

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

    def __init__(self, *args, **kwargs):
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

    def set_nanonets_authorization(self, api_key: str):
        """_summary_

        :param api_key: _description_
        :type api_key: str
        """
        self.api_key = api_key

    def ocr_fulltext(self, filename: str, file_path: str):
        """_summary_

        :param file_path: _description_
        :type file_path: str
        """
        base64string, mime = self._get_file_base64_and_mimetype(file_path)

        # payload = {"urls": ["MY_IMAGE_URL"]}
        files = [("file", (filename, open(file_path, "rb"), mime))]

        headers = {}
        response = requests.request(
            "POST",
            f"{self.base_url}/OCR/FullText",
            headers=headers,
            # data=payload,
            files=files,
            auth=requests.auth.HTTPBasicAuth(self.api_key, ""),
        )

        response.raise_for_status()
        return response.json()["results"]

    def get_all_models(self):
        """_summary_

        :return: _description_
        :rtype: _type_
        """
        response = requests.request(
            "GET",
            f"{self.base_url}/ImageCategorization/Models/",
            auth=requests.auth.HTTPBasicAuth(self.api_key, ""),
        )

        response.raise_for_status()
        return response.json()
