import base64
import logging
import importlib
from typing import Dict, Optional, Union
from pathlib import Path
from O365 import (
    Account,
    MSGraphProtocol,
    FileSystemTokenBackend,
    directory,
    drive,
    sharepoint,
)
from O365.utils import Token, BaseTokenBackend
from O365.utils.utils import (  # noqa: F401 pylint: disable=unused-import
    ME_RESOURCE,
    USERS_RESOURCE,
    GROUPS_RESOURCE,
    SITES_RESOURCE,
)
from robot.api.deco import keyword


DEFAULT_REDIRECT_URI = "https://login.microsoftonline.com/common/oauth2/nativeclient"
DEFAULT_TOKEN_PATH = Path("/temp")
DEFAULT_PROTOCOL = MSGraphProtocol()


def import_table():
    """Try to import `RPA.Tables.Table`"""
    try:
        module = importlib.import_module("RPA.Tables")
        return getattr(module, "Table")
    except ModuleNotFoundError:
        return None


Table = import_table()
DataTable = Table if Table else list[Dict]


class MSGraphAuthenticationError(Exception):
    "Error when authentication fails."


class MSGraphDownloadError(Exception):
    "Error when download fails."


class RobocorpVaultTokenBackend(BaseTokenBackend):
    "A simple Token backend that saves to Robocorp vault"


class SharedItem(drive.File):
    """Simple class to add support for shared items.
    Inherits File only to bypass checks in the library.
    """  # pylint: disable=super-init-not-called

    def __init__(self, data, url, con):
        self.name = data["name"]
        self.size = data["size"]
        self.con = con
        self.url = url
        self.object_id = None

    def build_url(self, *args):  # pylint: disable=unused-argument
        """Discard arguments since we already have the correct URL."""
        return self.url


