import json
import logging
import os
import requests
import time

DEFAULT_REGION = "northeurope"


class AzureBase:
    """Base class for all Azure servives.

    `TOKEN_LIFESPAN` is in seconds, token is valid for 10 minutes so max lifetime
    is set to 9.5 minutes = 570.0 seconds
    """

    COGNITIVE_API = "api.cognitive.microsoft.com"
    TOKEN_LIFESPAN = 570.0
    services = {}
    token = None
    token_time = None

    def __init__(self, region="northeurope"):
        self.region = region
        self.services = {}
        self.token_time = None
        self.token = None

    def _azure_request(
        self,
        service_name,
        url,
        method: str = "POST",
        token: str = None,
        params=None,
        content_type="application/json",
        filepath=None,
        jsondata=None,
        headers=None,
        body=None,
    ):
        if headers:
            request_parameters = {"headers": headers}
        else:
            request_parameters = {"headers": {}}
            if token:
                request_parameters["headers"]["Authorization"] = f"Bearer {token}"
            else:
                if (
                    service_name not in self.services
                    or self.services[service_name] is None
                ):
                    raise KeyError(
                        "Missing subscription key for service: %s" % service_name
                    )
                request_parameters["headers"][
                    "Ocp-Apim-Subscription-Key"
                ] = self.services[service_name]

            request_parameters["headers"]["Content-Type"] = content_type
        if filepath:
            with open(filepath, "rb") as f:
                filedata = f.read()
            request_parameters["data"] = filedata
        if jsondata:
            request_parameters["json"] = jsondata
        if params:
            request_parameters["params"] = params
        if body:
            request_parameters["data"] = body
        self.logger.debug("Azure %s: %s" % (method, url))
        self.logger.debug(
            "Content-Type: %s" % request_parameters["headers"]["Content-Type"]
        )
        if method == "POST":
            response = requests.post(url, **request_parameters)
        elif method == "GET":
            response = requests.get(url, **request_parameters)
        else:
            raise KeyError("Unknown Azure request type: %s" % method)

        status_code = response.status_code
        self.logger.debug("Azure request response status: %s", status_code)
        assert (
            status_code == 200
        ), f"Azure responded with status: {status_code} '{response.reason}'"
        return response

    def _write_json(self, json_filepath, response_json):
        if json_filepath and response_json:
            with open(json_filepath, "w") as f:
                json.dump(response_json, f)

    def _set_subscription_key(self, service_name):
        sub_key = os.getenv(f"AZURE_{service_name.upper()}_KEY")
        self.services[service_name] = sub_key

    def _get_token(self, service_name, region):
        current_time = time.time()
        token_age = (current_time - self.token_time) if self.token_time else None
        if self.token is None or token_age is None or token_age > self.TOKEN_LIFESPAN:
            self.token = self._request_new_token(service_name, region)
            self.token_time = current_time
        return self.token

    def _request_new_token(self, service_name: str, region: str = None):
        self.logger.debug("Requesting new Azure token for accessing services")
        request_region = region if region else self.region
        self.__base_url = f"https://{request_region}.{self.COGNITIVE_API}"
        token_url = f"{self.__base_url}/sts/v1.0/issueToken"
        response = self._azure_request(service_name, token_url)
        return str(response.text)

    def _handle_response(self, json_filepath: None, response: None):
        response_json = response.json()
        self._write_json(json_filepath, response_json)
        return response_json


class ServiceTextAnalytics(AzureBase):
    """Class for Azure TextAnalytics service"""

    # TODO documents format explained or only single text string
    __service_name = "textanalytics"

    def __init__(self) -> None:
        self.logger.debug("ServiceTextAnalytics init")

    def init_textanalytics_service(self, region: str = None):
        """Initialize Azure Text Analyticts

        :param region: [description], defaults to None
        """
        self.__region = region if region else self.region
        self.__base_url = f"https://{self.__region}.{self.COGNITIVE_API}"
        self._set_subscription_key(self.__service_name)

    def sentiment_analyze(self, documents, json_file=None):
        """Analyze sentiments in the given text

        :param documents: [description]
        :param json_file: filepath to write results into
        :return: sentiment analysis in json format
        """
        analyze_url = f"{self.__base_url}/text/analytics/v3.0/sentiment"
        response = self._azure_request(
            self.__service_name, analyze_url, jsondata=documents
        )
        return self._handle_response(json_file, response)

    def detect_language(self, documents, json_file=None):
        """Detect languages in the given text

        :param documents: [description]
        :param json_file: filepath to write results into
        :return: language analysis in json format
        """
        analyze_url = f"{self.__base_url}/text/analytics/v3.0/languages"
        response = self._azure_request(
            self.__service_name, analyze_url, jsondata=documents
        )
        return self._handle_response(json_file, response)

    def key_phrases(self, documents, json_file=None):
        """Detect key phrases in the given text

        :param documents: [description]
        :param json_file: filepath to write results into
        :return: key phrases in json format
        """
        analyze_url = f"{self.__base_url}/text/analytics/v3.0/keyphrases"
        response = self._azure_request(
            self.__service_name, analyze_url, jsondata=documents
        )
        return self._handle_response(json_file, response)

    def find_entities(self, documents, json_file=None):
        """Detect entities in the given text

        :param documents: [description]
        :param json_file: filepath to write results into
        :return: entities in json format
        """
        analyze_url = f"{self.__base_url}/text/analytics/v2.1/entities"
        response = self._azure_request(
            self.__service_name, analyze_url, jsondata=documents
        )
        return self._handle_response(json_file, response)


