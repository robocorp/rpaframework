import base64
from enum import Enum
from functools import wraps
from io import BytesIO
import json
import logging
import os
from pathlib import Path
import pickle
import shutil
import tempfile
import time
from typing import Any


try:
    from apiclient import discovery  # MediaIoBaseDownload
    from apiclient.errors import HttpError
    from apiclient.http import MediaFileUpload, MediaIoBaseDownload
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.cloud import vision
    from google.cloud import language_v1
    from google.cloud.language_v1 import enums
    from google.cloud import storage
    from google.cloud import videointelligence
    from google.cloud import translate_v3
    from google.cloud import texttospeech_v1
    from google.cloud.texttospeech_v1.types import (
        AudioConfig,
        VoiceSelectionParams,
        SynthesisInput,
    )
    from google.cloud import speech
    from google.oauth2 import service_account
    from google.protobuf.json_format import MessageToJson

    GOOGLECLOUD_IMPORT_ERROR = None
except ImportError as e:
    GOOGLECLOUD_IMPORT_ERROR = str(e)

from RPA.Robocloud.Secrets import Secrets


def google_dependency_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if GOOGLECLOUD_IMPORT_ERROR:
            raise ValueError(
                "Please install optional `google` package, "
                "`pip install rpaframework[google]` to use RPA.Cloud.Google library\n"
                + GOOGLECLOUD_IMPORT_ERROR
            )
        return f(*args, **kwargs)

    return wrapper


class GoogleOAuthAuthenticationError(Exception):
    """Raised when unable to get Google OAuth credentials."""


class GoogleDriveError(Exception):
    """Raised with errors in Drive API"""


class Update(Enum):
    """Possible file update actions."""

    trash = 1
    untrash = 2
    star = 3
    unstar = 4


def to_action(value):
    """Convert value to Update enum."""
    if isinstance(value, Update):
        return value

    sanitized = str(value).lower().strip().replace(" ", "_")
    try:
        return Update[sanitized]
    except KeyError as err:
        raise ValueError(f"Unknown file update action: {value}") from err


class GoogleBase:
    """Google base class for generic methods"""

    logger = None
    services: list = []
    clients: dict = {}
    region: str = None
    robocloud_vault_name: str = None
    robocloud_vault_secret_key: str = None
    global_scopes: list = []
    _scopes: list = []

    def _get_service(self, service_name: str = None):
        """Return client instance for servive if it has been initialized.

        :param service_name: name of the AWS service
        :return: client instance
        """
        if service_name not in self.clients.keys():
            raise KeyError(
                "Google service %s has not been initialized" % service_name.upper()
            )
        return self.clients[service_name]

    def _set_service(self, service_name: str = None, service: Any = None):
        self.clients[service_name] = service

    @google_dependency_required
    def _write_json(self, json_file, response):
        if json_file and response:
            with open(json_file, "w") as f:
                f.write(MessageToJson(response))

    def _get_service_account_from_robocloud(self):
        temp_filedesc = None
        if self.robocloud_vault_name is None or self.robocloud_vault_secret_key is None:
            raise KeyError(
                "Both 'robocloud_vault_name' and 'robocloud_vault_secret_key' "
                "are required to access Robocloud Vault. Set them in library "
                "init or with `set_robocloud_vault` keyword."
            )
        vault = Secrets()

        vault_items = vault.get_secret(self.robocloud_vault_name)
        secret = json.loads(vault_items[self.robocloud_vault_secret_key].strip())
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_filedesc:
            json.dump(secret, temp_filedesc, ensure_ascii=False)

        return temp_filedesc.name

    def _get_filecontent_from_robocloud(
        self, vault_name: str = None, secret_key: str = None
    ):
        vault_name = vault_name or self.robocloud_vault_name
        secret_key = secret_key or self.robocloud_vault_secret_key
        if vault_name is None or secret_key is None:
            raise KeyError(
                "Both 'robocloud_vault_name' and 'robocloud_vault_secret_key' "
                "are required to access Robocloud Vault. Set them in library "
                "init or with `set_robocloud_vault` keyword."
            )
        vault = Secrets()
        vault_items = vault.get_secret(vault_name)
        if isinstance(vault_items[secret_key], dict):
            return vault_items[secret_key]
        else:
            return vault_items[secret_key].strip()

    @google_dependency_required
    def _init_with_robocloud(self, client_object, service_name):
        temp_filedesc = self._get_service_account_from_robocloud()
        try:
            service = client_object.from_service_account_json(temp_filedesc)
            self._set_service(service_name, service)
        finally:
            if temp_filedesc:
                os.remove(temp_filedesc)

    def _init_service(
        self, client_object, service_name, service_credentials_file, use_robocloud_vault
    ):
        if use_robocloud_vault:
            self._init_with_robocloud(client_object, service_name)
        elif service_credentials_file:
            service = client_object.from_service_account_json(service_credentials_file)
            self._set_service(service_name, service)
        else:
            service = client_object()
            self._set_service(service_name, service)

    def set_robocloud_vault(self, vault_name: str = None, vault_secret_key: str = None):
        """Set Robocloud Vault name and secret key name

        :param vault_name: Robocloud Vault name
        :param vault_secret_key: Rococloud Vault secret key name
        """
        if vault_name:
            self.robocloud_vault_name = vault_name
        if vault_secret_key:
            self.robocloud_vault_secret_key = vault_secret_key

    def set_global_scopes(self, scopes: list = None):
        """Set global Google authentication scopes

        Useful when using numerous services with different scopes

        :param scopes: list of authentication scopes
        """
        if isinstance(scopes, list):
            self.global_scopes = scopes
        else:
            raise AttributeError("scopes needs to be a list")

    def _get_credentials_with_oauth_token(
        self, use_robocloud_vault, token_file, credentials_file, scopes, save_token
    ):
        credentials = None
        token_file_location = Path(token_file).absolute()
        if use_robocloud_vault:
            token = self._get_filecontent_from_robocloud(secret_key="oauth-token")
            credentials = pickle.loads(base64.b64decode(token))
        else:
            if os.path.exists(token_file_location):
                with open(token_file_location, "rb") as token:
                    credentials = pickle.loads(token)
        if scopes:
            self._scopes = self._scopes + [
                f"https://www.googleapis.com/auth/{scope}" for scope in scopes
            ]

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, self._scopes
                )
                credentials = flow.run_local_server()
            if save_token:
                with open(token_file_location, "wb") as token:
                    pickle.dump(credentials, token)
        if not credentials:
            raise GoogleOAuthAuthenticationError(
                "Could not get Google OAuth credentials"
            )
        return credentials


