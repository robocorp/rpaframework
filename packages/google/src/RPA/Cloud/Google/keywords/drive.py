from enum import Enum
from io import BytesIO
import mimetypes
from pathlib import Path
import shutil
import time
from typing import Optional

from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload, MediaIoBaseDownload

from . import (
    LibraryContext,
    keyword,
)


class Update(Enum):
    """Possible file update actions."""

    trash = 1
    untrash = 2
    star = 3
    unstar = 4


class GoogleDriveError(Exception):
    """Raised with errors in Drive API"""


class DriveKeywords(LibraryContext):
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

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword
    def init_drive(
        self,
        service_account: str = None,
        credentials: str = None,
        use_robocloud_vault: Optional[bool] = None,
        scopes: list = None,
        token_file: str = None,
        save_token: bool = False,
        auth_type: str = None,
    ) -> None:
        """Initialize Google Cloud Vision client

        :param service_account: filepath to credentials JSON
        :param use_robocloud_vault: use json stored into `Robocloud Vault`
        """
        drive_scopes = (
            ["drive", "drive.appdata", "drive.file", "drive.install", "drive.metadata"]
            + scopes
            if scopes
            else []
        )
        self.service = self.init_service(
            "drive",
            "v3",
            drive_scopes,
            service_account,
            credentials,
            use_robocloud_vault,
            token_file,
            save_token,
            auth_type,
        )

    @keyword
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

        query_string = f"name = '{filepath.name}' and '{folder_id}' in parents"
        target_file = self.drive_search_files(query=query_string, recurse=True)
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

    @keyword
    def drive_download_files(
        self,
        file_dict: dict = None,
        query: str = None,
        source: str = None,
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
            filelist = self.drive_search_files(query, source=source)
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

    @keyword
    def drive_update_file(
        self,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        source: str = None,
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
            files = self.drive_search_files(query, source=source, recurse=True)
            target_files = [tf.get("id", None) for tf in files]
            if not multiple_ok and len(target_files) > 1:
                raise GoogleDriveError(
                    "expected search to match 1 file, but it matched %s files"
                    % len(files)
                )

        return target_files

    def _drive_files_update(self, file_id: str, action: Update):
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
        self.logger.info(body)
        updated_file = self.service.files().update(fileId=file_id, body=body).execute()
        return updated_file

    @keyword
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
        target_files = self._get_target_file(file_id, file_dict, query, multiple_ok)

        delete_count = 0
        for tf in target_files:
            self.service.files().delete(fileId=tf).execute()
            delete_count += 1
        return delete_count

    @keyword
    def drive_get_folder_id(self, folder: str = None):  # , parent_folder: str = None):
        """Get file id for the folder

        :param folder: name of the folder to identify, by default returns drive's
         `root` folder id
        :return: file id of the folder

        Example:

        .. code-block:: robotframework

            ${root_id}=    Drive Get Folder Id   # returns Drive root folder id
            ${folder_id}=  Drive Get Folder Id  subdir
        """
        mime_folder_type = "application/vnd.google-apps.folder"
        folder_id = None
        if folder is None:
            file = self.service.files().get(fileId="root", fields="id").execute()
            folder_id = file.get("id", None)
        else:
            query_string = f"name = '{folder}' AND mimeType = '{mime_folder_type}'"
            # if parent_folder:
            #     parent_folder_id = None
            #     parent_query = (
            #         f"name = '{parent_folder}' AND mimeType = '{mime_folder_type}'"
            #     )
            #     folders = self.drive_search_files(query=parent_query, recurse=True)
            #     if len(folders) == 1:
            #         self.logger.warn("Parent folder id: %s", parent_folder_id)
            #         parent_folder_id = folders[0].get("id", None)
            #         query_string += f"'{parent_folder_id}' in parents"
            folders = self.drive_search_files(query=query_string, recurse=True)
            if len(folders) == 1:
                folder_id = folders[0].get("id", None)
            else:
                self.logger.info(
                    "Found %s directories with name '%s'" % (len(folders), folder)
                )
        return folder_id

    @keyword
    def drive_move_file(
        self,
        file_id: str = None,
        file_dict: dict = None,
        query: str = None,
        source: str = None,
        target: str = None,
        multiple_ok: bool = False,
    ):
        """Move file specified by id, file dictionary or query string into target folder

        :param file_id: drive file id
        :param file_dict: file dictionary returned by `Drive Search Files`
        :param query: drive query string to find target file, needs to match 1 file
        :param source: name of the folder to move file from, is by default drive's
         `root` folder id
        :param target: name of the folder to move file into, is by default drive's
         `root` folder id
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
        # if source:
        #     source_id = self.drive_get_folder_id(source)
        #     query += f"'{source_id}' in parents"
        # target_files = self._get_target_file(file_id, file_dict, query, multiple_ok)
        target_files = self.drive_search_files(query, source=source)
        target_parent = None
        if len(target_files) == 0:
            raise GoogleDriveError("Did not find any files to move")
        if target:
            target_parent = self.drive_get_folder_id(target)
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

    @keyword
    def drive_search_files(
        self, query: str = None, recurse: bool = False, source: str = None
    ) -> list:
        """Search Google Drive for files matching query string

        :param query: search string, defaults to None which means that all files
         and folders are returned
        :param recurse: set to `True` if search should recursive
        :param source: search files in this directory
        :raises GoogleDriveError: if there is a request error
        :return: list of files

        Example:

        .. code-block:: robotframework

            ${files}=  Drive Search Files   query=name contains 'hello'
            ${files}=  Drive Search Files   query=modifiedTime > '2020-06-04T12:00:00'
            ${files}=  Drive Search Files   query=mimeType contains 'image/' or mimeType contains 'video/'
            ${files}=  Drive Search Files   query=name contains '.yaml'  recurse=True
            ${files}=  Drive Search Files   query=name contains '.yaml'  source=datadirectory
        """  # noqa: E501
        page_token = None
        filelist = []
        parameters = {
            "fields": "nextPageToken, files(id, name, mimeType, parents)",
            "q": query,
        }

        if not recurse:
            folder_id = "root" if not source else self.drive_get_folder_id(source)
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

    @keyword
    def drive_create_directory(self, folder: str = None, parent_folder: str = None):
        """Create new directory to Google Drive

        :param folder: name for the new directory
        :raises GoogleDriveError: if folder name is not given
        :return: created file id
        """
        if not folder or len(folder) == 0:
            raise GoogleDriveError("Can't create Drive directory with empty name")

        folder_id = self.drive_get_folder_id(folder)  # , parent_folder)
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
            parent_folder_id = self.drive_get_folder_id(parent_folder)
            file_metadata["parents"] = [parent_folder_id]
        added_folder = (
            self.service.files().create(body=file_metadata, fields="id").execute()
        )
        return added_folder

    @keyword
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
        :return: file path to the exported file

        Example:

        .. code-block:: robotframework

            ${files}=  Drive Search Files  query=name contains 'my example worksheet'
            Drive Export File  file_dict=${files}[0]
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