class ServiceFace(AzureBase):
    """Class for Azure Face service"""

    __service_name = "face"

    def __init__(self) -> None:
        self.logger.debug("ServiceFace init")

    def init_face_service(self, region: str = None):
        """Initialize Azure Face

        :param region: [description], defaults to None
        """
        self.__region = region if region else self.region
        self.__base_url = f"https://{self.__region}.{self.COGNITIVE_API}"
        self._set_subscription_key(self.__service_name)

    def detect_face(self, image_file: str, json_file: str = None):
        """Detect facial attributes in the image

        # TODO. handle different FaceAttributes, RecognitionModels
        :param image_file: [description]
        :param json_file: filepath to write results into
        :return: [description]
        """
        analyze_url = f"{self.__base_url}/face/v1.0/detect"
        params = {
            "returnFaceId": "true",
            "returnFaceLandmarks": "false",
            "returnFaceAttributes": "age,gender,smile,facialHair,glasses,emotion,hair",
            "recognitionModel": "recognition_01",
            "returnRecognitionModel": "false",
        }
        content_type = "application/octet-stream"
        response = self._azure_request(
            self.__service_name,
            analyze_url,
            params=params,
            filepath=image_file,
            content_type=content_type,
        )
        return self._handle_response(json_file, response)


class ServiceComputerVision(AzureBase):
    """Class for Azure Computer Vision service"""

    __service_name = "computervision"

    def __init__(self) -> None:
        self.logger.debug("ServiceComputerVision init")

    def init_computervision_service(self, region: str = None):
        """Initialize Azure Computer Vision

        :param region: [description], defaults to None
        """
        self.__region = region if region else self.region
        self.__base_url = f"https://{self.__region}.{self.COGNITIVE_API}"
        self._set_subscription_key(self.__service_name)

    def vision_analyze(self, image_file: str, json_file: str = None):
        """Identify features in the image

        :param image_file: [description]
        :param json_file: filepath to write results into
        :return: [description]
        """
        analyze_url = f"{self.__base_url}/vision/v3.0/analyze"
        params = {"visualFeatures": "Categories,Description,Color"}
        content_type = "application/octet-stream"
        response = self._azure_request(
            self.__service_name,
            analyze_url,
            params=params,
            filepath=image_file,
            content_type=content_type,
        )
        return self._handle_response(json_file, response)

    def vision_describe(self, image_file: str, json_file: str = None):
        """Describe image with terms

        :param image_file: [description]
        :param json_file: [description], defaults to None
        :return: [description]
        """
        analyze_url = f"{self.__base_url}/vision/v3.0/describe"
        params = {"maxCandidates": "3", "language": "en"}
        response = self._azure_request(
            self.__service_name, analyze_url, params=params, filepath=image_file
        )
        response_json = response.json()
        self._write_json(json_file, response_json)
        return response_json

    def vision_read(self, image_file: str, json_file: str = None):
        """[summary]

        :param image_file: [description]
        :param json_file: filepath to write results into
        :return: [description]
        """
        analyze_url = f"{self.__base_url}/vision/v3.0/ocr"
        params = {"detectOrientation": "true", "language": "en"}
        content_type = "application/octet-stream"
        response = self._azure_request(
            self.__service_name,
            analyze_url,
            params=params,
            filepath=image_file,
            content_type=content_type,
        )
        return self._handle_response(json_file, response)

    def vision_see(self, image_file: str, json_file: str = None):
        """Detect objects in the image

        :param image_file: [description]
        :param json_file: filepath to write results into
        :return: [description]
        """
        analyze_url = f"{self.__base_url}/vision/v3.0/detect"
        content_type = "application/octet-stream"
        response = self._azure_request(
            self.__service_name,
            analyze_url,
            filepath=image_file,
            content_type=content_type,
        )
        return self._handle_response(json_file, response)