class ServiceVision(GoogleBase):
    """Class for Google Cloud Vision API

    Link to `Vision PyPI`_ page.

    .. _Vision PyPI: https://pypi.org/project/google-cloud-vision/
    """

    _service_name = "vision"

    def __init__(self) -> None:
        self.services.append(self._service_name)
        self.logger.debug("ServiceVision init")

    @google_dependency_required
    def init_vision_client(
        self,
        service_credentials_file: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Cloud Vision client

        :param service_credentials_file: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self._init_service(
            vision.ImageAnnotatorClient,
            self._service_name,
            service_credentials_file,
            use_robocloud_vault,
        )

    @google_dependency_required
    def _get_google_image(self, image_file):
        if not image_file:
            raise KeyError("image_file is required for parameter")
        with open(image_file, "rb") as f:
            content = f.read()
        return vision.types.Image(content=content)  # pylint: disable=E1101

    @google_dependency_required
    def detect_labels(self, image_file: str, json_file: str = None) -> dict:
        """Detect labels in the image

        :param image_file: source image file
        :param json_file: json target to save result, defaults to None
        :return: detection response
        """
        service = self._get_service(self._service_name)
        image = self._get_google_image(image_file)
        response = service.label_detection(image=image)
        self._write_json(json_file, response)
        return response

    @google_dependency_required
    def detect_text(self, image_file: str, json_file: str = None) -> dict:
        """Detect text in the image

        :param image_file: source image file
        :param json_file: json target to save result, defaults to None
        :return: detection response
        """
        service = self._get_service(self._service_name)
        image = self._get_google_image(image_file)
        response = service.text_detection(image=image)
        self._write_json(json_file, response)
        return response

    @google_dependency_required
    def detect_document(self, image_file: str, json_file: str = None) -> dict:
        """Detect document

        :param image_file: source image file
        :param json_file: json target to save result, defaults to None
        :return: detection response
        """
        service = self._get_service(self._service_name)
        image = self._get_google_image(image_file)
        response = service.document_text_detection(image=image)
        self._write_json(json_file, response)
        return response

    @google_dependency_required
    def annotate_image(self, image_uri: str, json_file: str = None) -> dict:
        """Annotate image

        :param image_file: source image file
        :param json_file: json target to save result, defaults to None
        :return: detection response
        """
        service = self._get_service(self._service_name)
        response = service.annotate_image(
            {"image": {"source": {"image_uri": image_uri}}}
        )
        self._write_json(json_file, response)
        return response

    @google_dependency_required
    def face_detection(self, image_uri: str, json_file: str = None) -> dict:
        """Detect faces

        :param image_uri: Google Cloud Storage URI
        :param json_file: json target to save result, defaults to None
        :return: detection response
        """
        service = self._get_service(self._service_name)
        response = service.face_detection({"source": {"image_uri": image_uri}})
        self._write_json(json_file, response)
        return response


class ServiceNaturalLanguage(GoogleBase):
    """Class for Google Cloud Natural Language API

    Link to `Natural Language PyPI`_ page.

    .. _Natural Language PyPI: https://pypi.org/project/google-cloud-language/
    """

    _service_name = "natural-language"

    def __init__(self) -> None:
        self.services.append(self._service_name)
        self.logger.debug("ServiceNaturalLanguage init")

    @google_dependency_required
    def init_natural_language_client(
        self, service_credentials_file: str = None, use_robocloud_vault: bool = False
    ) -> None:
        """Initialize Google Cloud Natural Language client

        :param service_credentials_file: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self._init_service(
            language_v1.LanguageServiceClient,
            self._service_name,
            service_credentials_file,
            use_robocloud_vault,
        )

    @google_dependency_required
    def analyze_sentiment(
        self, text_file: str, file_type: str = "text", json_file: str = None, lang=None
    ) -> dict:
        """Analyze sentiment in a text file

        :param text_file: source text file
        :param json_file: json target to save result, defaults to None
        :param lang: language code of the source, defaults to None
        :return: analysis response
        """
        service = self._get_service(self._service_name)
        with open(text_file, "r") as f:
            text_content = f.read()
        # Available types: PLAIN_TEXT, HTML
        if file_type == "text":
            type_ = enums.Document.Type.PLAIN_TEXT
        else:
            type_ = enums.Document.Type.HTML
        document = {"content": text_content, "type": type_}
        # Optional. If not specified, the language is automatically detected.
        # For list of supported languages:
        # https://cloud.google.com/natural-language/docs/languages
        if lang is not None:
            document["language"] = lang
        # Available values: NONE, UTF8, UTF16, UTF32
        encoding_type = enums.EncodingType.UTF8
        response = service.analyze_sentiment(document, encoding_type=encoding_type)
        self._write_json(json_file, response)
        return response

    @google_dependency_required
    def classify_text(self, text_file, json_file, lang=None):
        """Classify text

        :param text_file: source text file
        :param json_file: json target to save result, defaults to None
        :param lang: language code of the source, defaults to None
        :return: classify response
        """
        service = self._get_service(self._service_name)
        with open(text_file, "r") as f:
            text_content = f.read()
        # Available types: PLAIN_TEXT, HTML
        type_ = enums.Document.Type.PLAIN_TEXT
        document = {"content": text_content, "type": type_}
        # Optional. If not specified, the language is automatically detected.
        # For list of supported languages:
        # https://cloud.google.com/natural-language/docs/languages
        if lang is not None:
            document["language"] = lang
        response = service.classify_text(document)
        self._write_json(json_file, response)
        return response


class ServiceVideoIntelligence(GoogleBase):
    """Class for Google Cloud Video Intelligence API

    API supports only `Google Cloud Storages`_ URIs at the moment.

    Link to `Video Intelligence PyPI`_ page.

    .. _Video Intelligence PyPI: https://pypi.org/project/google-cloud-videointelligence
    .. _Google Cloud Storages: https://cloud.google.com/storage/
    """

    _service_name = "video-intelligence"

    def __init__(self) -> None:
        self.services.append(self._service_name)
        self.logger.debug("ServiceVideoIntelligence init")

    @google_dependency_required
    def init_video_intelligence_client(
        self,
        service_credentials_file: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Cloud Video Intelligence client

        :param service_credentials_file: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self._init_service(
            videointelligence.VideoIntelligenceServiceClient,
            self._service_name,
            service_credentials_file,
            use_robocloud_vault,
        )

    @google_dependency_required
    def annotate_video(
        self,
        video_uri: str = None,
        video_file: str = None,
        json_file: str = None,
        features: list = None,
    ):
        """Annotate video

        Possible values for features:

        - FEATURE_UNSPECIFIED, Unspecified.
        - LABEL_DETECTION, Label detection. Detect objects, such as dog or flower.
        - SHOT_CHANGE_DETECTION, Shot change detection.
        - EXPLICIT_CONTENT_DETECTION, Explicit content detection.
        - SPEECH_TRANSCRIPTION, Speech transcription.
        - TEXT_DETECTION, OCR text detection and tracking.
        - OBJECT_TRACKING, Object detection and tracking.
        - LOGO_RECOGNITION, Logo detection, tracking, and recognition.

        If `video_uri` is given then that is used even if `video_file` is None.

        :param video_uri: Google Cloud Storage URI
        :param video_file: filepath to video
        :param json_file: json target to save result, defaults to None
        :param features: list of annotation features to detect,
            defaults to ["LABEL_DETECTION", "SHOT_CHANGE_DETECTION"]
        :return: annotate result
        """
        service = self._get_service(self._service_name)
        response = None
        if features is None:
            features = ["LABEL_DETECTION", "SHOT_CHANGE_DETECTION"]
        if video_uri:
            response = service.annotate_video(
                input_uri=video_uri, features=features
            ).result()
        elif video_file:
            with open(video_file, "rb") as f:
                response = service.annotate_video(
                    input_content=f.read(), features=features
                ).result()
        self._write_json(json_file, response)
        return response


class ServiceTranslation(GoogleBase):
    """Class for Google Cloud Translation API

    Link to `Translation PyPI`_ page.

    .. _Translation PyPI: https://pypi.org/project/google-cloud-translate/
    """

    _service_name = "translation"

    def __init__(self) -> None:
        self.services.append(self._service_name)
        self.logger.debug("ServiceTranslation init")
        self._project_id = ""

    @google_dependency_required
    def init_translation_client(
        self,
        service_credentials_file: str = None,
        project_identifier: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Cloud Translation client

        :param service_credentials_file: filepath to credentials JSON
        :param project_identifier: identifier for Translation project
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self._init_service(
            translate_v3.TranslationServiceClient,
            self._service_name,
            service_credentials_file,
            use_robocloud_vault,
        )
        self._project_id = project_identifier

    @google_dependency_required
    def translate(
        self, text: Any, source_language: str = None, target_language: str = None
    ) -> dict:
        """Translate text

        :param text: text to translate
        :param source_language: language code, defaults to None
        :param target_language: language code, defaults to None
        :return: translated text
        """
        service = self._get_service(self._service_name)
        if not text and not target_language:
            raise KeyError("text and target_language are required parameters")
        parent = service.location_path(self._project_id, "global")
        if isinstance(text, str):
            text = [text]
        response = service.translate_text(
            contents=text,
            source_language_code=source_language,
            target_language_code=target_language,
            parent=parent,
        )
        return response


class ServiceTextToSpeech(GoogleBase):
    """Class for Google Cloud Text-to-Speech API

    Link to `Text To Speech PyPI`_ page.

    .. _Text To Speech PyPI: https://pypi.org/project/google-cloud-texttospeech/
    """

    _service_name = "text-to-speech"

    def __init__(self) -> None:
        self.services.append(self._service_name)
        self.logger.debug("ServiceTextToSpeech init")

    @google_dependency_required
    def init_text_to_speech_client(
        self, service_credentials_file: str = None, use_robocloud_vault: bool = False
    ) -> None:
        """Initialize Google Cloud Text to Speech client

        :param service_credentials_file: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self._init_service(
            texttospeech_v1.TextToSpeechClient,
            self._service_name,
            service_credentials_file,
            use_robocloud_vault,
        )

    @google_dependency_required
    def list_supported_voices(self, language_code: str = None):
        """List supported voices for the speech

        :param language_code: voice languages to list, defaults to None (all)
        :return: list of supported voices
        """
        service = self._get_service(self._service_name)
        if language_code:
            voices = service.list_voices(language_code)
        else:
            voices = service.list_voices()
        return voices.voices

    @google_dependency_required
    def synthesize_speech(
        self,
        text,
        language="en-US",
        name="en-US-Standard-B",
        gender="MALE",
        encoding="MP3",
        target_file="synthesized.mp3",
    ):
        """Synthesize speech synchronously

        :param text: input text to synthesize
        :param language: voice language, defaults to "en-US"
        :param name: voice name, defaults to "en-US-Standard-B"
        :param gender: voice gender, defaults to "MALE"
        :param encoding: result encoding type, defaults to "MP3"
        :param target_file: save synthesized output to file,
            defaults to "synthesized.mp3"
        :return: synthesized output in bytes
        """
        if not text:
            raise KeyError("text is required for kw: synthesize_speech")
        service = self._get_service(self._service_name)
        synth_input = SynthesisInput(text=text)
        voice_selection = VoiceSelectionParams(
            language_code=language, name=name, ssml_gender=gender
        )
        audio_config = AudioConfig(audio_encoding=encoding)
        response = service.synthesize_speech(synth_input, voice_selection, audio_config)
        if target_file:
            with open(target_file, "wb") as f:
                f.write(response.audio_content)
        return response.audio_content


class ServiceSpeechToText(GoogleBase):
    """Class for Google Cloud Speech-To-Text API

    Possible input audio encodings:

    - 'AMR'
    - 'AMR_WB'
    - 'ENCODING_UNSPECIFIED'
    - 'FLAC'
    - 'LINEAR16'
    - 'MULAW'
    - 'OGG_OPUS'
    - 'SPEEX_WITH_HEADER_BYTE'

    Link to `Speech To Text PyPI`_ page.

    .. _Speech To Text PyPI: https://pypi.org/project/google-cloud-speech/
    """

    _service_name = "speech-to-text"
    if not GOOGLECLOUD_IMPORT_ERROR:
        _encodings = {
            "AMR": speech.enums.RecognitionConfig.AudioEncoding.AMR,
            "AMR_WB": speech.enums.RecognitionConfig.AudioEncoding.AMR_WB,
            "FLAC": speech.enums.RecognitionConfig.AudioEncoding.FLAC,
            "LINEAR16": speech.enums.RecognitionConfig.AudioEncoding.LINEAR16,
            "MULAW": speech.enums.RecognitionConfig.AudioEncoding.MULAW,
            "OGG": speech.enums.RecognitionConfig.AudioEncoding.OGG_OPUS,
            "SPEEX": speech.enums.RecognitionConfig.AudioEncoding.SPEEX_WITH_HEADER_BYTE,  # noqa: E501 # pylint: disable=C0301
            "UNSPECIFIED": speech.enums.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,  # noqa: E501 # pylint: disable=C0301
        }
    else:
        _encodings = {}

    def __init__(self) -> None:
        self.services.append(self._service_name)
        self.logger.debug("ServiceSpeechToText init")

    @google_dependency_required
    def init_speech_to_text_client(
        self,
        service_credentials_file: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Cloud Speech to Text client

        :param service_credentials_file: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self._init_service(
            speech.SpeechClient,
            self._service_name,
            service_credentials_file,
            use_robocloud_vault,
        )

    @google_dependency_required
    def recognize(
        self,
        audio_file_uri,
        encoding: str = "FLAC",
        language_code: str = "en_US",
        audio_channel_count=2,
    ):
        """Recognize text in the audio file

        :param audio_file_uri: Google Cloud Storage URI
        :return: recognized texts
        """
        # flac or wav, does not require encoding type
        service = self._get_service(self._service_name)
        audio = speech.types.RecognitionAudio(  # pylint: disable=E1101
            uri=audio_file_uri
        )
        if encoding and encoding not in self._encodings:
            encoding = self._encodings["UNSPECIFIED"]
        config = speech.types.RecognitionConfig(  # pylint: disable=E1101
            encoding=encoding,
            language_code=language_code,
            audio_channel_count=audio_channel_count,
            use_enhanced=True,
        )
        rec = service.recognize(config=config, audio=audio)
        return rec.results


class ServiceStorage(GoogleBase):
    """Class for Google Cloud Storage API
     and Google Cloud Storage JSON API

    You will have to grant the appropriate permissions to the
    service account you are using to authenticate with
    @google-cloud/storage. The IAM page in the console is here:
    https://console.cloud.google.com/iam-admin/iam/project

    Link to `Google Storage PyPI`_ page.

    .. _Google Storage PyPI: https://pypi.org/project/google-cloud-storage/
    """

    _service_name = "storage"

    def __init__(self) -> None:
        self.services.append(self._service_name)
        self.logger.debug("ServiceStorage init")

    @google_dependency_required
    def init_storage_client(
        self,
        service_credentials_file: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Cloud Storage client

        :param service_credentials_file: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self._init_service(
            storage.Client,
            self._service_name,
            service_credentials_file,
            use_robocloud_vault,
        )

    @google_dependency_required
    def create_bucket(self, bucket_name: str):
        """Create Google Cloud Storage bucket

        :param bucket_name: name as string
        :return: bucket
        """
        service = self._get_service(self._service_name)
        bucket = service.create_bucket(bucket_name)
        return bucket

    @google_dependency_required
    def delete_bucket(self, bucket_name: str):
        """Delete Google Cloud Storage bucket

        Bucket needs to be empty before it can be deleted.

        :param bucket_name: name as string
        """
        bucket = self.get_bucket(bucket_name)
        try:
            bucket.delete()
        except Exception as e:
            raise ValueError("The bucket you tried to delete was not empty") from e

    @google_dependency_required
    def get_bucket(self, bucket_name: str):
        """Get Google Cloud Storage bucket

        :param bucket_name: name as string
        :return: bucket
        """
        if not bucket_name:
            raise KeyError("bucket_name is required for kw: get_bucket")
        service = self._get_service(self._service_name)
        bucket = service.get_bucket(bucket_name)
        return bucket

    @google_dependency_required
    def list_buckets(self) -> list:
        """List Google Cloud Storage buckets

        :return: list of buckets
        """
        service = self._get_service(self._service_name)
        buckets = list(service.list_buckets())
        return buckets

    @google_dependency_required
    def delete_files(self, bucket_name: str, files: Any):
        """Delete files in the bucket

        Files need to be object name in the bucket.

        :param bucket_name: name as string
        :param files: single file, list of files or
            comma separated list of files
        :return: list of files which could not be deleted,
            or True if all were deleted
        """
        if not bucket_name or not files:
            raise KeyError("bucket_name and files are required for kw: delete_files")
        if not isinstance(files, list):
            files = files.split(",")
        bucket = self.get_bucket(bucket_name)
        notfound = []
        for filename in files:
            filename = filename.strip()
            blob = bucket.get_blob(filename)
            if blob:
                blob.delete()
            else:
                notfound.append(filename)
        return notfound if len(notfound) > 0 else True

    @google_dependency_required
    def list_files(self, bucket_name: str):
        """List files in the bucket

        :param bucket_name: name as string
        :return: list of object names in the bucket
        """
        if not bucket_name:
            raise KeyError("bucket_name is required for kw: list_files")
        bucket = self.get_bucket(bucket_name)
        all_blobs = bucket.list_blobs()
        return sorted(blob.name for blob in all_blobs)

    @google_dependency_required
    def upload_file(self, bucket_name: str, filename: str, target_name: str):
        """Upload a file into a bucket

        :param bucket_name: name as string
        :param filename: filepath to upload file
        :param target_name: target object name
        """
        if not bucket_name or not filename or not target_name:
            raise KeyError(
                "bucket_name, filename and target_name are required for kw: upload_file"
            )
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(target_name)
        with open(filename, "rb") as f:
            blob.upload_from_file(f)

    @google_dependency_required
    def upload_files(self, bucket_name: str, files: dict):
        """Upload files into a bucket

        Example `files`:
        files = {"mytestimg": "image1.png", "mydoc": "google.pdf"}

        :param bucket_name: name as string
        :param files: dictionary of object names and filepaths
        """
        if not bucket_name or not files:
            raise KeyError("bucket_name and files are required for kw: upload_files")
        if not isinstance(files, dict):
            raise ValueError("files needs to be an dictionary")
        bucket = self.get_bucket(bucket_name)
        for target_name, filename in files.items():
            blob = bucket.blob(target_name)
            blob.upload_from_filename(filename)

    @google_dependency_required
    def download_files(self, bucket_name: str, files: Any):
        """Download files from a bucket

        Example `files`:
        files = {"mytestimg": "image1.png", "mydoc": "google.pdf

        :param bucket_name: name as string
        :param files: list of object names or dictionary of
            object names and target files
        :return: list of files which could not be downloaded, or
            True if all were downloaded
        """
        if isinstance(files, str):
            files = files.split(",")
        bucket = self.get_bucket(bucket_name)
        notfound = []
        if isinstance(files, dict):
            for object_name, filename in files.items():
                blob = bucket.get_blob(object_name)
                if blob:
                    with open(filename, "wb") as f:
                        blob.download_to_file(f)
                        self.logger.info(
                            "Downloaded object %s from Google to filepath %s",
                            object_name,
                            filename,
                        )
                else:
                    notfound.append(object_name)
        else:
            for filename in files:
                filename = filename.strip()
                blob = bucket.get_blob(filename)
                if blob:
                    with open(filename, "wb") as f:
                        blob.download_to_file(f)
                        self.logger.info(
                            "Downloaded object %s from Google to filepath %s",
                            filename,
                            filename,
                        )
                else:
                    notfound.append(filename)
        return notfound if len(notfound) > 0 else True


class ServiceSheets(GoogleBase):
    """Class for Google Sheets API

    You will have to grant the appropriate permissions to the
    service account you are using to authenticate with
    Google Sheets API. The IAM page in the console is here:
    https://console.cloud.google.com/iam-admin/iam/project

    For more information about Google Sheets API link_.

    .. _link: https://developers.google.com/sheets/api/quickstart/python
    """

    _service_name = "sheets"

    def __init__(self) -> None:
        self.services.append(self._service_name)

    @google_dependency_required
    def init_sheets_client(
        self,
        service_credentials_file: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize Google Sheets client

        :param service_credentials_file: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        self._scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        service_account_file = None
        service = None
        if use_robocloud_vault:
            service_account_file = self._get_service_account_from_robocloud()
        elif service_credentials_file:
            service_account_file = service_credentials_file
        try:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=self._scopes
            )
            service = discovery.build(
                "sheets", "v4", credentials=credentials, cache_discovery=False
            )
        except OSError as e:
            raise AssertionError from e
        finally:
            if use_robocloud_vault:
                os.remove(service_account_file)

        self._set_service(self._service_name, service)

    @google_dependency_required
    def create_sheet(self, title: str) -> str:
        """Create empty sheet with a title

        :param title: name as string
        :return: created `sheet_id`
        """
        if not title:
            raise KeyError("title is required for kw: create_sheet")

        service = self._get_service(self._service_name)
        data = {"properties": {"title": title}}
        spreadsheet = (
            service.spreadsheets().create(body=data, fields="spreadsheetId").execute()
        )
        return spreadsheet.get("spreadsheetId")

    @google_dependency_required
    def insert_values(
        self,
        sheet_id: str,
        sheet_range: str,
        values: list,
        major_dimension: str = "COLUMNS",
        value_input_option: str = "USER_ENTERED",
    ) -> None:
        """Insert values into sheet cells

        :param sheet_id: target sheet
        :param sheet_range: target sheet range
        :param values: list of values to insert into sheet
        :param major_dimension: major dimension of the values, default `COLUMNS`
        :param value_input_option: controls whether input strings are parsed or not,
                                   default `USER_ENTERED`
        """
        if not sheet_id or not sheet_range:
            raise KeyError(
                "sheet_id and sheet_range are required for kw: insert_values"
            )
        if not values:
            raise ValueError("Please provide list of values to insert into sheet")

        service = self._get_service(self._service_name)

        datavalues = []
        for val in values:
            datavalues.append([val])
        resource = {"majorDimension": major_dimension, "values": datavalues}
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=sheet_range,
            body=resource,
            valueInputOption=value_input_option,
        ).execute()

    def get_values(
        self,
        sheet_id: str,
        sheet_range: str,
        value_render_option: str = "UNFORMATTED_VALUE",
        datetime_render_option: str = "FORMATTED_STRING",
    ) -> list:
        """Get values from the range in the sheet

        :param sheet_id: target sheet
        :param sheet_range: target sheet range
        :param value_render_option: how values should be represented
                                    in the output defaults to "UNFORMATTED_VALUE"
        :param datetime_render_option: how dates, times, and durations should be
                                       represented in the output, defaults to "FORMATTED_STRING"
        """  # noqa: E501
        service = self._get_service(self._service_name)
        values = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=sheet_id,
                range=sheet_range,
                valueRenderOption=value_render_option,
                dateTimeRenderOption=datetime_render_option,
            )
            .execute()
        )
        return values

    def clear_values(self, sheet_id: str, sheet_range: str) -> None:
        """Clear cell values for range of cells within a sheet

        :param sheet_id: target sheet
        :param sheet_range: target sheet range
        """
        service = self._get_service(self._service_name)
        service.spreadsheets().values().clear(
            spreadsheetId=sheet_id,
            range=sheet_range,
        ).execute()


