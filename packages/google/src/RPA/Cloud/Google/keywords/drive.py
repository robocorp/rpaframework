from io import BytesIO
import mimetypes
from pathlib import Path
import shutil
import time
from typing import Dict, List, Optional

from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload, MediaIoBaseDownload

from . import LibraryContext, keyword, UpdateAction


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
            folder_id = self.create_drive_directory(folder)
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
        if len(target_file) == 1 and overwrite:
            self.logger.info("Overwriting file '%s' with new content", filename)
            file = (
                self.service.files()
                .update(fileId=target_file[0]["id"], media_body=media, fields="id")
                .execute()
            )
            return file.get("id", None)
        elif len(target_file) == 1 and not overwrite:
            self.logger.warn("Not uploading new copy of file '%s'", filepath.name)
            return None
        elif len(target_file) > 1:
            self.logger.warn(
                "Drive already contains '%s' copies of file '%s'. Not uploading again."
                % (len(target_file), filepath.name)
            )
            return None
        else:
            file = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id",
                )
                .execute()
            )
            return file.get("id", None)

    def _download_with_fileobject(self, file_object):
        request = self.service.files().get_media(fileId=file_object["id"])
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
            Download Drive Files  query=name contains '.json' and '${folder_id}' in parents  recurse=True
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

    def _get_target_file(self, file_id, file_dict, query, multiple_ok, source=None):
        target_files = []
        if file_id:
            target_files.append(file_id)
        elif file_dict:
            target_files.append(file_dict.get("id", None))
        else:
            files = self.search_drive_files(query, source=source, recurse=True)
            target_files = [tf.get("id", None) for tf in files]
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
        self.logger.info(body)
        updated_file = self.service.files().update(fileId=file_id, body=body).execute()
        return updated_file

    @keyword(tags=["drive"])
    def delete_drive_file(
        self,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        multiple_ok: bool = False,
    ) -> int:
        """Delete file specified by id, file dictionary or query string

        Note. Be extra careful when calling this keyword!

        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Search Drive Files`
        :param query: drive query string to find target file, needs to match 1 file
         unless parameter `multiple_ok` is set to `True`
        :param multiple_ok: set to `True` if it is ok to perform delete
         on more than 1 file
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
            self.service.files().delete(fileId=tf).execute()
            delete_count += 1
        return delete_count

    @keyword(tags=["drive"])
    def get_drive_folder_id(self, folder: str = None) -> str:
        """Get file id for the folder

        :param folder: name of the folder to identify, by default returns drive's
         `root` folder id
        :return: file id of the folder

        Example:

        .. code-block:: robotframework

            ${root_id}=    Get Drive Folder Id   # returns Drive root folder id
            ${folder_id}=  Get Drive Folder Id  subdir
        """
        mime_folder_type = "application/vnd.google-apps.folder"
        folder_id = None
        if folder is None:
            file = self.service.files().get(fileId="root", fields="id").execute()
            folder_id = file.get("id", None)
        else:
            query_string = f"name = '{folder}' AND mimeType = '{mime_folder_type}'"
            folders = self.search_drive_files(query=query_string, recurse=True)
            if len(folders) == 1:
                folder_id = folders[0].get("id", None)
            else:
                self.logger.info(
                    "Found %s directories with name '%s'" % (len(folders), folder)
                )
        return folder_id

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
            result_files.append(result_file)
        return result_files

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
        parameters = {
            "fields": "nextPageToken, files(id, name, mimeType, parents)",
            "q": query,
        }

        if not recurse:
            folder_id = "root" if not source else self.get_drive_folder_id(source)
            if folder_id is None:
                return []
            parameters["q"] += f" and '{folder_id}' in parents"

        while True:
            if page_token:
                parameters["pageToken"] = page_token
            try:
                response = self.service.files().list(**parameters).execute()
                self.logger.info(response)
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
            except HttpError as e:
                raise GoogleDriveError(str(e)) from e
        return filelist

    @keyword(tags=["drive"])
    def create_drive_directory(
        self, folder: str = None, parent_folder: str = None
    ) -> Dict:
        """Create new directory to Google Drive

        :param folder: name for the new directory
        :param parent_folder: top level directory for new directory
        :return: created file id
        """
        if not folder or len(folder) == 0:
            raise GoogleDriveError("Can't create Drive directory with empty name")

        folder_id = self.get_drive_folder_id(folder)  # , parent_folder)
        if folder_id:
            self.logger.info(
                "Folder '%s' already exists. Not creating new one.", folder_id
            )
            return None

        file_metadata = {
            "name": folder,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_folder:
            parent_folder_id = self.get_drive_folder_id(parent_folder)
            file_metadata["parents"] = [parent_folder_id]
        added_folder = (
            self.service.files().create(body=file_metadata, fields="id").execute()
        )
        return added_folder

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
        request = self.service.files().export(fileId=target_files[0], mimeType=mimetype)

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
