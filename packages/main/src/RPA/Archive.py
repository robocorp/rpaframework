from datetime import datetime
from fnmatch import fnmatch
import logging
import os
import os.path
from pathlib import Path
import tarfile
from typing import Union, List
import zipfile


def convert_date(timestamp):
    if isinstance(timestamp, tuple):
        d = datetime(
            year=timestamp[0],
            month=timestamp[1],
            day=timestamp[2],
            hour=timestamp[3],
            minute=timestamp[4],
            second=timestamp[5],
        )
    else:
        d = datetime.utcfromtimestamp(timestamp)
    formatted_date = d.strftime("%d.%m.%Y %H:%M:%S")
    return formatted_date


def list_files_in_directory(folder, recursive=False, include=None, exclude=None):
    filelist = []
    for rootdir, _, files in os.walk(folder):
        for file in files:
            archive_absolute = os.path.join(rootdir, file)
            archive_relative = rootdir.replace(folder, "")
            archive_relative = os.path.join(archive_relative, file)
            if include and not fnmatch(archive_relative, include):
                continue
            if exclude and fnmatch(archive_relative, exclude):
                continue
            filelist.append((archive_absolute, archive_relative))
        if not recursive:
            break
    return filelist


class Archive:
    """`Archive` is a library for operating with ZIP and TAR packages.

    **Examples**

    .. code-block:: robotframework

       *** Settings ***
       Library  RPA.Archive

       *** Tasks ***
       Creating a ZIP archive
          Archive Folder With ZIP   ${CURDIR}${/}tasks  tasks.zip   recursive=True  include=*.robot  exclude=/.*
          @{files}                  List Archive             tasks.zip
          FOR  ${file}  IN  ${files}
             Log  ${file}
          END
          Add To Archive            .${/}..${/}missing.robot  tasks.zip
          &{info}                   Get Archive Info


    .. code-block:: python

        from RPA.Archive import Archive

        lib = Archive()
        lib.archive_folder_with_tar('./tasks', 'tasks.tar', recursive=True)
        files = lib.list_archive('tasks.tar')
        for file in files:
           print(file)
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def archive_folder_with_zip(
        self,
        folder: str,
        archive_name: str,
        recursive: bool = False,
        include: str = None,
        exclude: str = None,
        compression: str = "stored",
    ) -> None:
        # pylint: disable=C0301
        """Create a zip archive of a folder

        :param folder: name of the folder to archive
        :param archive_name: filename of the archive
        :param recursive: should sub directories be included, defaults is False
        :param include: define file pattern to include in the package, defaults to None (means all files)
        :param exclude: define file pattern to exclude from the package, defaults is None
        :param compression: type of package compression method, defaults to "stored"

        This keyword creates an ZIP archive of a local folder. By default subdirectories are not
        included, but they can included using `recursive` argument.

        To include only certain files, like TXT files, the argument `include` can be used.
        Similarly to exclude certain file, like dotfiles, the argument `exclude` can be used.

        Compression methods:

        - stored, default
        - deflated
        - bzip2
        - lzma

        Example:

        .. code-block:: robotframework

            Archive Folder With Zip  ${CURDIR}${/}documents  mydocs.zip
            Archive Folder With Zip  ${CURDIR}${/}tasks      robottasks.zip   include=*.robot
            Archive Folder With Zip  ${CURDIR}${/}tasks      no_dotfiles.zip  exclude=/.*
            Archive Folder With Zip  ${CURDIR}${/}documents  documents.zip    recursive=True
            Archive Folder With Zip  ${CURDIR}               packagelzma.zip  compression=lzma
            Archive Folder With Zip  ${CURDIR}               bzipped.zip      compression=bzip2
        """  # noqa: E501
        if compression == "stored":
            comp_method = zipfile.ZIP_STORED
        elif compression == "deflated":
            comp_method = zipfile.ZIP_DEFLATED
        elif compression == "bzip2":
            comp_method = zipfile.ZIP_BZIP2
        elif compression == "lzma":
            comp_method = zipfile.ZIP_LZMA
        else:
            raise ValueError("Unknown compression method")

        filelist = list_files_in_directory(folder, recursive, include, exclude)
        if len(filelist) == 0:
            raise ValueError("No files found to archive")

        with zipfile.ZipFile(
            file=archive_name,
            mode="w",
            compression=comp_method,
        ) as archive:
            for archive_absolute, archive_relative in filelist:
                archive.write(archive_absolute, arcname=archive_relative)

    def archive_folder_with_tar(
        self,
        folder: str,
        archive_name: str,
        recursive: bool = False,
        include: str = None,
        exclude: str = None,
    ) -> None:
        """Create a tar/tar.gz archive of a folder

        :param folder: name of the folder to archive
        :param archive_name: filename of the archive
        :param recursive: should sub directories be included, defaults is False
        :param include: define file pattern to include in the package,
            by default all files are included
        :param exclude: define file pattern to exclude from the package

        This keyword creates an TAR or TAR.GZ archive of a local folder. Type of archive
        is determined by the file extension. By default subdirectories are not
        included, but they can included using `recursive` argument.

        To include only certain files, like TXT files, the argument `include` can be used.
        Similarly to exclude certain file, like dotfiles, the argument `exclude` can be used.

        Example:

        .. code-block:: robotframework

            Archive Folder With TAR  ${CURDIR}${/}documents  documents.tar
            Archive Folder With TAR  ${CURDIR}${/}tasks      tasks.tar.gz   include=*.robot
            Archive Folder With TAR  ${CURDIR}${/}tasks      tasks.tar      exclude=/.*
            Archive Folder With TAR  ${CURDIR}${/}documents  documents.tar  recursive=True
        """  # noqa: E501
        filelist = list_files_in_directory(folder, recursive, include, exclude)
        if len(filelist) == 0:
            raise ValueError("No files found to archive")

        with tarfile.TarFile(archive_name, "w") as archive:
            for archive_absolute, archive_relative in filelist:
                archive.add(archive_absolute, arcname=archive_relative)

    def add_to_archive(
        self,
        files: Union[List, str],
        archive_name: str,
        folder: str = None,
    ) -> None:
        """Add file(s) to the archive

        :param files: name of the file, or list of files, to add
        :param archive_name: filename of the archive
        :param folder: name of the folder for added file,
            relative path in the archive

        This keyword adds file or list of files into existing archive. Files
        can be added to archive structure with relative path using argument `folder`.

        Example:

        .. code-block:: robotframework

            Add To Archive  extrafile.txt  myfiles.zip
            Add To Archive  stat.png       archive.tar.gz  images
            @{files}        Create List    filename1.txt   filename2.txt
            Add To Archive  ${files}       files.tar
        """
        files_to_add = []

        if isinstance(files, list):
            for filename in files:
                file_relative = Path(filename).name
                if folder:
                    file_relative = folder + os.path.sep + file_relative
                files_to_add.append((filename, file_relative))
        else:
            file_relative = Path(files).name
            if folder:
                file_relative = folder + os.path.sep + file_relative
            files_to_add.append((files, file_relative))

        if zipfile.is_zipfile(archive_name):
            with zipfile.ZipFile(archive_name, "a") as zip_archive:
                for filename, file_relative in files_to_add:
                    zip_archive.write(filename, arcname=file_relative)
        elif tarfile.is_tarfile(archive_name):
            with tarfile.TarFile(archive_name, "a") as tar_archive:
                for file_absolute, file_relative in files_to_add:
                    tar_archive.add(file_absolute, arcname=file_relative)

    def list_archive(self, archive_name: str) -> list:
        """List files in an archive

        :param archive_name: filename of the archive

        Returns list of file, where each file in a list is a dictionary
        with following attributes:

        - name
        - size
        - mtime
        - last modification time in format `%d.%m.%Y %H:%M:%S`

        Example:

        .. code-block:: robotframework

            @{files}   List Archive    myfiles.zip
            FOR  ${file}  IN   ${files}
                Log  ${file}[filename]
                Log  ${file}[size]
                Log  ${file}[mtime]
            END
        """
        filelist = []
        if zipfile.is_zipfile(archive_name):
            with zipfile.ZipFile(archive_name, "r") as f:
                members = f.infolist()
                for memb in members:
                    filelist.append(
                        {
                            "filename": memb.filename,
                            "size": memb.file_size,
                            "mtime": memb.date_time,
                            "modified": convert_date(memb.date_time),
                        }
                    )
        elif tarfile.is_tarfile(archive_name):
            with tarfile.TarFile(archive_name, "r") as f:
                members = f.getmembers()
                for memb in members:
                    filelist.append(
                        {
                            "name": memb.name,
                            "size": memb.size,
                            "mtime": memb.mtime,
                            "modified": convert_date(memb.mtime),
                        }
                    )
        return filelist

    def get_archive_info(self, archive_name: str) -> dict:
        """Get information about the archive

        :param archive_name: filename of the archive

        Returns following file attributes in a dictionary:

        - filename
        - filemode
        - size
        - mtime
        - last modification time in format `%d.%m.%Y %H:%M:%S`

        Example:

        .. code-block:: robotframework

            &{archiveinfo}   Get Archive Info    myfiles.zip
        """
        archive_info = None
        st = os.stat(archive_name)
        if zipfile.is_zipfile(archive_name):
            with zipfile.ZipFile(archive_name, "r") as f:
                archive_info = {
                    "filename": f.filename,
                    "mode": f.mode,
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "modified": convert_date(st.st_mtime),
                }
        elif tarfile.is_tarfile(archive_name):
            with tarfile.TarFile(archive_name, "r") as f:
                archive_info = {
                    "filename": f.name,
                    "mode": f.mode,
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                    "modified": convert_date(st.st_mtime),
                }
        return archive_info

    def extract_archive(
        self, archive_name: str, path: str = None, members: Union[List, str] = None
    ) -> None:
        """Extract files from archive into local directory

        :param archive_name: filename of the archive
        :param path: filepath to extract file into, default is current working directory
        :param members: list of files to extract from, by default
            all files in archive are extracted

        This keyword supports extracting files from zip, tar and tar.gz archives.

        By default file is extracted into current working directory, but `path` argument
        can be set to define extraction path.

        Example:

        .. code-block:: robotframework

            Extract Archive    myfiles.zip   ${CURDIR}${/}extracted
            @{files}           Create List   filename1.txt    filename2.txt
            Extract Archive    archive.tar   C:${/}myfiles${/}  ${files}
        """  # noqa: E501
        root = Path(path) if path else Path.cwd()
        if members and not isinstance(members, list):
            members = [members]
        if zipfile.is_zipfile(archive_name):
            with zipfile.ZipFile(archive_name, "r") as f:
                if members:
                    f.extractall(path=root, members=members)
                else:
                    f.extractall(path=root)
        elif tarfile.is_tarfile(archive_name):
            members = map(tarfile.TarInfo, members) if members else None
            with tarfile.open(archive_name, "r") as f:
                if members:
                    f.extractall(path=root, members=members)
                else:
                    f.extractall(path=root)

    def extract_file_from_archive(
        self, filename: str, archive_name: str, path: str = None
    ):  # pylint: disable=C0301
        """Extract a file from archive into local directory

        :param filename: name of the file to extract
        :param archive_name: filename of the archive
        :param path: filepath to extract file into,
            default is current working directory

        This keyword supports extracting a file from zip, tar and tar.gz archives.

        By default file is extracted into current working directory,
        but `path` argument can be set to define extraction path.

        Example:

        .. code-block:: robotframework

            Extract File From Archive    extrafile.txt   myfiles.zip
            Extract File From Archive    background.png  images.tar.gz  ${CURDIR}${/}extracted
        """  # noqa: E501
        root = Path(path) if path else Path.cwd()
        if zipfile.is_zipfile(archive_name):
            with zipfile.ZipFile(archive_name, "r") as outfile:
                outfile.extract(filename, root)
        elif tarfile.is_tarfile(archive_name):
            with tarfile.open(archive_name, "r") as outfile:
                outfile.extract(filename, root)
