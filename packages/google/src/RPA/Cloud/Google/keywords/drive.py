from io import BytesIO
import mimetypes
from pathlib import Path
import shutil
import time
from typing import Dict, List, Optional

from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload, MediaIoBaseDownload

from . import LibraryContext, keyword, UpdateAction
from .enums import DriveRole, DriveType, to_drive_role, to_drive_type


class GoogleDriveError(Exception):
    """Raised with errors in Drive API"""


class DriveKeywords(LibraryContext):
    """Class for Google Drive API

    For more information about Google Drive API link_.

    .. _link: https://developers.google.com/drive/api
    """

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword(tags=["init", "drive"])
    def init_drive(
        self,
        service_account: str = None,
        credentials: str = None,
        use_robocorp_vault: Optional[bool] = None,
        scopes: list = None,
        token_file: str = None,
    ) -> None:
        """Initialize Google Drive client

        :param service_account: file path to service account file
        :param credentials: file path to credentials file
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param scopes: list of extra authentication scopes
        :param token_file: file path to token file
        """
        drive_scopes = [
            "drive",
            "drive.appdata",
            "drive.file",
            "drive.install",
            "drive.metadata",
        ]
        if scopes:
            drive_scopes += scopes
        self.service = self.init_service(
            service_name="drive",
            api_version="v3",
            scopes=drive_scopes,
            service_account_file=service_account,
            credentials_file=credentials,
            use_robocorp_vault=use_robocorp_vault,
            token_file=token_file,
        )

    @keyword(tags=["drive"])
    def upload_drive_file(
        self,
        filename: str = None,
        folder: str = None,
        overwrite: bool = False,
        make_dir: bool = False,
    ) -> str:
        """Upload files into Drive

        :param filename: name of the file to upload
        :param folder: target folder for upload
        :param overwrite: set to `True` if already existing file should be overwritten
        :param make_dir: set to `True` if folder should be created if it does not exist
        :return: uploaded file id

        Example:

        .. code-block:: robotframework

            ${file1_id}=  Upload Drive File  data.json  # Upload file to drive root
            ${file2_id}=  Upload Drive File  newdata.json  new_folder  make_dir=True
            ${file3_id}=  Upload Drive File  data.json  overwrite=True
        """
        folder_id = self.get_drive_folder_id(folder)
        if folder_id is None and make_dir:
            folder = self.create_drive_directory(folder)
            folder_id = folder["id"]
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

        query_string = f"name = '{filepath.name}' and '{folder_id}' in parents"
        self.logger.debug("Upload query_string: '%s'" % query_string)
        target_file = self.search_drive_files(query=query_string, recurse=True)
        guess_mimetype = mimetypes.guess_type(str(filepath.absolute()))
        file_mimetype = guess_mimetype[0] if guess_mimetype else "*/*"
        media = MediaFileUpload(
            filepath.absolute(), mimetype=file_mimetype, resumable=True
        )
        file_metadata = {
            "name": filepath.name,
            "parents": [folder_id],
            "mimeType": file_mimetype,
        }
        self.logger.debug("Upload file_metadata: '%s'" % file_metadata)
        if len(target_file) == 1 and overwrite:
            self.logger.info("Overwriting file '%s' with new content", filename)
            return self._file_update(target_file, media)
        elif len(target_file) == 1 and not overwrite:
            self.logger.warn("Not uploading new copy of file '%s'", filepath.name)
            return target_file[0]["id"]
        elif len(target_file) > 1:
            self.logger.warn(
                "Drive already contains '%s' copies of file '%s'. Not uploading again."
                % (len(target_file), filepath.name)
            )
            return None
        else:
            return self._file_create(file_metadata, media)

    def _file_create(self, file_metadata, media):
        try:
            result = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id",
                )
                .execute()
            )
            return result.get("id", None)
        except HttpError as err:
            raise GoogleDriveError(str(err)) from err

    def _file_update(self, target_file, media):
        try:
            result = (
                self.service.files()
                .update(fileId=target_file[0]["id"], media_body=media, fields="id")
                .execute()
            )
            return result.get("id", None)
        except HttpError as err:
            raise GoogleDriveError(str(err)) from err

    def _download_with_fileobject(self, file_object):
        try:
            request = self.service.files().get_media(fileId=file_object["id"])
        except HttpError as err:
            raise GoogleDriveError(str(err)) from err
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            _, done = downloader.next_chunk()
        fh.seek(0)
        with open(file_object["name"], "wb") as f:
            # pylint: disable=protected-access
            shutil.copyfileobj(fh, f, length=downloader._total_size)

    @keyword(tags=["drive"])
    def download_drive_files(
        self,
        file_dict: dict = None,
        query: str = None,
        source: str = None,
        limit: int = None,
        timeout: float = None,
    ) -> List:
        """Download files specified by file dictionary or query string

        Parameters `start`, `limit` and `timeout` are used only when
        downloading files defined by `query` parameter.

        :param file_dict: file dictionary returned by `Search Drive Files`
        :param query: drive query string to find target files, defaults to None
        :param source: source directory where query is executed
        :param limit: maximum amount of files that are downloaded, defaults to None
        :param timeout: maximum allowed time in seconds for download process
        :return: list of downloaded files

        Example:

        .. code-block:: robotframework

            ${files}=    Search Drive Files    query=name contains '.json'
            FOR    ${f}    IN    @{files}
                IF  ${f}[size] < 2000
                    Download Drive Files  file_dict=${f}
                END
            END

            ${folder_id}=   Get Drive Folder Id   datafolder
            Download Drive Files  query=name contains '.json' and '${folder_id}' in parents
        """  # noqa: E501
        if query:
            filelist = self.search_drive_files(query, source=source)
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
        return []

    @keyword(tags=["drive"])
    def update_drive_file(
        self,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        source: str = None,
        action: UpdateAction = UpdateAction.star,
        multiple_ok: bool = False,
    ) -> int:
        """Update file specified by id, file dictionary or query string

        Possible actions:
        - star
        - unstar
        - trash
        - untrash

        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Drive Search Files`
        :param query: drive query string to find target file, needs to match 1 file
        :param source: source directory where query is executed
        :param action: update action, default star file
        :param multiple_ok: set to `True` if it is ok to perform update
         on more than 1 file
        :return: number of updated files

        Example:

        .. code-block:: robotframework

            ${folder_id}=  Get Drive Folder Id   datafolder
            ${updated}=    Update Drive File  query=name contains '.json' and '${folder_id}' in parents
            ...            action=star
            ...            multiple_ok=True
        """  # noqa: E501
        target_files = self._get_target_file(
            file_id, file_dict, query, multiple_ok, source
        )
        update_count = 0
        for tf in target_files:
            self._drive_files_update(tf, action)
            update_count += 1
        return update_count

    def _get_target_file(
        self, file_id, file_dict, query, multiple_ok, source=None, details=False
    ):
        target_files = []
        if file_id:
            if details:
                filedata = self.get_drive_file_by_id(file_id)
                target_files.append(filedata)
            else:
                target_files.append(file_id)
        elif file_dict:
            target_files.append(file_dict.get("id", None))
        else:
            files = self.search_drive_files(query, source=source, recurse=True)
            target_files = [tf if details else tf.get("id", None) for tf in files]
            if not multiple_ok and len(target_files) > 1:
                raise GoogleDriveError(
                    "expected search to match 1 file, but it matched %s files"
                    % len(files)
                )

        return target_files

    def _drive_files_update(self, file_id: str, action: UpdateAction):
        body = None
        if action == UpdateAction.trash:
            body = {"trashed": True}
        elif action == UpdateAction.untrash:
            body = {"trashed": False}
        elif action == UpdateAction.star:
            body = {"starred": True}
        elif action == UpdateAction.unstar:
            body = {"starred": False}
        else:
            # TODO: mypy should handle enum exhaustivity validation
            raise ValueError(f"Unsupported update action: {action}")
        self.logger.debug(body)
        try:
            updated_file = (
                self.service.files().update(fileId=file_id, body=body).execute()
            )
        except HttpError as err:
            raise GoogleDriveError(str(err)) from err
        return updated_file

    @keyword(tags=["drive"])
    def delete_drive_file(
        self,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        multiple_ok: bool = False,
        suppress_errors: bool = False,
    ) -> int:
        """Delete file specified by id, file dictionary or query string

        Note. Be extra careful when calling this keyword!

        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Search Drive Files`
        :param query: drive query string to find target file, needs to match 1 file
         unless parameter `multiple_ok` is set to `True`
        :param multiple_ok: set to `True` if it is ok to perform delete
         on more than 1 file
        :param suppress_errors: on True will log warning message instead of
         raising an exception, defaults to False
        :return: how many files where deleted

        Example:

        .. code-block:: robotframework

            ${folder_id}=  Get Drive Folder Id   datafolder
            ${deleted}=    Delete Drive File  query=name contains '.json' and '${folder_id}' in parents
            ...            multiple_ok=True
        """  # noqa: E501
        target_files = self._get_target_file(file_id, file_dict, query, multiple_ok)

        delete_count = 0
        for tf in target_files:
            try:
                self.service.files().delete(fileId=tf).execute()
            except HttpError as err:
                if suppress_errors:
                    self.logger.warn(str(err))
                else:
                    raise GoogleDriveError(str(err)) from err
            delete_count += 1
        return delete_count

    @keyword(tags=["drive"])
    def get_drive_folder_id(
        self, folder: str = None, parent_folder: str = None, details: bool = False
    ) -> str:
        """Get file id for the folder

        :param folder: name of the folder to identify, by default returns drive's
         `root` folder id
        :param parent_folder: can be used to narrow search by giving parent
         folder name
        :param details: on True will return folder dictionary, on False (default)
         folder id is returned
        :return: file id of the folder or file dictionary when details = True

        Example:

        .. code-block:: robotframework

            ${root_id}=    Get Drive Folder Id   # returns Drive root folder id
            ${folder_id}=  Get Drive Folder Id  subdir
        """
        mime_folder_type = "application/vnd.google-apps.folder"
        drive_file = None
        if folder is None:
            try:
                drive_file = (
                    self.service.files().get(fileId="root", fields="id").execute()
                )
            except HttpError as err:
                raise GoogleDriveError(str(err)) from err
        else:
            query_string = f"name = '{folder}' AND mimeType = '{mime_folder_type}'"
            parameters = {"query": query_string, "recurse": True}
            if parent_folder:
                parameters["source"] = parent_folder
            folders = self.search_drive_files(**parameters)
            if len(folders) == 1:
                drive_file = folders[0]  # .get("id", None)
            else:
                self.logger.info(
                    "Found %s directories with name '%s'" % (len(folders), folder)
                )
        if drive_file:
            return drive_file if details else drive_file.get("id", None)
        return None

    @keyword(tags=["drive"])
    def move_drive_file(
        self,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        source: str = None,
        target: str = None,
        multiple_ok: bool = False,
    ) -> List:
        """Move file specified by id, file dictionary or query string into target folder

        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Search Drive Files`
        :param query: drive query string to find target file, needs to match 1 file
        :param source: name of the folder to move file from, is by default drive's
         `root` folder id
        :param target: name of the folder to move file into, is by default drive's
         `root` folder id
        :param multiple_ok: if `True` then moving more than 1 file
        :return: list of file ids

        Example:

        .. code-block:: robotframework

            ${source_id}=  Get Drive Folder Id  sourcefolder
            ${query}=      Set Variable  name contains '.json' and '${sourceid}' in parents
            ${files}=      Move Drive File  query=${query}  folder=target_folder  multiple_ok=True
        """  # noqa: E501
        result_files = []
        if file_id or file_dict:
            target_files = self._get_target_file(file_id, file_dict, query, multiple_ok)
        else:
            target_files = self.search_drive_files(query, source=source)
        target_parent = None
        if len(target_files) == 0:
            raise GoogleDriveError("Did not find any files to move")
        if target:
            target_parent = self.get_drive_folder_id(target)
        if target_parent is None:
            raise GoogleDriveError(
                "Unable to find target folder: '%s'" % (target if target else "root")
            )
        for tf in target_files:
            file = self.service.files().get(fileId=tf["id"], fields="parents").execute()
            previous_parents = ",".join(file.get("parents"))
            try:
                result_file = (
                    self.service.files()
                    .update(
                        fileId=tf["id"],
                        addParents=target_parent,
                        removeParents=previous_parents,
                        fields="id, parents",
                    )
                    .execute()
                )
            except HttpError as err:
                raise GoogleDriveError(str(err)) from err
            result_files.append(result_file)
        return result_files

    @keyword(tags=["drive", "drive share", "v2.0.0"])
    def list_shared_drive_files(self, query: str = None, source: str = None) -> List:
        """Keyword for listing shared files in the source folder.

        Alias keyword for ``Search Drive Files`` which can be used to list
        only files which have been shared.

        :param query: drive query string to find target files
        :param source: source directory where query is executed
        :return: list of shared files

        Example:

        .. code-block:: robotframework

            ${shared}=    List Shared Drive Files    source=subfolder
            FOR    ${file}    IN    @{shared}
                Log To Console    ${file}
            END
        """
        files = self.search_drive_files(query=query, source=source)
        return [f for f in files if f["shared"]]

    @keyword(tags=["drive"])
    def search_drive_files(
        self, query: str = None, recurse: bool = False, source: str = None
    ) -> List:
        """Search Google Drive for files matching query string

        :param query: search string, defaults to None which means that all files
         and folders are returned
        :param recurse: set to `True` if search should recursive
        :param source: source directory where query is executed
        :return: list of files

        Example:

        .. code-block:: robotframework

            ${files}=  Search Drive Files   query=name contains 'hello'
            ${files}=  Search Drive Files   query=modifiedTime > '2020-06-04T12:00:00'
            ${files}=  Search Drive Files   query=mimeType contains 'image/' or mimeType contains 'video/'
            ${files}=  Search Drive Files   query=name contains '.yaml'  recurse=True
            ${files}=  Search Drive Files   query=name contains '.yaml'  source=datadirectory
        """  # noqa: E501
        page_token = None
        filelist = []

        parameters = self._set_search_parameters(query, source, recurse)

        while True:
            if page_token:
                parameters["pageToken"] = page_token
            try:
                self.logger.debug("Searching with parameters: '%s'" % parameters)
                response = self.service.files().list(**parameters).execute()
                for file_details in response.get("files", []):
                    file_dict = self._drive_file_details_into_file_dict(file_details)
                    filelist.append(file_dict)
                page_token = response.get("nextPageToken", None)
                if page_token is None:
                    break
            except HttpError as err:
                raise GoogleDriveError(str(err)) from err
        return filelist

    def _set_search_parameters(self, query, source, recurse):
        parameters = {
            "fields": "*",
        }
        if query:
            parameters["q"] = query

        folder_id = None
        if source:
            folder_id = self.get_drive_folder_id(source)
        elif not recurse:
            folder_id = "root"

        if folder_id:
            if "q" in parameters:
                parameters["q"] += f" and '{folder_id}' in parents"
            else:
                parameters["q"] = f"'{folder_id}' in parents"
        return parameters

    def _drive_file_details_into_file_dict(self, details):
        filesize = details.get("size")
        file_id = details.get("id")
        parents = details.get("parents")
        kind = details.get("kind")
        mimetype = details.get("mimeType")
        is_folder = mimetype == "application/vnd.google-apps.folder"
        folder_id = (
            file_id
            if mimetype == "application/vnd.google-apps.folder"
            else parents[0]
            if parents and len(parents) > 0
            else None
        )
        file_link = (
            None
            if mimetype == "application/vnd.google-apps.folder"
            else f"https://drive.google.com/file/d/{file_id}?usp=sharing"
        )
        folder_link = (
            f"https://drive.google.com/drive/folders/{folder_id}?usp=sharing"
            if folder_id
            else ""
        )
        file_dict = {
            "name": details.get("name"),
            "id": file_id,
            "size": int(filesize) if filesize else None,
            "kind": kind,
            "is_folder": is_folder,
            "parents": parents,
            "starred": details.get("starred"),
            "trashed": details.get("trashed"),
            "shared": details.get("shared"),
            "permissions": details.get("permissions", []),
            "mimeType": mimetype,
            "spaces": details.get("spaces", None),
            "exportLinks": details.get("exportLinks"),
            "createdTime": details.get("createdTime"),
            "modifiedTime": details.get("modifiedTime"),
            "fileLink": file_link,
            "folderLink": folder_link,
        }
        return file_dict

    @keyword(tags=["drive"])
    def create_drive_directory(
        self, folder: str = None, parent_folder: str = None
    ) -> Dict:
        """Create new directory to Google Drive

        :param folder: name for the new directory
        :param parent_folder: top level directory for new directory
        :return: dictionary containing folder ID and folder URL

        Example:

        .. code-block:: robotframework

            ${folder}=  Create Drive Directory   example-folder
            Log To Console    Google Drive folder ID: ${folder}[id]
            Log To Console    Google Drive folder URL:  ${folder}[url]
        """
        if not folder or len(folder) == 0:
            raise GoogleDriveError("Can't create Drive directory with empty name")

        folder_id = self.get_drive_folder_id(folder, parent_folder=parent_folder)
        if folder_id:
            self.logger.info(
                "Folder '%s' already exists. Not creating new one.", folder_id
            )
            return self._folder_response(folder_id)

        file_metadata = {
            "name": folder,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_folder:
            parent_folder_id = self.get_drive_folder_id(parent_folder)
            file_metadata["parents"] = [parent_folder_id]
        try:
            added_folder = (
                self.service.files().create(body=file_metadata, fields="id").execute()
            )
            return self._folder_response(added_folder["id"])
        except HttpError as err:
            raise GoogleDriveError(str(err)) from err

    def _folder_response(self, folder_id):
        return {
            "id": folder_id,
            "url": f"https://drive.google.com/drive/folders/{folder_id}?usp=sharing",
        }

    @keyword(tags=["drive"])
    def export_drive_file(
        self,
        file_id: str = None,
        file_dict: dict = None,
        target_file: str = None,
        mimetype: str = "application/pdf",
    ) -> str:
        """Export Google Drive file using Drive export links

        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Search Drive Files`
        :param target_file: name for the exported file
        :param mimetype: export mimetype, defaults to "application/pdf"
        :return: file path to the exported file

        Example:

        .. code-block:: robotframework

            ${files}=  Drive Search Files  query=name contains 'my example worksheet'
            Export Drive File  file_dict=${files}[0]
        """
        if target_file is None or len(target_file) == 0:
            raise AttributeError("The target_file is required parameter for export")
        if file_id is None and file_dict is None:
            raise AttributeError("Either file_id or file_dict is required for export")
        target_files = self._get_target_file(file_id, file_dict, None, False)
        if len(target_files) != 1:
            raise ValueError("Did not find the Google Drive file to export")
        try:
            request = self.service.files().export(
                fileId=target_files[0], mimeType=mimetype
            )
        except HttpError as err:
            raise GoogleDriveError(str(err)) from err

        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            _, done = downloader.next_chunk()

        fh.seek(0)
        filepath = Path(target_file).absolute()
        with open(filepath, "wb") as f:
            shutil.copyfileobj(fh, f, length=131072)
        return filepath

    @keyword(tags=["drive", "drive share", "v2.0.0"])
    def add_drive_share(
        self,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        source: str = None,
        email: str = None,
        domain: str = None,
        role: DriveRole = DriveRole.READER,
        share_type: DriveType = DriveType.USER,
        notification: bool = False,
        notification_message: str = None,
    ) -> Dict:
        """Keyword for sharing drive file or folder.

        Parameters `file_id`, `file_dict`, `query` and `source` can be
        used to select files to which sharing is added to.

        If share is added to a folder, all files within that folder get same
        sharing permissions.

        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Search Drive Files`
        :param query: drive query string to find target file, needs to match 1 file
        :param source: name of the folder to search files in, is by default drive's
         `root` folder
        :param email: user or group email address if share type
         is DriveType.USER or DriveType.GROUP
        :param domain: domain name if share type is DriveType.DOMAIN
        :param role: see ``DriveRole`` enum for possible values,
         defaults to DriveRole.READER
        :param share_type: see ``DriveType`` enum for possible values,
         defaults to DriveType.USER
        :param notification: whether to send notificatin email, defaults to False
        :param notification_message: optional message to include with the notification
        :return: share response dictionary containing 'file_id' and 'permission_id'

        Example:

        .. code-block:: robotframework

            # Add file share for a email address with email notification
            Add Drive Share
            ...    query=name = 'okta.png'
            ...    email=robocorp.tester@gmail.com
            ...    notification=True
            ...    notification_message=Hello. I have shared 'okta.png' with you for review.
            # Add file share for a domain
            Add Drive Share
            ...    query=name = 'okta.png'
            ...    domain=robocorp.com
            # Add folder share for a email address
            ${folder}=    Create Drive Directory   attachments-for-the-task
            ${share}=  Add Drive Share
            ...   file_id=${folder}[id]
            ...   email=robocorp.tester@gmail.com
            ...   role=writer
            Log To Console  Share details: ${share}[file_id], ${share}[permission_id]
        """  # noqa: E501
        target_file = self._get_target_file(
            file_id, file_dict, query, False, source=source
        )
        if not target_file:
            raise GoogleDriveError("Did not find target file")
        if domain:
            share_type = DriveType.DOMAIN
        user_permission = {
            "type": to_drive_type(share_type),
            "role": to_drive_role(role),
        }
        if share_type in [DriveType.USER, DriveType.GROUP]:
            if not email:
                raise ValueError(
                    "email parameter is required with share_type = 'user' or 'group'"
                )
            user_permission["emailAddress"] = email
        if share_type == DriveType.DOMAIN:
            if not domain:
                raise ValueError(
                    "domain parameter is required with share_type = 'domain'"
                )
            user_permission["domain"] = domain

        request_parameters = {
            "fileId": target_file[0],
            "body": user_permission,
            "fields": "id",
            "sendNotificationEmail": notification,
        }
        if notification and notification_message:
            request_parameters["emailMessage"] = notification_message

        try:
            response = self.service.permissions().create(**request_parameters).execute()
            return {"file_id": target_file[0], "permission_id": response["id"]}
        except HttpError as err:
            raise GoogleDriveError(str(err)) from err

    @keyword(tags=["drive", "drive share", "v2.0.0"])
    def remove_drive_share_by_permission_id(
        self,
        permission_id: str,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        source: str = None,
        suppress_errors: bool = False,
    ) -> Dict:
        """Keyword for removing share permission of file or folder
        permission id.

        Parameters `file_id`, `file_dict`, `query` and `source` can be
        used to select files from which sharing is removed.

        :param permission_id: id of the permission to remove
        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Search Drive Files`
        :param query: drive query string to find target file, needs to match 1 file
        :param source: name of the folder to search files in, is by default drive's
         `root` folder
        :param suppress_errors: on True will log warning message instead of
         raising an exception, defaults to False (exception is raised)
        :return: dictionary of permission response

        Example:

        .. code-block:: robotframework

            ${share}=   Add Drive Share
            ...  query=name = 'sharable-files' and mimeType = 'application/vnd.google-apps.folder'
            ...  email=robocorp.tester@gmail.com
            #
            # actions on shared files in the folder 'shareable-files' ....
            #
            Remove Drive Share By Permission Id   ${share}[permission_id]  ${share}[file_id]
        """  # noqa: E501
        target_file = self._get_target_file(
            file_id, file_dict, query, False, source=source
        )
        if not target_file:
            raise GoogleDriveError("Did not find target file")

        self.logger.info(
            "Removing permission id '%s' for file_id '%s'"
            % (permission_id, target_file[0])
        )
        response = None
        try:
            response = (
                self.service.permissions()
                .delete(fileId=target_file[0], permissionId=permission_id)
                .execute()
            )
        except HttpError as err:
            if suppress_errors:
                self.logger.warn(str(err))
            else:
                raise GoogleDriveError(str(err)) from err
        return response

    @keyword(tags=["drive", "drive share", "v2.0.0"])
    def remove_drive_share_by_criteria(
        self,
        email: str = None,
        domain: str = None,
        permission_id: str = None,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        source: str = None,
        suppress_errors: bool = False,
    ) -> List:
        """Keyword for removing share from file or folder
        based on criteria.

        Parameters `file_id`, `file_dict`, `query` and `source` can be
        used to select files from which sharing is removed.

        Parameters `email`, `domain` or `permission_id` can be
        used to select which share is removed from selected files.

        :param email: email address of the permission to remove
        :param domain: domain name of the permission to remove
        :param permission_id: id of the permission to remove
        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Search Drive Files`
        :param query: drive query string to find target files
        :param source: name of the folder to search files in, is by default drive's
         `root` folder
        :param suppress_errors: on True will log warning message instead of
         raising an exception, defaults to False (exception is raised)
        :return: list of dictionaries containing information of file permissions removed

        Example:

        .. code-block:: robotframework

            # Remove domain shares for files in the folder ${FOLDER_NAME}
            ${removed}=    Remove Drive Share By Criteria
            ...    domain=robocorp.com
            ...    source=${FOLDER_NAME}
            # Remove email share for a file
            ${removed}=    Remove Drive Share By Criteria
            ...    query=name = 'okta.png'
            ...    email=robocorp.tester@gmail.com
        """
        if not email and not domain and permission_id:
            raise AttributeError(
                "At least one of the 'email', 'domain' or 'permission_id' "
                "is required to remove drive share"
            )
        target_files = self._get_target_file(
            file_id, file_dict, query, multiple_ok=True, source=source, details=True
        )
        if not target_files or len(target_files) == 0:
            raise GoogleDriveError("Did not find target files")
        permissions_removed = []
        for tf in target_files:
            file_permissions_removed = []
            if "permissions" in tf and tf["permissions"]:
                self.logger.info(
                    "Removing shares from file '%s' id '%s'" % (tf["name"], tf["id"])
                )
                for p in tf["permissions"]:
                    if self._is_permission_removable(p, email, domain, permission_id):
                        self._remove_file_permission(
                            tf, p, file_permissions_removed, suppress_errors
                        )
            if file_permissions_removed:
                permissions_removed.append(
                    {
                        "file_id": tf["id"],
                        "file_name": tf["name"],
                        "permissions_removed": file_permissions_removed,
                    }
                )
        return permissions_removed

    def _is_permission_removable(self, permission, email, domain, permission_id):
        return (
            (
                email
                and "emailAddress" in permission.keys()
                and permission["emailAddress"] == email
            )
            or (
                domain
                and "domain" in permission.keys()
                and permission["domain"] == domain
            )
            or (permission_id and permission["id"] == permission_id)
        )

    def _remove_file_permission(
        self, drive_file, permission, permissions_removed, suppress_errors
    ):
        try:
            self.service.permissions().delete(
                fileId=drive_file["id"], permissionId=permission["id"]
            ).execute()
            permissions_removed.append(permission)
        except HttpError as err:
            if suppress_errors:
                self.logger.warn(str(err))
            else:
                raise GoogleDriveError(str(err)) from err

    @keyword(tags=["drive", "drive share", "v2.0.0"])
    def remove_all_drive_shares(
        self,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        suppress_errors: bool = False,
    ) -> List:
        """Keyword for removing all shares from selected files (only owner
        permission is retained).

        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Search Drive Files`
        :param query: drive query string to find target files
        :param suppress_errors: on True will log warning message instead of
         raising an exception, defaults to False (exception is raised)
        :return: list of dictionaries containing information of file permissions removed

        Example:

        .. code-block:: robotframework

            ${removed}=  Remove All Drive Shares    file_id=${FOLDER_ID}
        """
        target_files = self._get_target_file(
            file_id, file_dict, query, multiple_ok=True, details=True
        )
        permissions_removed = []
        for tf in target_files:
            if "permissions" in tf and tf["permissions"]:
                self.logger.info(
                    "Removing shares from file '%s' id '%s'" % (tf["name"], tf["id"])
                )
                for p in tf["permissions"]:
                    if p["role"] != "owner":
                        self.remove_drive_share_by_permission_id(
                            file_id=tf["id"],
                            permission_id=p["id"],
                            suppress_errors=suppress_errors,
                        )
                        permissions_removed.append(p)
        return permissions_removed

    @keyword(tags=["drive", "v2.0.0"])
    def get_drive_file_by_id(self, file_id: str, suppress_errors: bool = False) -> Dict:
        """Get file dictionary by its file id.

        :param file_id: id of the file in the Google Drive
        :param suppress_errors: on True will log warning message instead of
         raising an exception, defaults to False (exception is raised)
        :return: dictionary containing file information

        Example:

        .. code-block:: robotframework

            ${file_dict}=  Get Drive File By ID    file_id=${FILE_ID}
        """
        response = None
        try:
            raw_response = (
                self.service.files().get(fileId=file_id, fields="*").execute()
            )
            response = self._drive_file_details_into_file_dict(raw_response)
        except HttpError as err:
            if suppress_errors:
                self.logger.warn(str(err))
            else:
                raise GoogleDriveError(str(err)) from err
        return response