class ServiceAppsScript(GoogleBase):
    """Class for Google Apps Script API

    **Note:** The Apps Script API does not work with _service accounts_

    Following steps are needed to authenticate and use the service:

    1. enable Apps Script API in the Cloud Platform project (GCP)
    2. create OAuth credentials so API can be authorized (download ``credentials.json``
       which is needed to initialize service)
    3. the Google Script needs to be linked to Cloud Platform project number
    4. Google Script needs to have necessary OAuth scopes to access app
       which is being scripted
    5. necessary authentication scopes and credentials.json are needed
       to initialize service and run scripts

    For more information about Google Apps Script API link_.

    .. _link: https://developers.google.com/apps-script/api
    """

    _service_name = "apps_script"

    def __init__(self) -> None:
        self.services.append(self._service_name)

    @google_dependency_required
    def init_apps_script_client(
        self,
        credentials_file: str = "credentials.json",
        token_file: str = "oauth.token",
        use_robocloud_vault: bool = False,
        scopes: list = None,
        save_token: bool = False,
    ) -> None:
        """Initialize Google Apps Script client

        :param credentials_file: filepath to credentials JSON
        :param token_file: filepath to OAuth token file
        :param use_robocloud_vault: if `True` the token is read from Robocloud
        :param scopes: authenticated scopes, for example. ['forms', 'spreadsheets']
        :param save_token: set to `True` if token should be saved to local file
        """
        self._scopes = ["https://www.googleapis.com/auth/script.projects"]
        credentials = self._get_credentials_with_oauth_token(
            use_robocloud_vault, token_file, credentials_file, scopes, save_token
        )

        service = build("script", "v1", credentials=credentials, cache_discovery=False)
        self._set_service(self._service_name, service)

    def run_script(self, script_id: str, function_name: str, parameters: dict) -> None:
        """Run the Google Apps Script

        :param script_id: Google Script identifier
        :param function_name: name of the script function
        :param parameters: script function parameters as a dictionary
        :raises AssertionError: thrown when Google Script returns errors

        Example:

        .. code-block:: robotframework

            &{params}=    Create Dictionary  formid=aaad4232  formvalues=1,2,3
            ${response}=  Run Script    abc21397283712da  submit_form   ${params}
            Log Many   ${response}
        """
        request = {
            "function": function_name,
            "parameters": [parameters],
        }
        service = self._get_service(self._service_name)
        response = (
            service.scripts()
            .run(
                body=request,
                scriptId=script_id,
            )
            .execute()
        )
        if "error" in response.keys():
            raise AssertionError(response["error"])
        return response


