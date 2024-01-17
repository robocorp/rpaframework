import importlib
import logging
import os
from robotlibcore import DynamicCore


from .keywords import (
    AppsScriptKeywords,
    BaseKeywords,
    DocumentAIKeywords,
    DriveKeywords,
    GmailKeywords,
    NaturalLanguageKeywords,
    SheetsKeywords,
    SpeechToTextKeywords,
    StorageKeywords,
    TextToSpeechKeywords,
    TranslationKeywords,
    VideoIntelligenceKeywords,
    VisionKeywords,
)


def import_vault():
    """Try to import Vault/Secrets library, with the new name."""
    try:
        module = importlib.import_module("RPA.Robocorp.Vault")
        return getattr(module, "Vault")
    except ModuleNotFoundError:
        return None


class Google(DynamicCore):
    """`Google` is a library for operating with Google API endpoints.

    **Installation**

    Usage requires the following steps:

    - Create a GCP project
    - Enable approriate APIs
    - Create credentials (OAuth or service account)
    - Install ``rpaframework-google`` package

    Check the latest package version from `PyPI`_.

    **Google authentication**

    Authentication for Google is set with `service account JSON file` which can be given to the library
    in three different ways or with `OAuth2 token`, which is used for OAuth authentication.

    See `library authentication examples`_ for more information.

    **Basic usage examples**

    **Python**

    .. code-block:: python

        from RPA.Cloud.Google import Google

        library = Google()
        service_account = '/path/to/service_account.json'

        library.init_vision(service_account)
        library.init_text_to_speech(service_account)

        response = library.detect_text('imagefile.png', 'result.json')
        library.synthesize_speech('I want this said aloud', target_file='said.mp3')

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Google

        *** Variables ***
        ${SERVICE_ACCOUNT}    ${/}path${/}to${/}service_account.json
        ${BUCKET_NAME}            testbucket12213123123

        *** Tasks ***
        Upload a file into a new storage bucket
            [Setup]   Init Storage    ${SERVICE_ACCOUNT}
            Create Storage Bucket    ${BUCKET_NAME}
            Upload Storage File      ${BUCKET_NAME}
            ...   ${/}path${/}to${/}file.pdf
            ...   myfile.pdf
            @{files}         List Storage Files   ${BUCKET_NAME}
            FOR   ${file}  IN   @{files}
                Log  ${file}
            END

    .. _PyPI: https://pypi.org/project/rpaframework-google/
    .. _library authentication examples: https://github.com/robocorp/rpaframework/blob/master/packages/google/docs/authentication.md
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(
        self,
        service_account: str = None,
        vault_name: str = None,
        vault_secret_key: str = None,
        cloud_auth_type: str = "serviceaccount",
    ):
        """Library initialization

        :param service_account: path to service account
        :param vault_name: Robocorp vault name
        :param vault_secret_key: Robocorp secret key
        :param cloud_auth_type: "serviceaccount" or "token",
         defaults to "serviceaccount"
        """
        self.logger = logging.getLogger(__name__)
        self.service_account_file = service_account
        self.robocorp_vault_name = vault_name
        self.robocorp_vault_secret_key = vault_secret_key
        self.cloud_auth_type = cloud_auth_type
        self.use_robocorp_vault = False
        if self.robocorp_vault_name and self.robocorp_vault_secret_key:
            self.use_robocorp_vault = True
        if self.service_account_file is None:
            self.service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.secrets_library = import_vault()

        # Register keyword libraries to LibCore
        libraries = [
            AppsScriptKeywords(self),
            BaseKeywords(self),
            DocumentAIKeywords(self),
            DriveKeywords(self),
            GmailKeywords(self),
            NaturalLanguageKeywords(self),
            SheetsKeywords(self),
            SpeechToTextKeywords(self),
            StorageKeywords(self),
            TextToSpeechKeywords(self),
            TranslationKeywords(self),
            VideoIntelligenceKeywords(self),
            VisionKeywords(self),
        ]
        super().__init__(libraries)
