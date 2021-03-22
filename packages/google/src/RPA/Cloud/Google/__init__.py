import logging
from robotlibcore import DynamicCore

from RPA.core.logger import RobotLogListener

from RPA.Cloud.Google.keywords import SheetsKeywords


class Google(DynamicCore):
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

    or as a separate package:

    ``pip install rpaframework-google``

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
        self.logger = logging.getLogger(__name__)
        self.robocloud_vault_name = robocloud_vault_name
        self.robocloud_vault_secret_key = robocloud_vault_secret_key

        # Register keyword libraries to LibCore
        libraries = [
            SheetsKeywords(self),
        ]
        super().__init__(libraries)

        # listener = RobotLogListener()
