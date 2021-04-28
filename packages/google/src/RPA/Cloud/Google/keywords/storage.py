from typing import Any, Optional

from google.cloud import storage

from . import (
    LibraryContext,
    keyword,
)


class StorageKeywords(LibraryContext):
    """Class for Google Cloud Storage API
     and Google Cloud Storage JSON API

    You will have to grant the appropriate permissions to the
    service account you are using to authenticate with
    @google-cloud/storage. The IAM page in the console is here:
    https://console.cloud.google.com/iam-admin/iam/project

    Link to `Google Storage PyPI`_ page.

    .. _Google Storage PyPI: https://pypi.org/project/google-cloud-storage/
    """

    def __init__(self, ctx):
        super().__init__(ctx)
        self.service = None

    @keyword
    def init_storage(
        self,
        service_account: str = None,
        use_robocorp_vault: Optional[bool] = None,
        token_file: str = None,
    ) -> None:
        """Initialize Google Cloud Storage client

        :param service_account: file path to service account file
        :param use_robocorp_vault: use credentials in `Robocorp Vault`
        :param token_file: file path to token file
        """
        self.service = self.init_service_with_object(
            storage.Client, service_account, use_robocorp_vault, token_file
        )

    @keyword
    def create_bucket(self, bucket_name: str) -> dict:
        """Create Google Cloud Storage bucket

        :param bucket_name: name as string
        :return: bucket

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Create Bucket   visionfolder
        """
        bucket = self.service.create_bucket(bucket_name)
        return bucket

    @keyword
    def delete_bucket(self, bucket_name: str):
        """Delete Google Cloud Storage bucket

        Bucket needs to be empty before it can be deleted.

        :param bucket_name: name as string

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Delete Bucket   visionfolder
        """
        bucket = self.get_bucket(bucket_name)
        try:
            bucket.delete()
        except Exception as e:
            raise ValueError("The bucket you tried to delete was not empty") from e

    @keyword
    def get_bucket(self, bucket_name: str) -> dict:
        """Get Google Cloud Storage bucket

        :param bucket_name: name as string
        :return: bucket

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Get Bucket   visionfolder
        """
        bucket = self.service.get_bucket(bucket_name)
        return bucket

    @keyword
    def list_buckets(self) -> list:
        """List Google Cloud Storage buckets

        :return: list of buckets

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${buckets}=   List Buckets
            FOR  ${bucket}  IN   @{buckets}
                Log  ${bucket}
            END
        """
        return list(self.service.list_buckets())

    @keyword
    def delete_files(self, bucket_name: str, files: Any):
        """Delete files in the bucket

        Files need to be object name in the bucket.

        :param bucket_name: name as string
        :param files: single file, list of files or
            comma separated list of files
        :return: list of files which could not be deleted

         **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=   Delete Files   ${BUCKET_NAME}   file1,file2
        """
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

    @keyword
    def list_files(self, bucket_name: str) -> list:
        """List files in the bucket

        :param bucket_name: name as string
        :return: list of object names in the bucket

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${files}=   List Files   ${BUCKET_NAME}
            FOR  ${bucket}  IN   @{files}
                Log  ${file}
            END
        """
        bucket = self.get_bucket(bucket_name)
        all_blobs = bucket.list_blobs()
        sorted_blobs = sorted(blob.name for blob in all_blobs)
        return [
            {"name": name, "uri": f"gs://{bucket_name}/{name}"} for name in sorted_blobs
        ]

    @keyword
    def upload_file(self, bucket_name: str, filename: str, target_name: str) -> None:
        """Upload a file into a bucket

        :param bucket_name: name as string
        :param filename: filepath to upload file
        :param target_name: target object name

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            Upload File   ${BUCKET_NAME}
            ...   ${CURDIR}${/}test.txt    test.txt
        """
        bucket = self.get_bucket(bucket_name)
        blob = bucket.blob(target_name)
        with open(filename, "rb") as f:
            blob.upload_from_file(f)

    @keyword
    def upload_files(self, bucket_name: str, files: dict) -> None:
        """Upload files into a bucket

        Example `files`:
        files = {"mytestimg": "image1.png", "mydoc": "google.pdf"}

        :param bucket_name: name as string
        :param files: dictionary of object names and filepaths

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${files}=   Create Dictionary
            ...   test1.txt   ${CURDIR}${/}test1.txt
            ...   test2.txt   ${CURDIR}${/}test2.txt
            Upload Files   ${BUCKET_NAME}   ${files}
        """
        if not isinstance(files, dict):
            raise ValueError("files needs to be an dictionary")
        bucket = self.get_bucket(bucket_name)
        for target_name, filename in files.items():
            blob = bucket.blob(target_name)
            blob.upload_from_filename(filename)

    @keyword
    def download_files(self, bucket_name: str, files: Any) -> list:
        """Download files from a bucket

        Example `files`:
        files = {"mytestimg": "image1.png", "mydoc": "google.pdf"}

        :param bucket_name: name as string
        :param files: list of object names or dictionary of
            object names and target files
        :return: list of files which could not be downloaded

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            ${result}=  Download Files   ${BUCKET_NAME}   test1.txt,test2.txt
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
        return notfound
