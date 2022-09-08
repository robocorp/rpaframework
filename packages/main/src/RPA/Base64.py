import base64
import json
import logging
import mimetypes

import requests

from RPA.RobotLogListener import RobotLogListener


class Base64:
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        scan = "mock/scan" if "mock" in args else "scan"
        self.scan_endpoint = f"https://base64.ai/api/{scan}"
        self.logger.warning(f"using endpoint {self.scan_endpoint}")
        self._request_headers = {"Content-Type": "application/json"}
        listener = RobotLogListener()
        listener.register_protected_keywords(["RPA.Base64.set_authorization"])

    def get_file_base64_and_mimetype(self, file_path: str):
        with open(file_path, "rb") as image_file:
            encoded_content = base64.b64encode(image_file.read())
        return encoded_content.decode("utf-8"), mimetypes.guess_type(file_path)[0]

    def set_authorization(self, api_email: str, api_key: str):
        self._request_headers["Authorization"] = f"ApiKey {api_email}:{api_key}"

    def scan_document_file(self, file_path: str):
        base64string, mime = self.get_file_base64_and_mimetype(file_path)
        payload = json.dumps({"image": f"data:{mime};base64,{base64string}"})
        response = requests.request(
            "POST", self.scan_endpoint, headers=self._request_headers, data=payload
        )
        self.logger.warning(response.text)

    def scan_document_url(self, url: str):
        payload = json.dumps({"url": url})
        response = requests.request(
            "POST", self.scan_endpoint, headers=self._request_headers, data=payload
        )
        self.logger.warning(response.text)