class MSGraph:
    """
    The *MSGraph* library wraps the `O365 package`_, giving robots
    the ability to access the Microsoft Graph API programmatically.

    OAuth Configuration
    -------------------

    Graph's API primarily authenticates via the OAuth 2.0 authorization code grant
    flow or OpenID Connect. This library exposes the OAuth 2.0 flow for robots to
    authenticate on behalf of users. A user must complete an initial authentication
    flow with the help of our `OAuth Graph Example Bot`_.

    For best results, `register an app`_ in Azure AD and configure it as so:

    - The type is "Web App".
    - Redirect URI should be ``https://login.microsoftonline.com/common/oauth2/nativeclient``
    - The app should be a multi-tenant app.
    - ``Accounts in any organizational directory`` is checked.
    - Has relevant permissions enabled, check the `Microsoft Graph permissions reference`_
    for a list of permissions available to MS Graph apps.

    .. TODO: Determine bundles of permissions needed for each keyword in the library.

    .. _O365 package: https://pypi.org/project/O365
    .. _OAuth Graph Example Bot: https://robocorp.com/portal/
    .. _register an app: https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
    .. _Microsoft Graph permissions reference: https://docs.microsoft.com/en-us/graph/permissions-reference


    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "Global"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        token: Optional[Token] = None,  # pylint: disable=unused-argument
        refresh_token: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        vault_backend: bool = False,
        vault_secret: Optional[str] = None,
        file_backend_path: Optional[Path] = DEFAULT_TOKEN_PATH,
    ) -> None:
        """When importing the library to Robot Framework, you can set the
        ``client_id`` and ``client_secret``.

        :param client_id: Application client id.
        :param client_secret: Application client secret.

        """
        self.logger = logging.getLogger(__name__)
        # TODO: Implement a `TokenBackend` that uses Robocorp vault,
        #       if implemented, returned refresh tokens are unnecessary.
        if not vault_backend:
            self.token_backend = FileSystemTokenBackend(
                file_backend_path, "auth_token.txt"
            )
        elif vault_backend and not vault_secret:
            raise ValueError(
                "Argument vault_secret cannot be blank if vault_backend set to True."
            )
        else:
            raise NotImplementedError(
                "Robocorp vault token backend not yet implemented."
            )
        if client_id and client_secret:
            self.configure_msgraph_client(
                client_id, client_secret, refresh_token, redirect_uri
            )
        else:
            self.client = None
            self.redirect_uri = redirect_uri or DEFAULT_REDIRECT_URI

    def _require_client(self):
        if self.client is None:
            raise MSGraphAuthenticationError("The MSGraph client is not configured.")

    def _require_authentication(self):
        self._require_client()
        if not self.client.is_authenticated:
            raise MSGraphAuthenticationError(
                "The MS Graph client is not authenticated."
            )

    def _get_refresh_token(self):
        """Returns the refresh token using the backend if that backend
        is not the Vault.
        """
        try:
            if isinstance(self.token_backend, FileSystemTokenBackend):
                return self.token_backend.load_token().get("refresh_token")
            else:
                return None
        except AttributeError:
            return None

    def _get_drive_instance(
        self, resource: Optional[str] = None, drive_id: Optional[str] = None
    ) -> drive.Drive:
        """Returns the specified drive if any or the default one if none."""
        storage = self.client.storage(resource=resource)
        if drive_id:
            return storage.get_drive(drive_id)
        else:
            return storage.get_default_drive()

    def _get_folder_instance(
        self,
        drive_instance: drive.Drive,
        folder: Union[drive.Folder, str, None] = None,
    ) -> drive.Folder:
        """Get folder from OneDrive."""
        if isinstance(folder, drive.DriveItem):
            if isinstance(folder, drive.Folder):
                return folder
            else:
                raise TypeError("The folder argument is not of Folder type.")
        elif folder in [None, "/", "\\", "root", "ROOT", ""]:
            return drive_instance.get_root_folder()
        else:
            return drive_instance.get_item_by_path(folder)

    def _get_file_instance(
        self, target_file: Union[drive.File, str], drive_instance: drive.Drive
    ) -> drive.File:
        if isinstance(target_file, str):
            return drive_instance.get_item_by_path(target_file)
        elif isinstance(target_file, drive.File):
            return drive_instance.get_item(target_file.object_id)
        else:
            raise TypeError("Target file is not any of the expected types.")

    def _encode_share_url(self, file_url: str) -> str:
        """Encodes the OneDrive file share link to a format supported
        by the Graph API.
        """
        base64_bytes = base64.b64encode(bytes(file_url, "utf-8"))
        base64_string = (
            base64_bytes.decode("utf-8")
            .replace("=", "")
            .replace("/", "_")
            .replace("+", "-")
        )
        return "u!{}".format(base64_string)

    def _download_file(
        self,
        file_instance: drive.File,
        to_path: Union[Path, str, None] = None,
        name: Optional[str] = None,
    ) -> Path:
        """Downloads the file and return the destination path.
        The O365 library returns only a boolean, so it was necessary
        to define the destination path the same way the library does it.
        """
        if not isinstance(file_instance, drive.File):
            raise MSGraphDownloadError("Drive item is not a file.")

        if to_path is None:
            to_path = Path()
        else:
            if not isinstance(to_path, Path):
                to_path = Path(to_path)

        if not to_path.exists():
            raise FileNotFoundError("{} does not exist".format(to_path))

        if name and not Path(name).suffix and file_instance.name:
            name = name + Path(file_instance.name).suffix

        name = name or file_instance.name
        downloaded_file = to_path / name

        success = file_instance.download(to_path=to_path, name=name)
        if not success:
            raise MSGraphDownloadError("Downloading file failed.")
        return downloaded_file

    def _download_folder(
        self, folder_instance: drive.Folder, to_folder: Union[Path, str, None] = None
    ) -> Path:
        """Downloads the content of the folder recursively.
        The O365 library returns only a boolean, so it was necessary to define
        the destination path the same way the O365 library does it.
        """
        if not isinstance(folder_instance, drive.Folder):
            raise MSGraphDownloadError("Drive item is not a folder.")
        if to_folder is None:
            downloaded_folder = Path() / folder_instance.name
        else:
            downloaded_folder = Path() / to_folder
        # Method download_contents has no return value.
        folder_instance.download_contents(to_folder=to_folder)
        return downloaded_folder

    def _get_sharepoint_drive(
        self, site: sharepoint.Site, drive_id: str = None
    ) -> drive.Drive:
        """Returns the specified SharePoint drive if any or the default one if none."""
        if drive_id:
            return site.get_document_library(drive_id)
        else:
            return site.get_default_document_library()

    def _sharepoint_items_into_dict_list(
        self, items_instance: list[sharepoint.SharepointListItem]
    ) -> list[dict]:
        """Turns a list of SharePointListItem into a list of dictionaries.
        This improves the Robot Developer experience, since the inspection
        of attributes isn't easy in Robot Framework.
        """
        items_list = []
        for item in items_instance:
            item_dict = {"object_id": item.object_id}
            item_dict.update(item.fields)
            items_list.append(item_dict)
        return items_list

    @keyword
    def configure_msgraph_client(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: Optional[str] = None,
        redirect_uri: str = DEFAULT_REDIRECT_URI,
    ) -> Union[str, None]:
        """Configures the MS Graph client. If a refresh token is
        known, it can be provided to obtain a current user token
        to authenticate with. A new refresh token is returned
        if one is provided.
        """
        credentials = (client_id, client_secret)
        self.client = Account(credentials, token_backend=self.token_backend)
        self.redirect_uri = redirect_uri
        if refresh_token:
            return self.refresh_oauth_token(refresh_token)
        return None

    @keyword
    def get_scopes(self, *scopes: str) -> list:
        # pylint: disable=anomalous-backslash-in-string
        """Returns the proper scope definitions based on the
        provided "scope helpers", which are enumerated below.
        You can pass none to get all scopes. Basic is included
        in all other scopes. The provided object can be passed
        to the ``scopes`` parameter when calling
        \`Generate OAuth Authorization URL\`.

        * ``basic``
        * ``mailbox``
        * ``mailbox_shared``
        * ``message_send``
        * ``message_send_shared``
        * ``message_all``
        * ``message_all_shared``
        * ``address_book``
        * ``address_book_shared``
        * ``address_book_all``
        * ``address_book_all_shared``
        * ``calendar``
        * ``calendar_shared``
        * ``calendar_all``
        * ``calendar_shared_all``
        * ``users``
        * ``onedrive``
        * ``onedrive_all``
        * ``sharepoint``
        * ``sharepoint_dl``
        * ``settings_all``
        * ``tasks``
        * ``tasks_all``
        * ``presence``
        """  # noqa: W605
        if len(scopes) == 0:
            return DEFAULT_PROTOCOL.get_scopes_for(None)
        else:
            scopes_to_get = [s.lower() for s in scopes]
            if "basic" not in scopes_to_get:
                scopes_to_get.append("basic")
            return DEFAULT_PROTOCOL.get_scopes_for(scopes_to_get)

    @keyword
    def generate_oauth_authorization_url(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: str = None,
        scopes: list = None,
    ) -> str:
        # pylint: disable=anomalous-backslash-in-string
        """Generates an authorization URL which must be opened
        by the user to complete the OAuth flow. If no scopes
        are provided, the default scope is used which is all
        scopes defined in the \`Get Scopes\` keyword
        """  # noqa: W605
        if redirect_uri is None:
            redirect_uri = (
                self.redirect_uri
                if self.redirect_uri is not None
                else DEFAULT_REDIRECT_URI
            )
        if not self.client:
            self.configure_msgraph_client(
                client_id, client_secret, redirect_uri=redirect_uri
            )
        if scopes is None:
            scopes = self.get_scopes()
        return self.client.connection.get_authorization_url(
            scopes,
            redirect_uri,
        )[0]

    @keyword
    def authorize_and_get_token(self, authorization_url: str) -> str:
        # pylint: disable=anomalous-backslash-in-string
        """Exchanges the OAuth authorization URL obtained from
        \`Generate OAuth Authorization URL\` for an access token. This
        library maintains the user access token for current requests
        and returns the refresh token to be stored in a secure location
        (e.g., the Robocorp Control Room Vault).
        """  # noqa: W605
        self._require_client()
        if self.client.connection.request_token(
            authorization_url, redirect_uri=self.redirect_uri
        ):
            self.logger.info("Authentication successful.")
            return self._get_refresh_token()
        else:
            raise MSGraphAuthenticationError(
                f"Authentication not successful using '{authorization_url}' as auth URL."  # noqa: E501
            )

    @keyword
    def refresh_oauth_token(self, refresh_token: Optional[str] = None) -> str:
        """Refreshes the user token using the provided ``refresh_token``.
        The user token is retained in the library and a new
        refresh token is returned. If no token is provided, this keyword
        assumes the Robocorp Vault is being used as a backend and attempts
        to refresh it based on that backend.
        """
        self._require_client()
        if refresh_token:
            self.token_backend.token = Token(refresh_token=refresh_token)
            self.token_backend.save_token()
        if self.client.connection.refresh_token():
            self.logger.info("Token successfully refreshed.")
            return self._get_refresh_token()
        else:
            raise MSGraphAuthenticationError("Access token could not be refreshed.")

    @keyword
    def get_me(self) -> directory.User:
        """Returns the MS Graph object representing the currently logged
        in user. A User object is returned. Properties of the user can
        be accessed like so:

        .. code-block: robotframework

            *** Tasks ***
            Get the me user object
                ${me}=    Get Me
                Log    ${me.full_name}
                Log    ${me.display_name}
                Log    ${me.given_name}
                Log    ${me.surname}
                Log    ${me.full_name}
                Log    ${me.mail}
                Log    ${me.business_phones}
                Log    ${me.mobile_phone}
                Log    ${me.about_me}
                Log    ${me.interests}
                Log    ${me.job_title}
                Log    ${me.object_id}
                Log    ${me.user_principal_name}
        """
        self._require_authentication()
        return self.client.get_current_user()

    @keyword
    def search_for_users(
        self,
        search_string: str,
        search_field: str = "displayName",
        resource: str = USERS_RESOURCE,
    ) -> list[directory.User]:
        # pylint: disable=anomalous-backslash-in-string
        """Returns a list of user objects from the Active Directory
        based on the provided search string.

        User objects have additional properties that can be accessed
        with dot-notation, see \`Get Me\` for additional details.

        :param search_string: Text to search for.
        :param search_field: Where to search. Defaults to display name.
        :param resource: Name of the resource if not using default.

        .. code-block: robotframework

            *** Tasks ***
            Search users
                ${users}=    Search For Users    John
        """  # noqa: W605
        self._require_authentication()

        # Get the session if not already defined, which is necessary because we
        # need to modify the headers.
        if self.client.con.session is None:
            self.client.con.session = self.client.con.get_session(load_token=True)

        # It is necessary to pass a specific header to use $search, as the error
        # message instructs: "Request with $search query parameter only works through
        # MSGraph with a special request header: 'ConsistencyLevel: eventual'".
        active_directory = self.client.directory(resource)
        query = active_directory.new_query().search(f"{search_field}:{search_string}")
        self.client.con.session.headers["ConsistencyLevel"] = "eventual"
        users = active_directory.get_users(query=query)
        del self.client.con.session.headers["ConsistencyLevel"]
        return users

    @keyword
    def list_files_in_onedrive_folder(
        self,
        target_folder: Union[drive.Folder, str, None] = None,
        include_folders: Optional[bool] = False,
        resource: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> list[drive.DriveItem]:
        """Returns a list of files from the specified OneDrive folder.

        The files returned are DriveItem objects and they have additional
        properties that can be accessed with dot-notation.

        :param target_folder: Path of the folder in OneDrive.
        :param include_folders: Boolean indicating if should return folders as well.
        :param resource: Name of the resource if not using default.
        :param drive_id: Drive ID if not using default.
        :return: List of DriveItems in the folder.

        .. code-block: robotframework

            *** Tasks ***
            List files
                ${files}=    List Files In Onedrive Folder    /path/to/folder
                FOR    ${file}    IN    @{files}
                    Log    ${file.name}
                    Log    ${file.extension}
                    Log    ${file.description}
                    Log    ${file.created_by}
                    Log    ${file.created}
                    Log    ${file.is_file}
                    Log    ${file.is_image}
                    Log    ${file.is_photo}
                    Log    ${file.is_folder}
                    Log    ${file.size}
                    Log    ${file.web_url}
                END
        """
        self._require_authentication()
        drive_instance = self._get_drive_instance(resource, drive_id)
        folder = self._get_folder_instance(drive_instance, target_folder)
        items = folder.get_items()
        if include_folders:
            return items
        return [item for item in items if not item.is_folder]

    @keyword
    def download_file_from_onedrive(
        self,
        target_file: Union[drive.File, str],
        to_path: Union[Path, str, None] = None,
        name: Optional[str] = None,
        resource: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> Path:
        """Downloads a file from OneDrive.

        The downloaded file will be saved to a local path.

        :param target_file: `DriveItem` or file path of the desired file.
        :param to_path: Destination folder of the downloaded file,
                defaults to the current directory.
        :param name: New name for the downloaded file, with or without extension.
        :param resource: Name of the resource if not using default.
        :param drive_id: Drive ID if not using default.
        :return: Path to the downloaded file.

        .. code-block: robotframework

            *** Tasks ***
            Download file with path
                ${download_path}=    Download File From Onedrive
                ...    /path/to/onedrive/file
                ...    /path/to/local/folder
                ...    Report.pdf

            Download file with object
                ${download_path}=    Download File From Onedrive
                ...    ${drive_item}
                ...    /path/to/local/folder
                ...    Report.pdf
        """
        self._require_authentication()
        drive_instance = self._get_drive_instance(resource, drive_id)
        file_instance = self._get_file_instance(target_file, drive_instance)
        return self._download_file(file_instance, to_path, name)

    @keyword
    def download_folder_from_onedrive(
        self,
        target_folder: Union[drive.Folder, str],
        to_path: Union[Path, str, None] = None,
        resource: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> Path:
        """Downloads a folder from OneDrive with all of it's contents,
        including subfolders.

        Caution when downloading big folder structures. The downloaded
        folder will be saved to a local path.

        :param target_folder: `DriveItem` or path of the desired folder.
        :param to_path: Destination folder where the download will be saved to,
                defaults to the current directory.
        :param resource: Name of the resource if not using default.
        :param drive_id: Drive ID if not using default.
        :return: Path to the downloaded folder.

        .. code-block: robotframework

            *** Tasks ***
            Download folder with path
                ${download_path}=    Download Folder From Onedrive
                ...    /path/to/onedrive/folder
                ...    /path/to/local/folder

            Download folder with object
                ${download_path}=    Download Folder From Onedrive
                ...    ${drive_item}
                ...    /path/to/local/folder
        """
        self._require_authentication()
        drive_instance = self._get_drive_instance(resource, drive_id)
        folder_instance = self._get_folder_instance(drive_instance, target_folder)
        return self._download_folder(folder_instance, to_path)

    @keyword
    def find_onedrive_file(
        self,
        search_string: str,
        target_folder: Union[drive.Folder, str, None] = None,
        include_folders: Optional[bool] = False,
        resource: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> list[drive.DriveItem]:
        # pylint: disable=anomalous-backslash-in-string
        """Returns a list of files found in OneDrive based on the search string.
        If a folder is not specified, the search is done in the entire drive and
        may include items that were shared with the user. It is possible to pass
        \`root\` as the target folder in order to avoid this behavior.

        The files returned are DriveItem objects and they have additional
        properties that can be accessed with dot-notation, see
        \`List Files In Onedrive Folder\` for details.

        :param search_string: String used to search for file in OneDrive.
         Values may be matched across several fields including filename,
         metadata, and file content.
        :param target_folder: Folder where to search for files.
        :param include_folders: Boolean indicating if should return folders as well.
        :param resource: Name of the resource if not using default.
        :param drive_id: Drive ID if not using default.
        :return: List of DriveItems found based on the search string.

        .. code-block: robotframework

            *** Tasks ***
            Find file
                ${files}=    Find Onedrive File    Report.xlsx
        """  # noqa: W605
        self._require_authentication()
        drive_instance = self._get_drive_instance(resource, drive_id)
        if target_folder:
            folder = self._get_folder_instance(drive_instance, target_folder)
            items = folder.search(search_string)
        else:
            items = drive_instance.search(search_string)
        if include_folders:
            return items
        return [item for item in items if not item.is_folder]

    @keyword
    def download_file_from_share_link(
        self,
        share_url: str,
        to_path: Union[Path, str, None] = None,
        name: Optional[str] = None,
    ) -> Path:
        """Downloads file from the share link.

        The downloaded file will be saved to a local path.

        :param share_url: URL of the shared file
        :param to_path: Destination folder of the downloaded file,
                defaults to the current directory.
        :param name: New name for the downloaded file, with or without extension.

        .. code-block: robotframework

            *** Tasks ***
            Download file
                ${download_path}=    Download File From Share Link
                ...    https://...
                ...    /path/to/local/folder
                ...    Report.pdf
        """
        self._require_authentication()

        # O365 doesn't support getting items from shared links yet
        base_url = self.client.protocol.service_url
        base_url = base_url[:-1] if base_url.endswith("/") else base_url
        encoded_url = self._encode_share_url(share_url)
        endpoint = "/shares/{id}/driveItem"
        direct_url = "{}{}".format(base_url, endpoint.format(id=encoded_url))

        response = self.client.con.get(direct_url)
        if not response:
            return None

        data = response.json()
        file_instance = SharedItem(data, direct_url, self.client.con)
        return self._download_file(file_instance, to_path, name)

    @keyword
    def upload_file_to_onedrive(
        self,
        file_path: str,
        target_folder: Union[drive.Folder, str, None] = None,
        resource: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> drive.DriveItem:
        # pylint: disable=anomalous-backslash-in-string
        """Uploads a file to the specified OneDrive folder.

        The uploaded file is returned as a DriveItem object and it has
        additional properties that can be accessed with dot-notation, see
        \`List Files In Onedrive Folder\` for details.

        :param file_path: Path of the local file being uploaded.
        :param target_folder: Path of the folder in OneDrive.
        :param resource: Name of the resource if not using default.
        :param drive_id: Drive ID if not using default.

        .. code-block: robotframework

            *** Tasks ***
            Upload file
                ${file}=    Upload File To Onedrive
                ...    /path/to/file.txt
                ...    /path/to/folder
        """  # noqa: W605
        self._require_authentication()
        drive_instance = self._get_drive_instance(resource, drive_id)
        folder = self._get_folder_instance(drive_instance, target_folder)
        return folder.upload_file(item=file_path)

    @keyword
    def get_sharepoint_site(
        self, *args: str, resource: Optional[str] = ""
    ) -> sharepoint.Site:
        """Returns a SharePoint site.

        :param args: It accepts multiple ways of retrieving a site. See below.

         get_site(host_name): the host_name e.g. 'contoso.sharepoint.com'
         or 'root'.

         get_site(site_id): the site_id is a comma separated string of
         (host_name, site_collection_id, site_id).

         get_site(host_name, path_to_site): host_name e.g. 'contoso.
         sharepoint.com' and path_to_site is a url path (with a leading slash).

         get_site(host_name, site_collection_id, site_id): a collection of
         (host_name, site_collection_id, site_id).

        :param resource: Name of the resource if not using default.
        :return: SharePoint Site instance.

        The return is of type Site and it has additional properties
        that can be accessed with dot-notation. See examples below.

        .. code-block: robotframework

            *** Tasks ***
            Get site
                ${site}=    Get Sharepoint Site    contoso.sharepoint.com
                Log    ${site.name}
                Log    ${site.display_name}
                Log    ${site.description}
                Log    ${site.web_url}
                Log    ${site.object_id}
        """
        self._require_authentication()
        sp = self.client.sharepoint(resource=resource)
        return sp.get_site(*args)

    @keyword
    def get_items_from_sharepoint_list(
        self,
        list_name: str,
        site: sharepoint.Site,
    ) -> DataTable:
        # pylint: disable=anomalous-backslash-in-string
        """Returns the items on a SharePoint list. The list is found
        by it's display name.

        This keyword tries to return the SharePoint list it as a table
        (see ``RPA.Tables``), if ``RPA.Tables`` is not available in the
        keyword's scope, the data will be returned as a list of dictionaries.

        :param list_name: Display name of the SharePoint list.
        :param site: Site instance obtained from \`Get Sharepoint Site\`.
        :return: Table or list of dicts of the items.

        .. code-block: robotframework

            *** Tasks ***
            Get List
                ${table}=    Get Items From Sharepoint List    My List    ${site}
        """  # noqa: W605
        self._require_authentication()
        sp_list = site.get_list_by_name(list_name)
        sp_items = sp_list.get_items(expand_fields=True)
        items = self._sharepoint_items_into_dict_list(sp_items)

        if not Table:
            self.logger.info(
                "Tables in the response will be in a `dictionary` type, "
                "because `RPA.Tables` library is not available in the scope."
            )
        return DataTable(items) if Table else items

    @keyword
    def create_sharepoint_list(
        self,
        list_data: dict,
        site: sharepoint.Site,
    ) -> sharepoint.SharepointList:
        # pylint: disable=anomalous-backslash-in-string
        """Creates a sharepoint list and returns the instance.

        :param list_data: Dictionary with the data for the new list.
        :param site: Site instance obtained from \`Get Sharepoint Site\`.
        :return: SharePoint List that was created.

        List objects have additional properties that can be accessed
        with dot-notation, see examples below.

        .. code-block: robotframework

            *** Tasks ***
            Create list
                ${list}=    Create Sharepoint List
                ...    ${list_data}
                ...    ${site}
                Log    ${list.object_id}
                Log    ${list.name}
                Log    ${list.display_name}
                Log    ${list.description}
                Log    ${list.column_name_cw}
                Log    ${list.created_by}
                Log    ${list.created}
                Log    ${list.last_modified_by}
                Log    ${list.modified}
                Log    ${list.web_url}
        """  # noqa: W605
        self._require_authentication()
        return site.create_list(list_data)

    @keyword
    def list_sharepoint_site_drives(self, site: sharepoint.Site) -> list[drive.Drive]:
        # pylint: disable=anomalous-backslash-in-string
        """Get a list of Drives available in the SharePoint Site.

        :param site: Site instance obtained from \`Get Sharepoint Site\`.
        :return: List of Drives present in the SharePoint Site.

        .. code-block: robotframework

            *** Tasks ***
            List SharePoint drives
                ${drives}    List Sharepoint Site Drives    ${site}
                FOR    ${drive}    IN    @{drives}
                    Log    ${drive.name}
                    Log    ${drive.description}
                    Log    ${drive.owner.display_name}
                    Log    ${drive.web_url}
                    Log    ${drive.object_id}
                END
        """  # noqa: W605
        self._require_authentication()
        return site.list_document_libraries()

    @keyword
    def list_files_in_sharepoint_site_drive(
        self,
        site: sharepoint.Site,
        include_folders: Optional[bool] = False,
        drive_id: Optional[str] = None,
    ) -> list[drive.DriveItem]:
        # pylint: disable=anomalous-backslash-in-string
        """List files in the SharePoint Site drive.

        If the drive_id is not informed, the default Document Library will be used.
        The drive_id can be obtained from the keyword \`List Sharepoint Site Drives\`.

        The files returned are DriveItem objects and they have additional
        properties that can be accessed with dot-notation, see
        \`List Files In Onedrive Folder\` for details.

        :param site: Site instance obtained from \`Get Sharepoint Site\`.
        :param include_folders: Boolean indicating if should return folders as well.
        :param drive_id: ID of the desired drive.
        :return: List of DriveItems present in the Site Drive.

        .. code-block: robotframework

            *** Tasks ***

            List files in SharePoint drive
                ${files}    List Files In Sharepoint Site Drive    ${site}
        """  # noqa: W605
        self._require_authentication()
        sp_drive = self._get_sharepoint_drive(site, drive_id)
        folder = self._get_folder_instance(sp_drive)
        items = folder.get_items()
        if include_folders:
            return items
        return [item for item in items if not item.is_folder]

    @keyword
    def download_file_from_sharepoint(
        self,
        target_file: Union[drive.File, str],
        site: sharepoint.Site,
        to_path: Union[Path, str, None] = None,
        name: Optional[str] = None,
        drive_id: Optional[str] = None,
    ) -> Path:
        # pylint: disable=anomalous-backslash-in-string
        """Downloads file from SharePoint.

        The downloaded file will be saved to a local folder.

        :param target_file: `DriveItem` or file path of the desired file.
        :param site: Site instance obtained from \`Get Sharepoint Site\`.
        :param to_path: Destination folder of the downloaded file,
                defaults to the current directory.
        :param name: New name for the downloaded file, with or without extension.
        :param drive_id: Drive ID if not using default.
        :return: Path to the downloaded file.

        .. code-block: robotframework

            *** Tasks ***
            Download file
                ${download_path}=    Download File From Sharepoint
                ...    /path/to/sharepoint/file
                ...    ${site}
                ...    /path/to/local/folder
                ...    Report.pdf

            Download file with object
                ${download_path}=    Download File From Onedrive
                ...    ${drive_item}
                ...    ${site}
                ...    /path/to/local/folder
                ...    Report.pdf
        """  # noqa: W605
        self._require_authentication()
        sp_drive = self._get_sharepoint_drive(site, drive_id)
        file_instance = self._get_file_instance(target_file, sp_drive)
        return self._download_file(file_instance, to_path, name)
