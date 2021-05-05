import importlib
import logging
import os
from robotlibcore import DynamicCore


from .keywords import (
    AppsScriptKeywords,
    BaseKeywords,
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


class Google(DynamicCore):
    """`Google` is a library for operating with Google API endpoints.

    Usage requires the following steps:

    - Create a GCP project
    - Create a service account key file (JSON) and save it to a place the robot
      can use it
    - Enable APIs
    - Install rpaframework-google package

    **Google authentication**

    Authentication for Google is set with `service account JSON file` which can be given to the library
    in three different ways or with `credentials.json`, which is used for OAuth authentication.

    Methods when using service credentials:

    - Method 1 as environment variables, ``GOOGLE_APPLICATION_CREDENTIALS`` with path to service account file.
    - Method 2 as keyword parameter to ``Init Storage Client`` for example.
    - Method 3 as Robocorp vault secret. The vault name and secret key name needs to be given in library init
      or with keyword ``Set Robocorp Vault``. Secret value should contain JSON file contents.

    Method 1. service credentials using environment variable

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Google

        *** Tasks ***
        Init Google services
            # NO parameters for Vision Client, expecting to get JSON
            # with GOOGLE_APPLICATION_CREDENTIALS environment variable
            Init Vision

    Method 2. service account with keyword parameter

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Google

        *** Tasks ***
        Init Google services
            Init Speech To Text   /path/to/service_account.json

    Method 3. setting Robocorp Vault in the library init

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Google
        ...       vault_name=googlecloud
        ...       vault_secret_key=servicecreds

        *** Tasks ***
        Init Google services
            Init Storage

    Method 3. setting Robocorp Vault with keyword

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Google

        *** Tasks ***
        Init Google services
            Set Robocorp Vault   vault_name=googlecloud  vault_secret_key=servicecreds
            Init Storage    use_robocorp_vault=${TRUE}

    Method when using OAuth credentials.json:

    The Google Apps Script and Google Drive services are authenticated using this method.

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.Google

        *** Variables ***
        @{SCRIPT_SCOPES}     forms   spreadsheets

        *** Tasks ***
        Init Google OAuth services
            Init Apps Script    /path/to/credentials.json   ${SCRIPT_SCOPES}

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
            Init Drive     use_robocorp_vault=True


    **Installation**

    ``pip install rpaframework-google``

    **Examples**

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
        service_account = '/path/to/service_account.json'

        library.init_vision(service_account)
        library.init_text_to_speech(service_account)

        response = library.detect_text('imagefile.png', 'result.json')
        library.synthesize_speech('I want this said aloud', target_file='said.mp3')
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
        try:
            secrets_library = importlib.import_module("RPA.Robocloud.Secrets")
            self.secrets_library = getattr(secrets_library, "Secrets")

        except ModuleNotFoundError:
            self.secrets_library = None
        # Register keyword libraries to LibCore
        libraries = [
            AppsScriptKeywords(self),
            BaseKeywords(self),
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
