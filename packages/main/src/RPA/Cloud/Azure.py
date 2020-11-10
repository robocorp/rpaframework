import json
import logging
import os
import time
from typing import Any
import requests

from RPA.Robocloud.Secrets import Secrets

DEFAULT_REGION = "northeurope"


class AzureBase:
    """Base class for all Azure servives.

    `TOKEN_LIFESPAN` is in seconds, token is valid for 10 minutes so max lifetime
    is set to 9.5 minutes = 570.0 seconds
    """

    __base_url: str = None
    __region: str = None
    COGNITIVE_API = "api.cognitive.microsoft.com"
    TOKEN_LIFESPAN = 570.0
    region = None
    robocloud_vault_name: str = None
    services: dict = {}
    token = None
    token_time = None
    logger = None

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
        self.logger.debug("Azure %s: %s", method, url)
        self.logger.debug(
            "Content-Type: %s", request_parameters["headers"]["Content-Type"]
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

    def _set_subscription_key(self, service_name, use_robocloud_vault):
        common_key = "AZURE_SUBSCRIPTION_KEY"
        service_key = f"AZURE_{service_name.upper()}_KEY"
        sub_key = None
        if use_robocloud_vault:
            vault = Secrets()
            vault_items = vault.get_secret(self.robocloud_vault_name)
            vault_items = {k.upper(): v for (k, v) in vault_items.items()}
            if service_key in vault_items and vault_items[service_key].strip() != "":
                sub_key = vault_items[service_key]
            elif common_key in vault_items and vault_items[common_key].strip() != "":
                sub_key = vault_items[common_key]
            if sub_key is None:
                raise KeyError(
                    "The 'robocloud_vault_name' is required to access "
                    "Robocloud Vault. Set them in library "
                    "init or with `set_robocloud_vault` keyword."
                )
        else:
            sub_key = os.getenv(service_key)
            if sub_key is None or sub_key.strip() == "":
                sub_key = os.getenv(common_key)
            if sub_key is None or sub_key.strip() == "":
                raise KeyError(
                    "Azure service key is required to use Azure Cloud "
                    "service: %s" % service_name
                )

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

    def _azure_request_image(
        self, service_name, request_url, image_url, image_file, params=None
    ):
        if image_url:
            return self._azure_request(
                service_name,
                request_url,
                params=params,
                jsondata={"url": image_url},
                content_type="application/json",
            )
        else:
            return self._azure_request(
                service_name,
                request_url,
                params=params,
                filepath=image_file,
                content_type="application/octet-stream",
            )

    def _image_url_or_image_file_is_required(
        self, image_url: str = None, image_file: str = None
    ):
        if image_url is None and image_file is None:
            raise KeyError("Parameter 'image_url' or 'image_file' must be given.")

    def set_robocloud_vault(self, vault_name):
        """Set Robocloud Vault name

        :param vault_name: Robocloud Vault name
        """
        if vault_name:
            self.robocloud_vault_name = vault_name


class ServiceTextAnalytics(AzureBase):
    """Class for Azure TextAnalytics service"""

    __service_name = "textanalytics"

    def __init__(self) -> None:
        self.logger.debug("ServiceTextAnalytics init")
        self.__region = None

    def init_text_analytics_service(
        self, region: str = None, use_robocloud_vault: bool = False
    ):
        """Initialize Azure Text Analyticts

        :param region: identifier for service region
        :param use_robocloud_vault: use secret stored into `Robocloud Vault`
        """
        self.__region = region if region else self.region
        self.__base_url = f"https://{self.__region}.{self.COGNITIVE_API}"
        self._set_subscription_key(self.__service_name, use_robocloud_vault)

    def sentiment_analyze(
        self, text: str, language: str = None, json_file: str = None
    ) -> dict:
        """Analyze sentiments in the given text

        :param text: A UTF-8 text string
        :param language: if input language is known
        :param json_file: filepath to write results into
        :return: analysis in json format
        """
        analyze_url = f"{self.__base_url}/text/analytics/v3.0/sentiment"

        document = {"id": "1", "text": text}
        if language:
            document["language"] = language
        response = self._azure_request(
            self.__service_name, analyze_url, jsondata={"documents": [document]}
        )
        return self._handle_response(json_file, response)

    def detect_language(self, text: str, json_file: str = None) -> dict:
        """Detect languages in the given text

        :param text: A UTF-8 text string
        :param json_file: filepath to write results into
        :return: analysis in json format
        """
        analyze_url = f"{self.__base_url}/text/analytics/v3.0/languages"
        document = {"id": "1", "text": text}
        response = self._azure_request(
            self.__service_name, analyze_url, jsondata={"documents": [document]}
        )
        return self._handle_response(json_file, response)

    def key_phrases(
        self, text: str, language: str = None, json_file: str = None
    ) -> dict:
        """Detect key phrases in the given text

        :param text: A UTF-8 text string
        :param language: if input language is known
        :param json_file: filepath to write results into
        :return: analysis in json format
        """
        analyze_url = f"{self.__base_url}/text/analytics/v3.0/keyphrases"
        document = {"id": "1", "text": text}
        if language:
            document["language"] = language
        response = self._azure_request(
            self.__service_name, analyze_url, jsondata={"documents": [document]}
        )
        return self._handle_response(json_file, response)

    def find_entities(self, text: str, language: str = None, json_file=None) -> dict:
        """Detect entities in the given text

        :param text: A UTF-8 text string
        :param language: if input language is known
        :param json_file: filepath to write results into
        :return: analysis in json format
        """
        analyze_url = f"{self.__base_url}/text/analytics/v2.1/entities"
        document = {"id": "1", "text": text}
        if language:
            document["language"] = language
        response = self._azure_request(
            self.__service_name, analyze_url, jsondata={"documents": [document]}
        )
        return self._handle_response(json_file, response)


class ServiceFace(AzureBase):
    """Class for Azure Face service"""

    __service_name = "face"

    def __init__(self) -> None:
        self.logger.debug("ServiceFace init")

    def init_face_service(
        self, region: str = None, use_robocloud_vault: bool = False
    ) -> None:
        """Initialize Azure Face

        :param region: identifier for service region
        :param use_robocloud_vault: use secret stored into `Robocloud Vault`
        """
        self.__region = region if region else self.region
        self.__base_url = f"https://{self.__region}.{self.COGNITIVE_API}"
        self._set_subscription_key(self.__service_name, use_robocloud_vault)

    def detect_face(
        self,
        image_file: str = None,
        image_url: str = None,
        face_attributes: str = None,
        face_landmarks: bool = False,
        recognition_model: str = "recognition_02",
        json_file: str = None,
    ) -> dict:
        # pylint: disable=C0301
        """Detect facial attributes in the image

        :param image_file: filepath of image file
        :param image_url: URI to image, if given will be used instead of `image_file`
        :param face_attributes: comma separated list of attributes,
            for example. "age,gender,smile"
        :param face_landmarks: return face landmarks of the detected faces
            or not. The default value is `False`
        :param recognition_model: model used by Azure to detech faces, options
            are "recognition_01" or "recognition_02", default is "recognition_02"
        :param json_file: filepath to write results into
        :return: analysis in json format

        Read more about `face_attributes` at `Face detection explained`_:

        - age
        - gender
        - smile
        - facialHair
        - headPose
        - glasses
        - emotion
        - hair
        - makeup
        - accessories
        - blur
        - exposure
        - nouse

        .. _Face detection explained: https://docs.microsoft.com/en-us/azure/cognitive-services/face/concepts/face-detection
        """  # noqa: E501
        self._image_url_or_image_file_is_required(image_url, image_file)
        analyze_url = f"{self.__base_url}/face/v1.0/detect"
        params = {
            "returnFaceId": "true",
            "returnFaceLandmarks": str(face_landmarks),
            "recognitionModel": recognition_model,
            "returnRecognitionModel": "false",
        }
        if face_attributes:
            params["returnFaceAttributes"] = face_attributes
        response = self._azure_request_image(
            self.__service_name, analyze_url, image_url, image_file, params
        )
        return self._handle_response(json_file, response)


class ServiceComputerVision(AzureBase):
    """Class for Azure Computer Vision service"""

    __service_name = "computervision"

    def __init__(self) -> None:
        self.logger.debug("ServiceComputerVision init")

    def init_computer_vision_service(
        self, region: str = None, use_robocloud_vault: bool = False
    ) -> None:
        """Initialize Azure Computer Vision

        :param region: identifier for service region
        :param use_robocloud_vault: use secret stored into `Robocloud Vault`
        """
        self.__region = region if region else self.region
        self.__base_url = f"https://{self.__region}.{self.COGNITIVE_API}"
        self._set_subscription_key(self.__service_name, use_robocloud_vault)

    def vision_analyze(
        self,
        image_file: str = None,
        image_url: str = None,
        visual_features: str = None,
        json_file: str = None,
    ) -> dict:
        # pylint: disable=C0301
        """Identify features in the image

        :param image_file: filepath of image file
        :param image_url: URI to image, if given will be used instead of `image_file`
        :param visual_features: comma separated list of features,
            for example. "Categories,Description,Color"
        :param json_file: filepath to write results into
        :return: analysis in json format

        See `Computer Vision API`_ for valid feature names and their explanations:

        - Adult
        - Brands
        - Categories
        - Color
        - Description
        - Faces
        - ImageType
        - Objects
        - Tags

        .. _Computer Vision API: https://westcentralus.dev.cognitive.microsoft.com/docs/services/computer-vision-v3-ga
        """  # noqa: E501
        self._image_url_or_image_file_is_required(image_url, image_file)
        analyze_url = f"{self.__base_url}/vision/v3.0/analyze"
        params = {}
        if visual_features:
            params["visualFeatures"] = visual_features
        response = self._azure_request_image(
            self.__service_name, analyze_url, image_url, image_file, params
        )
        return self._handle_response(json_file, response)

    def vision_describe(
        self, image_file: str = None, image_url: str = None, json_file: str = None
    ) -> dict:
        """Describe image with tags and captions

        :param image_file: filepath of image file
        :param image_url: URI to image, if given will be used instead of `image_file`
        :param json_file: filepath to write results into
        :return: analysis in json format
        """
        self._image_url_or_image_file_is_required(image_url, image_file)
        analyze_url = f"{self.__base_url}/vision/v3.0/describe"
        params = {"maxCandidates": "3", "language": "en"}
        response = self._azure_request_image(
            self.__service_name, analyze_url, image_url, image_file, params
        )
        return self._handle_response(json_file, response)

    def vision_ocr(
        self, image_file: str = None, image_url: str = None, json_file: str = None
    ) -> dict:
        """Optical Character Recognition (OCR) detects text in an image

        :param image_file: filepath of image file
        :param image_url: URI to image, if given will be used instead of `image_file`
        :param json_file: filepath to write results into
        :return: analysis in json format
        """
        self._image_url_or_image_file_is_required(image_url, image_file)
        analyze_url = f"{self.__base_url}/vision/v3.0/ocr"
        params = {"detectOrientation": "true", "language": "en"}
        response = self._azure_request_image(
            self.__service_name, analyze_url, image_url, image_file, params
        )
        return self._handle_response(json_file, response)

    def vision_detect_objects(
        self, image_file: str = None, image_url: str = None, json_file: str = None
    ) -> dict:
        """Detect objects in the image

        :param image_file: filepath of image file
        :param image_url: URI to image, if given will be used instead of `image_file`
        :param json_file: filepath to write results into
        :return: analysis in json format
        """
        self._image_url_or_image_file_is_required(image_url, image_file)
        analyze_url = f"{self.__base_url}/vision/v3.0/detect"
        response = self._azure_request_image(
            self.__service_name, analyze_url, image_url, image_file
        )
        return self._handle_response(json_file, response)


class ServiceSpeech(AzureBase):
    """Class for Azure Speech service"""

    __service_name = "speech"
    audio_formats = {
        "MP3": "audio-24khz-96kbitrate-mono-mp3",
        "WAV": "riff-24khz-16bit-mono-pcm",
    }

    def __init__(self) -> None:
        self.logger.debug("ServiceSpeech init")

    def init_speech_service(
        self, region: str = None, use_robocloud_vault: bool = False
    ) -> None:
        """Initialize Azure Speech

        :param region: identifier for service region
        :param use_robocloud_vault: use secret stored into `Robocloud Vault`
        """
        self.__region = region if region else self.region
        self.__base_url = f"https://{self.__region}.tts.speech.microsoft.com"
        self._set_subscription_key(self.__service_name, use_robocloud_vault)

    def text_to_speech(
        self,
        text: str,
        language: str = "en-US",
        name: str = "en-US-AriaRUS",
        gender: str = "FEMALE",
        encoding: str = "MP3",
        neural_voice_style: Any = None,
        target_file: str = "synthesized.mp3",
    ):
        """Synthesize speech synchronously

        :param text: input text to synthesize
        :param language: voice language, defaults to "en-US"
        :param name: voice name, defaults to "en-US-AriaRUS"
        :param gender: voice gender, defaults to "FEMALE"
        :param encoding: result encoding type, defaults to "MP3"
        :param neural_voice_style: if given then neural voice is used,
            example style. "cheerful"
        :param target_file: save synthesized output to file,
            defaults to "synthesized.mp3"
        :return: synthesized output in bytes

        Neural voices are only supported for Speech resources created in
        East US, South East Asia, and West Europe regions.
        """
        encoding = encoding.upper() if encoding else None
        if encoding is None or encoding not in self.audio_formats.keys():
            raise KeyError(
                "Unknown encoding %s for text_to_speech, available formats are: %s"
                % (encoding, ", ".join(self.audio_formats.keys()))
            )
        token = self._get_token(self.__service_name, self.__region)
        headers = {
            "X-Microsoft-OutputFormat": self.audio_formats[encoding],
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

        :param locale: list only voices specific to locale, by default return all voices
        :param neural_only: `True` if only neural voices should be returned,
            `False` by default
        :param json_file: filepath to write results into
        :return: voices in json

        Available voice selection might differ between regions.
        """
        token = self._get_token(self.__service_name, self.__region)
        voice_url = f"{self.__base_url}/cognitiveservices/voices/list"
        response = self._azure_request(
            self.__service_name, voice_url, method="GET", token=token
        )
        response_json = response.json()
        if neural_only:
            response_json = [x for x in response_json if x["VoiceType"] == "Neural"]
        if locale:
            response_json = [x for x in response_json if locale in x["Locale"]]
        self._write_json(json_file, response_json)
        return response_json


class Azure(ServiceTextAnalytics, ServiceFace, ServiceComputerVision, ServiceSpeech):
    """`Azure` is a library for operating with Microsoft Azure API endpoints.

    List of supported service names:

    - computervision (`Azure Computer Vision API`_)
    - face (`Azure Face API`_)
    - speech (`Azure Speech Services API`_)
    - textanalytics (`Azure Text Analytics API`_)

    **Azure authentication**

    Authentication for Azure is set with `service subscription key` which can be given to the library
    in two different ways.

    - Method 1 as environment variables, either service specific environment variable
      for example ``AZURE_TEXTANALYTICS_KEY`` or with common key ``AZURE_SUBSCRIPTION_KEY`` which
      will be used for all the services.
    - Method 2 as Robocloud vault secret. The vault name needs to be given in library init or
      with keyword ``Set Robocloud Vault``. Secret keys are expected to match environment variable
      names.

    Method 1. subscription key using environment variable

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Azure

        *** Tasks ***
        Init Azure services
            # NO parameters for client, expecting to get subscription key
            # with AZURE_TEXTANALYTICS_KEY or AZURE_SUBSCRIPTION_KEY environment variable
            Init Text Analytics Service

    Method 2. setting Robocloud Vault in the library init

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Azure  robocloud_vault_name=azure

        *** Tasks ***
        Init Azure services
            Init Text Analytics Service  use_robocloud_vault=${TRUE}

    Method 2. setting Robocloud Vault with keyword

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Azure

        *** Tasks ***
        Init Azure services
            Set Robocloud Vault          vault_name=googlecloud
            Init Text Analytics Service  use_robocloud_vault=${TRUE}

    **References**

    List of supported language locales - `Azure locale list`_

    List of supported region identifiers - `Azure region list`_

    .. _Azure Computer Vision API: https://docs.microsoft.com/en-us/azure/cognitive-services/computer-vision/
    .. _Azure Face API: https://docs.microsoft.com/en-us/azure/cognitive-services/face/
    .. _Azure Speech Services API: https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/
    .. _Azure Text Analytics API: https://docs.microsoft.com/en-us/azure/cognitive-services/text-analytics/
    .. _Azure locale list: https://docs.microsoft.com/en-gb/azure/cognitive-services/speech-service/language-support#speech-to-text
    .. _Azure region list: https://docs.microsoft.com/en-gb/azure/cognitive-services/speech-service/regions#speech-to-text-text-to-speech-and-translation

    **Examples**

    **Robot Framework**

    This is a section which describes how to use the library in your
    Robot Framework tasks.

    .. code-block:: robotframework

       *** Settings ***
       Library  RPA.Cloud.Azure

       *** Variables ***
       ${IMAGE_URL}   IMAGE_URL
       ${FEATURES}    Faces,ImageType

       *** Tasks ***
       Visioning image information
          Init Computer Vision Service
          &{result}   Vision Analyze  image_url=${IMAGE_URL}  visual_features=${FEATURES}
          @{faces}    Set Variable  ${result}[faces]
          FOR  ${face}  IN   @{faces}
             Log  Age: ${face}[age], Gender: ${face}[gender], Rectangle: ${face}[faceRectangle]
          END

    **Python**

    This is a section which describes how to use the library in your
    own Python modules.

    .. code-block:: python

       library = Azure()
       library.init_text_analytics_service()
       library.init_face_service()
       library.init_computer_vision_service()
       library.init_speech_service("westeurope")

       response = library.sentiment_analyze(
          text="The rooms were wonderful and the staff was helpful."
       )
       response = library.detect_face(
          image_file=PATH_TO_FILE,
          face_attributes="age,gender,smile,hair,facialHair,emotion",
       )
       for item in response:
          gender = item["faceAttributes"]["gender"]
          age = item["faceAttributes"]["age"]
          print(f"Detected a face, gender:{gender}, age: {age}")

       response = library.vision_analyze(
          image_url=URL_TO_IMAGE,
          visual_features="Faces,ImageType",
       )
       meta = response['metadata']
       print(
          f"Image dimensions meta['width']}x{meta['height']} pixels"
       )

       for face in response["faces"]:
          left = face["faceRectangle"]["left"]
          top = face["faceRectangle"]["top"]
          width = face["faceRectangle"]["width"]
          height = face["faceRectangle"]["height"]
          print(f"Detected a face, gender:{face['gender']}, age: {face['age']}")
          print(f"\tFace rectangle: (left={left}, top={top})")
          print(f"\tFace rectangle: (width={width}, height={height})")

       library.text_to_speech(
           text="Developer tools for open-source RPA leveraging the Robot Framework ecosystem",
           neural_voice_style="cheerful",
           target_file='output.mp3'
       )
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self, region: str = DEFAULT_REGION, robocloud_vault_name: str = None):
        self.set_robocloud_vault(robocloud_vault_name)
        self.logger = logging.getLogger(__name__)
        ServiceTextAnalytics.__init__(self)
        ServiceFace.__init__(self)
        ServiceComputerVision.__init__(self)
        ServiceSpeech.__init__(self)
        self.region = region
        self.logger.info("Azure library initialized. Default region: %s", self.region)