class ServiceDrive(GoogleBase):
    """Class for Google Drive API

    **Note:** The Drive API does not work with _service accounts_

    Following steps are needed to authenticate and use the service:

    1. enable Drive API in the Cloud Platform project (GCP)
    2. create OAuth credentials so API can be authorized (download ``credentials.json``
       which is needed to initialize service)
    3. necessary authentication scopes and credentials.json are needed
       to initialize service

    For more information about Google Drive API link_.

    .. _link: https://developers.google.com/drive/api
    """

    _service_name = "drive"

    def __init__(self) -> None:
        self.services.append(self._service_name)

    @google_dependency_required
    def init_drive_client(
        self,
        credentials_file: str = "credentials.json",
        token_file: str = "oauth.token",
        use_robocloud_vault: bool = False,
        scopes: list = None,
        save_token: bool = False,
    ) -> None:
        """Initialize Google Drive client

        :param credentials_file: filepath to credentials JSON
        :param token_file: filepath to OAuth token file
        :param use_robocloud_vault: if `True` the token is read from Robocloud
        :param scopes: authenticated scopes, for example. ['forms', 'spreadsheets']
        :param save_token: set to `True` if token should be saved to local file
        """
        self._scopes = [
            "https://www.googleapis.com/auth/drive.appdata",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive.install",
        ]
        credentials = self._get_credentials_with_oauth_token(
            use_robocloud_vault, token_file, credentials_file, scopes, save_token
        )
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        self.logger.info(service)
        self._set_service(self._service_name, service)

    def drive_upload_file(
        self,
        filename: str = None,
        folder: str = None,
        overwrite: bool = False,
        make_dir: bool = False,
    ) -> dict:
        """Upload files into Drive

        :param filename: name of the file to upload
        :param folder: target folder for upload
        :param overwrite: set to `True` if already existing file should be overwritten
        :param make_dir: set to `True` if folder should be created if it does not exist
        :raises GoogleDriveError: if target_folder does not exist or
         trying to upload directory
        :return: uploaded file id

        Example:

        .. code-block:: robotframework

            ${file1_id}=  Drive Upload File   data.json  # Upload file to drive root
            ${file2_id}=  Drive Upload File   newdata.json  new_folder  make_dir=True
            ${file3_id}=  Drive Upload File   data.json  overwrite=True
        """
        service = self._get_service(self._service_name)

        folder_id = self.drive_get_folder_id(folder)
        if folder_id is None and make_dir:
            folder_id = self.drive_create_directory(folder)
        if folder_id is None:
            raise GoogleDriveError(
                "Target folder '%s' does not exist or could not be created" % folder
            )

        filepath = Path(filename)
        if filepath.is_dir():
            raise GoogleDriveError(
                "The '%s' is a directory and can not be uploaded" % filename
            )
        elif not filepath.is_file():
            raise GoogleDriveError("Filename '%s' does not exist" % filename)

        query_string = f"name = '{filename}' and '{folder_id}' in parents"
        target_file = self.drive_search_files(query=query_string, recurse=True)
        file_metadata = {
            "name": filepath.name,
            "parents": [folder_id],
            "mimeType": "*/*",
        }
        media = MediaFileUpload(filepath.absolute(), mimetype="*/*", resumable=True)
        if len(target_file) == 1 and overwrite:
            self.logger.info("Overwriting file '%s' with new content", filename)
            file = (
                service.files()
                .update(fileId=target_file[0]["id"], media_body=media, fields="id")
                .execute()
            )
            return file.get("id", None)
        elif len(target_file) == 1 and not overwrite:
            self.logger.info("Not uploading new copy of file '%s'", filename)
            return None
        elif len(target_file) > 1:
            self.logger.warning(
                "Drive already contains '%s' copies of file '%s'. Not uploading again."
                % (len(target_file), filename)
            )
            return None
        else:
            file = (
                service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            return file.get("id", None)

    def _download_with_fileobject(self, file_object):
        service = self._get_service(self._service_name)
        request = service.files().get_media(fileId=file_object["id"])
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            _, done = downloader.next_chunk()
        fh.seek(0)
        with open(file_object["name"], "wb") as f:
            # pylint: disable=protected-access
            shutil.copyfileobj(fh, f, length=downloader._total_size)

    def drive_download_files(
        self,
        file_dict: dict = None,
        query: str = None,
        limit: int = None,
        timeout: float = None,
    ):
        """Download files specified by file dictionary or query string

        Parameters `start`, `limit` and `timeout` are used only when
        downloading files defined by `query` parameter.

        :param file_dict: file dictionary returned by `Drive Search Files`
        :param query: drive query string to find target files, defaults to None
        :param start: start index from which to start download files
        :param limit: maximum amount of files that are downloaded, defaults to None
        :param timeout: maximum allowed time in seconds for download process
        :return: list of downloaded files

        Example:

        .. code-block:: robotframework

            ${files}=    Drive Search Files    query=name contains '.json'
            FOR    ${f}    IN    @{files}
                Run Keyword If  ${f}[size] < 2000  Drive Download Files  file_dict=${f}
            END

            ${folder_id}=   Drive Get Folder Id   datafolder
            Drive Download Files  query=name contains '.json' and '${folder_id}' in parents  recurse=True
        """  # noqa: E501
        if query:
            filelist = self.drive_search_files(query)
            files_downloaded = []
            start_time = time.time()

            for f in filelist:
                self._download_with_fileobject(f)
                current_time = time.time()
                files_downloaded.append(f["name"])
                if limit and len(files_downloaded) >= limit:
                    self.logger.info(
                        "Drive download limit %s reached. Stopping the download.", limit
                    )
                    break
                if timeout and (current_time - start_time) > float(timeout):
                    self.logger.info(
                        "Drive download timeout %s seconds reached. "
                        "Stopping the download.",
                        timeout,
                    )
                    break
            return files_downloaded

        if file_dict:
            self._download_with_fileobject(file_dict)
            return [file_dict]
        return None

    def drive_update_file(
        self,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        action: Update = Update.star,
        multiple_ok: bool = False,
    ):
        """Update file specified by id, file dictionary or query string

        Possible actions:
        - star
        - unstar
        - trash
        - untrash

        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Drive Search Files`
        :param query: drive query string to find target file, needs to match 1 file
        :param action: update action, default star file
        :param multiple_ok: set to `True` if it is ok to perform update
         on more than 1 file
        :return: number of updated files

        Example:

        .. code-block:: robotframework

            ${folder_id}=  Drive Get Folder Id   datafolder
            ${updated}=    Drive Update File   query=name contains '.json' and '${folder_id}' in parents
            ...            action=star
            ...            multiple_ok=True
        """  # noqa: E501
        target_files = self._get_target_file(file_id, file_dict, query, multiple_ok)
        action = to_action(action)
        update_count = 0
        for tf in target_files:
            self._drive_files_update(tf, action)
            update_count += 1
        return update_count

    def _get_target_file(self, file_id, file_dict, query, multiple_ok):
        target_files = []
        if file_id:
            target_files.append(file_id)
        elif file_dict:
            target_files.append(file_dict.get("id", None))
        else:
            files = self.drive_search_files(query, recurse=True)
            target_files = [tf.get("id", None) for tf in files]
            if not multiple_ok and len(target_files) > 1:
                raise GoogleDriveError(
                    "expected search to match 1 file, but it matched %s files"
                    % len(files)
                )

        return target_files

    def _drive_files_update(self, file_id: str, action: Update):
        service = self._get_service(self._service_name)
        body = None
        if action == Update.trash:
            body = {"trashed": True}
        elif action == Update.untrash:
            body = {"trashed": False}
        elif action == Update.star:
            body = {"starred": True}
        elif action == Update.unstar:
            body = {"starred": False}
        else:
            # TODO: mypy should handle enum exhaustivity validation
            raise ValueError(f"Unsupported update action: {action}")
        updated_file = service.files().update(fileId=file_id, body=body).execute()
        return updated_file

    def drive_delete_file(
        self,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        multiple_ok: bool = False,
    ):
        """Delete file specified by id, file dictionary or query string

        Note. Be extra careful when calling this keyword!

        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Drive Search Files`
        :param query: drive query string to find target file, needs to match 1 file
         unless parameter `multiple_ok` is set to `True`
        :param multiple_ok: set to `True` if it is ok to perform delete
         on more than 1 file
        :return: how many files where deleted

        Example:

        .. code-block:: robotframework

            ${folder_id}=  Drive Get Folder Id   datafolder
            ${deleted}=    Drive Delete File   query=name contains '.json' and '${folder_id}' in parents
            ...            multiple_ok=True
        """  # noqa: E501
        service = self._get_service(self._service_name)
        target_files = self._get_target_file(file_id, file_dict, query, multiple_ok)

        delete_count = 0
        for tf in target_files:
            service.files().delete(fileId=tf).execute()
            delete_count += 1
        return delete_count

    def drive_get_folder_id(self, folder: str = None):
        """Get file id for the folder

        :param folder: name of the folder to identify, by default returns drive's
         `root` folder id
        :return: file id of the folder

        Example:

        .. code-block:: robotframework

            ${root_id}=    Drive Get Folder Id   # returns Drive root folder id
            ${folder_id}=  Drive Get Folder Id  subdir
        """
        service = self._get_service(self._service_name)
        mime_folder_type = "application/vnd.google-apps.folder"
        folder_id = None
        if folder is None:
            file = service.files().get(fileId="root", fields="id").execute()
            folder_id = file.get("id", None)
        else:
            query_string = f"name = '{folder}' AND mimeType = '{mime_folder_type}'"
            folders = self.drive_search_files(query=query_string, recurse=True)
            if len(folders) == 1:
                folder_id = folders[0].get("id", None)
            else:
                self.logger.info(
                    "Found '%s' directories with name '%s'", (len(folders), folder)
                )
        return folder_id

    def drive_move_file(
        self,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        folder: str = None,
        folder_id: str = None,
        multiple_ok: bool = False,
    ):
        """Move file specified by id, file dictionary or query string into target folder

        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Drive Search Files`
        :param query: drive query string to find target file, needs to match 1 file
        :param folder: name of the folder to move file into, is by default drive's
         `root` folder id
        :param folder_id: id of the folder to move file into, if set the `folder`
         parameter is ignored
        :param multiple_ok: if `True` then moving more than 1 file
        :return: list of file ids
        :raises GoogleDriveError: if there are no files to move or
         target folder can't be found

        Example:

        .. code-block:: robotframework

            ${source_id}=  Drive Get Folder Id  sourcefolder
            ${query}=      Set Variable  name contains '.json' and '${sourceid}' in parents
            ${files}=      Drive Move File  query=${query}  folder=target_folder  multiple_ok=True
        """  # noqa: E501
        result_files = []
        service = self._get_service(self._service_name)
        target_files = self._get_target_file(file_id, file_dict, query, multiple_ok)
        if len(target_files) == 0:
            raise GoogleDriveError("Did not find any files to move")
        if folder_id:
            target_parent = folder_id
        else:
            target_parent = self.drive_get_folder_id(folder)
        if target_parent is None:
            raise GoogleDriveError(
                "Unable to find target folder: '%s'" % (folder if folder else "root")
            )
        for tf in target_files:
            file = service.files().get(fileId=tf, fields="parents").execute()
            previous_parents = ",".join(file.get("parents"))
            result_file = (
                service.files()
                .update(
                    fileId=tf,
                    addParents=target_parent,
                    removeParents=previous_parents,
                    fields="id, parents",
                )
                .execute()
            )
            result_files.append(result_file)
        return result_files

    def drive_search_files(
        self, query: str = None, recurse: bool = False, folder_name: str = None
    ) -> list:
        """Search Google Drive for files matching query string

        :param query: search string, defaults to None which means that all files
         and folders are returned
        :param recurse: set to `True` if search should recursive
        :param folder_name: search files in this directory
        :raises GoogleDriveError: if there is a request error
        :return: list of files

        Example:

        .. code-block:: robotframework

            ${files}=  Drive Search Files   query=name contains 'hello'
            ${files}=  Drive Search Files   query=modifiedTime > '2020-06-04T12:00:00'
            ${files}=  Drive Search Files   query=mimeType contains 'image/' or mimeType contains 'video/'
            ${files}=  Drive Search Files   query=name contains '.yaml'  recurse=True
            ${files}=  Drive Search Files   query=name contains '.yaml'  folder_name=datadirectory
        """  # noqa: E501
        service = self._get_service(self._service_name)
        page_token = None
        filelist = []
        parameters = {"fields": "nextPageToken, files", "spaces": "drive", "q": ""}
        query_string = [query] if query else []

        if not recurse:
            folder_id = (
                "root" if not folder_name else self.drive_get_folder_id(folder_name)
            )
            if folder_id is None:
                return []
            query_string.append(f"'{folder_id}' in parents")

        parameters["q"] = " and ".join(query_string)

        while True:
            parameters["pageToken"] = page_token
            try:
                response = service.files().list(**parameters).execute()
            except HttpError as e:
                raise GoogleDriveError(str(e)) from e
            for file in response.get("files", []):
                filesize = file.get("size")
                filelist.append(
                    {
                        "name": file.get("name"),
                        "id": file.get("id"),
                        "size": int(filesize) if filesize else None,
                        "kind": file.get("kind"),
                        "parents": file.get("parents"),
                        "starred": file.get("starred"),
                        "trashed": file.get("trashed"),
                        "shared": file.get("shared"),
                        "mimeType": file.get("mimeType"),
                        "spaces": file.get("spaces", None),
                        "exportLinks": file.get("exportLinks"),
                        "createdTime": file.get("createdTime"),
                        "modifiedTime": file.get("modifiedTime"),
                    }
                )
            page_token = response.get("nextPageToken", None)
            if page_token is None:
                break
        return filelist

    def drive_create_directory(self, folder: str = None):
        """Create new directory to Google Drive

        :param folder: name for the new directory
        :raises GoogleDriveError: if folder name is not given
        :return: created file id
        """
        if not folder or len(folder) == 0:
            raise GoogleDriveError("Can't create Drive directory with empty name")

        folder_id = self.drive_get_folder_id(folder)
        if folder_id:
            self.logger.info("Folder '%s' already exists. Not creating new one.")
            return None

        service = self._get_service(self._service_name)
        file_metadata = {
            "name": folder,
            "mimeType": "application/vnd.google-apps.folder",
        }

        added_folder = service.files().create(body=file_metadata, fields="id").execute()
        return added_folder

    def drive_export_file(
        self,
        file_id: str = None,
        file_dict: dict = None,
        target_file: str = None,
        mimetype: str = "application/pdf",
    ):
        """Export Google Drive file using Drive export links

        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Drive Search Files`
        :param target_file: name for the exported file
        :param mimetype: export mimetype, defaults to "application/pdf"

        Example:

        .. code-block:: robotframework

            ${files}=  Drive Search Files  query=name contains 'my example worksheet'
            Drive Export File  file_dict=${files}[0]
        """
        if target_file is None or len(target_file) == 0:
            raise AttributeError("The target_file is required parameter for export")
        if file_id is None and file_dict is None:
            raise AttributeError("Either file_id or file_dict is required for export")
        service = self._get_service(self._service_name)
        target_files = self._get_target_file(file_id, file_dict, None, False)
        if len(target_files) != 1:
            raise ValueError("Did not find the Google Drive file to export")
        request = service.files().export(fileId=target_files[0], mimeType=mimetype)

        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            _, done = downloader.next_chunk()

        fh.seek(0)
        filepath = Path(target_file).absolute()
        with open(filepath, "wb") as f:
            shutil.copyfileobj(fh, f, length=131072)


class Google(  # pylint: disable=R0901
    ServiceVision,
    ServiceNaturalLanguage,
    ServiceVideoIntelligence,
    ServiceTranslation,
    ServiceTextToSpeech,
    ServiceSpeechToText,
    ServiceStorage,
    ServiceSheets,
    ServiceAppsScript,
    ServiceDrive,
):
    """`Google` is a library for operating with Google API endpoints.

    Usage requires the following steps:

    - Create a GCP project
    - Create a service account key file (JSON) and save it to a place the robot
      can use it
    - Enable APIs
    - Install rpaframework[google]

    **Google authentication**

    Authentication for Google is set with `service credentials JSON file` which can be given to the library
    in three different ways or with `credentials.json`, which is used for OAuth authentication.

    Methods when using service credentials:

    - Method 1 as environment variables, ``GOOGLE_APPLICATION_CREDENTIALS`` with path to JSON file.
    - Method 2 as keyword parameter to ``Init Storage Client`` for example.
    - Method 3 as Robocloud vault secret. The vault name and secret key name needs to be given in library init
      or with keyword ``Set Robocloud Vault``. Secret value should contain JSON file contents.

    Method 1. service credentials using environment variable

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Google

        *** Tasks ***
        Init Google services
            # NO parameters for Vision Client, expecting to get JSON
            # with GOOGLE_APPLICATION_CREDENTIALS environment variable
            Init Vision Client

    Method 2. service credentials with keyword parameter

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Google

        *** Tasks ***
        Init Google services
            Init Speech To Text Client  /path/to/service_credentials.json

    Method 3. setting Robocloud Vault in the library init

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Google
        ...       robocloud_vault_name=googlecloud
        ...       robocloud_vault_secret_key=servicecreds

        *** Tasks ***
        Init Google services
            Init Storage Client   use_robocloud_vault=${TRUE}

    Method 3. setting Robocloud Vault with keyword

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Google

        *** Tasks ***
        Init Google services
            Set Robocloud Vault   vault_name=googlecloud  vault_secret_key=servicecreds
            Init Storage Client   use_robocloud_vault=${TRUE}

    Method when using OAuth credentials.json:

    The Google Apps Script and Google Drive services are authenticated using this method.

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Google

        *** Variables ***
        @{SCRIPT_SCOPES}     forms   spreadsheets

        *** Tasks ***
        Init Google OAuth services
            Init Apps Script Client   /path/to/credentials.json   ${SCRIPT_SCOPES}

    **Creating and using OAuth token file**

    The token file can be created using `credentials.json` by running command:

    ``rpa-google-oauth --service drive`` or
    ``rpa-google-oauth --scopes drive.appdata,drive.file,drive.install``

    This will start web based authentication process, which outputs the token at the end.
    Token could be stored into ``Robocorp Vault`` where it needs to be in variable ``google-oauth``.

    Example Vault content.

    .. code-block:: json

        "googlecloud": {
            "oauth-token": "gANfd123321aabeedYsc"
        }

    Using the Vault.

    .. code-block:: robotframework

        *** Keywords ***
        Set up Google Drive authentication
            Set Robocloud Vault    vault_name=googlecloud
            Init Drive Client    use_robocloud_vault=True


    **Requirements**

    Due to number of dependencies related to Google Cloud services this library has been set as
    an optional package for ``rpaframework``.

    This can be installed by opting in to the `google` dependency:

    ``pip install rpaframework[google]``

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Google

        *** Variables ***
        ${SERVICE CREDENTIALS}    ${/}path${/}to${/}service_credentials.json
        ${BUCKET_NAME}            testbucket12213123123

        *** Tasks ***
        Upload a file into a new storage bucket
            [Setup]   Init Storage Client   ${SERVICE CREDENTIALS}
            Create Bucket    ${BUCKET_NAME}
            Upload File      ${BUCKET_NAME}   ${/}path${/}to${/}file.pdf  myfile.pdf
            @{files}         List Files   ${BUCKET_NAME}
            FOR   ${file}  IN   @{files}
                Log  ${file}
            END

    **Python**

    .. code-block:: python

        from RPA.Cloud.Google import Google

        library = Google
        service_credentials = '/path/to/service_credentials.json'

        library.init_vision_client(service_credentials)
        library.init_text_to_speech(service_credentials)

        response = library.detect_text('imagefile.png', 'result.json')
        library.synthesize_speech('I want this said aloud', target_file='said.mp3')
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(
        self, robocloud_vault_name: str = None, robocloud_vault_secret_key: str = None
    ):
        self.set_robocloud_vault(robocloud_vault_name, robocloud_vault_secret_key)
        self.logger = logging.getLogger(__name__)
        ServiceVision.__init__(self)
        ServiceNaturalLanguage.__init__(self)
        ServiceVideoIntelligence.__init__(self)
        ServiceTranslation.__init__(self)
        ServiceTextToSpeech.__init__(self)
        ServiceSpeechToText.__init__(self)
        ServiceStorage.__init__(self)
        ServiceSheets.__init__(self)
        ServiceAppsScript.__init__(self)
        ServiceDrive.__init__(self)
        self.logger.info("Google library initialized")