class ServiceSpeech(AzureBase):
    """Class for Azure Speech service"""

    __service_name = "speech"

    def __init__(self) -> None:
        self.logger.debug("ServiceSpeech init")

    def init_speech_service(self, region: str = None):
        """Initialize Azure Speech

        :param region: [description], defaults to None
        :type region: str, optional
        """
        self.__region = region if region else self.region
        self.__base_url = f"https://{self.__region}.tts.speech.microsoft.com"
        self._set_subscription_key(self.__service_name)

    def text_to_speech(
        self,
        text,
        language="en-US",
        name="en-US-AriaRUS",
        gender="FEMALE",
        encoding="MP3",
        neural_voice_style=None,
        target_file="synthesized.mp3",
    ):
        """Synthesize speech synchronously

        Available encoding types:

            - audio-24khz-96kbitrate-mono-mp3

        :param text: input text to synthesize
        :param language: voice language, defaults to "en-US"
        :param name: voice name, defaults to "en-US-AriaRUS"
        :param gender: voice gender, defaults to "FEMALE"
        :param encoding: result encoding type, defaults to "MP3"
        :param target_file: save synthesized output to file,
            defaults to "synthesized.mp3"
        :return: synthesized output in bytes
        """

        token = self._get_token(self.__service_name, self.__region)
        headers = {
            "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
            "Content-Type": "application/ssml+xml",
            "Authorization": "Bearer " + token,
            "User-Agent": "RPA software robot",
        }
        voice_url = f"{self.__base_url}/cognitiveservices/v1"
        xml_ns = "xmlns='http://www.w3.org/2001/10/synthesis'"
        if neural_voice_style is None:
            request_body = f"""
            <speak version='1.0' xml:lang='en-US'>
                <voice xml:lang='{language}'
                    xml:gender='{gender.capitalize()}'
                    name='{name}'>
            {text}
            </voice></speak>
            """
        else:
            mstts_ns = "xmlns:mstts='https://www.w3.org/2001/mstts'"
            request_body = f"""
            <speak version="1.0" {xml_ns} {mstts_ns} xml:lang="en-US">
                <voice name="{name}">
                    <mstts:express-as style="{neural_voice_style}">
                    {text}
                    </mstts:express-as>
                </voice>
            </speak>"""

        response = self._azure_request(
            self.__service_name,
            voice_url,
            method="POST",
            token=token,
            headers=headers,
            body=request_body,
        )
        if target_file:
            with open(target_file, "wb") as f:
                f.write(response.content)
        return response.content

    def list_supported_voices(
        self, locale: str = None, neural_only: bool = False, json_file: str = None
    ):
        """List supported voices for Azure API Speech Services.

        Available voice selection might differ between regions.

        :param locale: list only voices specific to locale, by default return all voices
        :param json_file: filepath to write results into
        :return: voices in json
        """
        token = self._get_token(self.__service_name, self.__region)
        voice_url = f"{self.__base_url}/cognitiveservices/voices/list"
        response = self._azure_request(
            self.__service_name, voice_url, method="GET", token=token
        )
        # TODO filter by locale and neural
        return self._handle_response(json_file, response)


class Azure(ServiceTextAnalytics, ServiceFace, ServiceComputerVision, ServiceSpeech):
    """Library for interacting with Azure services

    Authentication to Azure API is handled by `service subcription key` which
    can set for all services using environment variable `AZURE_SUBSCRIPTION_KEY`.

    If there are service specific subscription keys, these can be set using
    environment variable `AZURE_SERVICENAME_KEY`. Replace `SERVICENAME` with service
    name.

    List of supported service names:

        - computervision (Azure `Computer Vision`_ API)
        - face (Azure `Face`_ API)
        - speech (Azure `Speech Services`_ API)
        - textanalytics (Azure `Text Analytics`_ API)

    .. _Computer Vision: https://docs.microsoft.com/en-us/azure/cognitive-services/computer-vision/
    .. _Face: https://docs.microsoft.com/en-us/azure/cognitive-services/face/
    .. _Speech Services: https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/
    .. _Text Analytics: https://docs.microsoft.com/en-us/azure/cognitive-services/text-analytics/
    """

    def __init__(self, region: str = DEFAULT_REGION):
        self.logger = logging.getLogger(__name__)
        ServiceTextAnalytics.__init__(self)
        ServiceFace.__init__(self)
        ServiceComputerVision.__init__(self)
        ServiceSpeech.__init__(self)
        self.region = region
        self.logger.info("Azure library initialized. Default region: %s" % self.region)
