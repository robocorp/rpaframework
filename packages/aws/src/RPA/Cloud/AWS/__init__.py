# pylint: disable=too-many-lines
from collections import OrderedDict
import importlib
import json
import logging
from functools import wraps
import os
from pathlib import Path
from time import sleep
from typing import Any, Dict, List, Optional, Union

try:
    import boto3
    from botocore.exceptions import ClientError, WaiterError
    from botocore.waiter import Waiter, WaiterModel, create_waiter_with_client
    from boto3.exceptions import S3UploadFailedError

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


from RPA.core.logger import RobotLogListener
from RPA.core.helpers import required_param, required_env

from .textract import TextractDocument


DEFAULT_REGION = "eu-west-1"


def import_vault():
    """Try to import Vault library."""
    try:
        module = importlib.import_module("RPA.Robocorp.Vault")
        return getattr(module, "Vault")
    except ModuleNotFoundError:
        pass
    return None


def import_tables():
    """Try to import Tables library"""
    try:
        module = importlib.import_module("RPA.Tables")
        return getattr(module, "Tables")
    except ModuleNotFoundError:
        return None


SqlTable = (
    getattr(importlib.import_module("RPA.Tables"), "Table") if import_tables() else Dict
)


def aws_dependency_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not HAS_BOTO3:
            raise ValueError(
                "Please install the `aws` package, "
                "`pip install rpaframework-aws` to use RPA.Cloud.AWS library"
            )
        return f(*args, **kwargs)

    return wrapper


class RedshiftDatabaseError(Exception):
    """Raised when the Redshift API raises a database error."""


class AWSBase:
    """AWS base class for generic methods"""

    logger = None
    services: list = []
    clients: dict = {}
    region: Optional[str] = None
    robocorp_vault_name: Optional[str] = None

    def _get_client_for_service(self, service_name: Optional[str] = None):
        """Return client instance for servive if it has been initialized.

        :param service_name: name of the AWS service
        :return: client instance
        """
        if service_name not in self.clients.keys():
            raise KeyError(
                "AWS service %s has not been initialized" % service_name.upper()
            )
        return self.clients[service_name]

    def _set_service(
        self, service_name: Optional[str] = None, client: Optional[Any] = None
    ):
        self.clients[service_name] = client

    @aws_dependency_required
    def _init_client(
        self,
        service_name: str,
        aws_key_id: Optional[str] = None,
        aws_key: Optional[str] = None,
        region: Optional[str] = None,
        use_robocorp_vault: bool = False,
        session_token: Optional[str] = None,
    ):
        if use_robocorp_vault:
            aws_key_id, aws_key, region = self._get_secrets_from_cloud()
        else:
            if aws_key_id is None or aws_key_id.strip() == "":
                aws_key_id = os.getenv("AWS_KEY_ID")
            if aws_key is None or aws_key.strip() == "":
                aws_key = os.getenv("AWS_KEY")
            if region is None or region.strip() == "":
                region = os.getenv("AWS_REGION", self.region)
        if (
            aws_key_id is None
            or aws_key_id.strip() == ""
            or aws_key is None
            or aws_key.strip() == ""
        ):
            auth_params = {}
        else:
            auth_params = {
                "aws_access_key_id": aws_key_id,
                "aws_secret_access_key": aws_key,
            }
        if session_token:
            auth_params["aws_session_token"] = session_token
        self.logger.info("Using region: %s", region)
        client = boto3.client(service_name, region_name=region, **auth_params)
        self._set_service(service_name, client)

    def set_robocorp_vault(self, vault_name):
        """Set Robocorp Vault name

        :param vault_name: Robocorp Vault name
        """
        if vault_name:
            self.robocorp_vault_name = vault_name

    def _get_secrets_from_cloud(self):
        vault = import_vault()
        if not vault:
            raise ImportError(
                "RPA.Robocorp.Vault library is required to use Vault"
                " with RPA.Cloud.AWS library"
            )
        if not self.robocorp_vault_name:
            raise KeyError(
                "Please set Vault secret name with 'Set Robocorp Vault' keyword"
            )
        vault_items = vault().get_secret(self.robocorp_vault_name)
        vault_items = {k.upper(): v for (k, v) in vault_items.items()}
        try:
            aws_key_id = vault_items["AWS_KEY_ID"]
            aws_key = vault_items["AWS_KEY"]
            region = vault_items.get("AWS_REGION", self.region)
            return aws_key_id, aws_key, region
        except KeyError as err:
            raise KeyError(
                "Secrets 'AWS_KEY_ID' and 'AWS_KEY' need to exist in the Vault '%s'"
                % self.robocorp_vault_name
            ) from err


class ServiceS3(AWSBase):
    """Class for AWS S3 service"""

    def __init__(self) -> None:
        self.services.append("s3")
        self.logger.debug("ServiceS3 init")

    def init_s3_client(
        self,
        aws_key_id: Optional[str] = None,
        aws_key: Optional[str] = None,
        region: Optional[str] = None,
        use_robocorp_vault: bool = False,
        session_token: Optional[str] = None,
    ) -> None:
        """Initialize AWS S3 client

        :param aws_key_id: access key ID
        :param aws_key: secret access key
        :param region: AWS region
        :param use_robocorp_vault: use secret stored in `Robocorp Vault`
        :param session_token: a session token associated with temporary
            credentials, such as from ``Assume Role``.
        """
        self._init_client(
            "s3", aws_key_id, aws_key, region, use_robocorp_vault, session_token
        )

    @aws_dependency_required
    def create_bucket(self, bucket_name: Optional[str] = None, **kwargs) -> bool:
        """Create S3 bucket with name

        **note** This keyword accepts additional parameters in key=value format

        More info on `additional parameters <https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.create_bucket/>`_.

        :param bucket_name: name for the bucket
        :return: boolean indicating status of operation

        Robot Framework example:

        .. code-block:: robotframework

            Create Bucket  public-bucket   ACL=public-read-write
        """  # noqa: E501
        required_param(bucket_name, "create_bucket")
        client = self._get_client_for_service("s3")
        try:
            response = client.create_bucket(Bucket=bucket_name, **kwargs)
            return response["ResponseMetadata"]["HTTPStatusCode"] == 204
        except ClientError as e:
            self.logger.error(e)
            return False

    @aws_dependency_required
    def delete_bucket(self, bucket_name: Optional[str] = None) -> bool:
        """Delete S3 bucket with name

        :param bucket_name: name for the bucket
        :return: boolean indicating status of operation
        """
        required_param(bucket_name, "delete_bucket")
        client = self._get_client_for_service("s3")
        try:
            response = client.delete_bucket(Bucket=bucket_name)
            return response["ResponseMetadata"]["HTTPStatusCode"] == 204
        except ClientError as e:
            self.logger.error(e)
            return False

    @aws_dependency_required
    def list_buckets(self) -> list:
        """List all buckets for this account

        :return: list of buckets
        """
        client = self._get_client_for_service("s3")
        response = client.list_buckets()
        return response["Buckets"] if "Buckets" in response else []

    @aws_dependency_required
    def delete_files(
        self, bucket_name: Optional[str] = None, files: Optional[list] = None, **kwargs
    ):
        """Delete files in the bucket

        **note** This keyword accepts additional parameters in key=value format

        More info on `additional parameters <https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.delete_objects/>`_.

        :param bucket_name: name for the bucket
        :param files: list of files to delete
        :return: number of files deleted or `False`
        """  # noqa: E501
        required_param(bucket_name, "delete_files")
        if not files:
            self.logger.warning(
                "Parameter `files` is empty. There is nothing to delete."
            )
            return False
        if not isinstance(files, list):
            files = files.split(",")
        client = self._get_client_for_service("s3")
        try:
            objects = {"Objects": [{"Key": f} for f in files]}
            response = client.delete_objects(
                Bucket=bucket_name, Delete=objects, **kwargs
            )
            return len(response["Deleted"]) if "Deleted" in response else 0
        except ClientError as e:
            self.logger.error(e)
            return False

    @aws_dependency_required
    def list_files(
        self,
        bucket_name: str,
        limit: Optional[int] = None,
        search: Optional[str] = None,
        prefix: Optional[str] = None,
        **kwargs,
    ) -> list:
        """List files in the bucket

        **note** This keyword accepts additional parameters in key=value format

        More info on `additional parameters <https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.list_objects_v2/>`_.

        :param bucket_name: name for the bucket
        :param limit: limits the response to maximum number of items
        :param search: `JMESPATH <https://jmespath.org/>`_ expression to filter
         objects
        :param prefix: limits the response to keys that begin with the
         specified prefix
        :param kwargs: allows setting all extra parameters for
         `list_objects_v2` method
        :return: list of files

        **Python examples**

        .. code:: python

            # List all files in a bucket
            files = AWSlibrary.list_files("bucket_name")

            # List files in a bucket matching `.yaml`
            files = AWSlibrary.list_files(
                "bucket_name", search="Contents[?contains(Key, '.yaml')]"
            )

            # List files in a bucket matching `.png` and limit results to max 3
            files = AWSlibrary.list_files(
                "bucket_name", limit=3, search="Contents[?contains(Key, '.png')]"
            )

            # List files in a bucket prefixed with `special` and get only 1
            files = AWSlibrary.list_files(
                "bucket_name", prefix="special", limit=1
            )

        **Robot Framework examples**

        .. code:: robotframework

            # List all files in a bucket
            @{files}=   List Files   bucket-name

            # List files in a bucket matching `.yaml`
            @{files}=   List Files
            ...    bucket-name
            ...    search=Contents[?contains(Key, '.yaml')]

            # List files in a bucket matching `.png` and limit results to max 3
            @{files}=  List Files
            ...   bucket-name
            ...   limit=3
            ...   search=Contents[?contains(Key, '.png')]

            # List files in a bucket prefixed with `special` and get only 1
            @{files}=   List Files
            ...   bucket-name
            ...   prefix=special
            ...   limit=1
            )
        """  # noqa: E501
        client = self._get_client_for_service("s3")
        paginator = client.get_paginator("list_objects_v2")
        max_keys = min(limit or 1001, 1000)

        new_params = self._set_list_files_arguments(prefix, limit)
        request_params = {**kwargs, **new_params}

        files = []
        try:
            paginated = paginator.paginate(Bucket=bucket_name, **request_params)
            if search:
                filtered = paginated.search(search)
                for index, page in enumerate(filtered, start=1):
                    if page:
                        files.append(page)
                    if limit and limit == index:
                        break
            else:
                for index, page in enumerate(paginated, start=1):
                    if limit and (index * max_keys) > limit:
                        break
                    files.extend(page["Contents"] if "Contents" in page.keys() else [])

        except ClientError as e:
            self.logger.error(e)
        return files

    def _set_list_files_arguments(self, prefix=None, limit=None):
        kwargs = {}
        if prefix:
            kwargs["Prefix"] = prefix
        if limit and limit < 1000:
            kwargs["MaxKeys"] = limit
        return kwargs

    @aws_dependency_required
    def _s3_upload_file(self, bucket_name, filename, object_name, **kwargs):
        client = self._get_client_for_service("s3")
        uploaded = False
        error = None
        try:
            client.upload_file(filename, bucket_name, object_name, **kwargs)
            uploaded = True
        except ClientError as e:
            error = str(e)
            uploaded = False
        except FileNotFoundError as e:
            error = str(e)
            uploaded = False
        except S3UploadFailedError as e:
            error = str(e)
            uploaded = False
        return (uploaded, error)

    @aws_dependency_required
    def upload_file(
        self,
        bucket_name: Optional[str] = None,
        filename: Optional[str] = None,
        object_name: Optional[str] = None,
        **kwargs,
    ) -> tuple:
        """Upload single file into bucket

        :param bucket_name: name for the bucket
        :param filename: filepath for the file to be uploaded
        :param object_name: name of the object in the bucket, defaults to None
        :return: tuple of upload status and error

        If `object_name` is not given then basename of the file is
        used as `object_name`.

        **note** This keyword accepts additional parameters in key=value format (see below code example).

        More info on `additional parameters <https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.upload_file/>`_.

        Robot Framework example:

        .. code-block:: robotframework

            &{extras}=    Evaluate    {'ContentType': 'image/png'}
            ${uploaded}    ${error}=    Upload File
            ...    mybucket
            ...    ${CURDIR}${/}image.png
            ...    image.png
            ...    ExtraArgs=${extras}
        """  # noqa: E501
        required_param([bucket_name, filename], "upload_file")
        if object_name is None:
            object_name = Path(filename).name
        return self._s3_upload_file(bucket_name, filename, object_name, **kwargs)

    @aws_dependency_required
    def upload_files(
        self, bucket_name: Optional[str] = None, files: Optional[list] = None, **kwargs
    ) -> list:
        """Upload multiple files into bucket

        :param bucket_name: name for the bucket
        :param files: list of files (2 possible ways, see above)
        :return: number of files uploaded

        Giving files as list of filepaths:
            ['/path/to/file1.txt', '/path/to/file2.txt']

        Giving files as list of dictionaries (including filepath and object name):
            [{'filename':'/path/to/file1.txt', 'object_name': 'file1.txt'},
            {'filename': '/path/to/file2.txt', 'object_name': 'file2.txt'}]

        **note** This keyword accepts additional parameters in key=value format (see below code example).

        More info on `additional parameters <https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.upload_file/>`_.

        Python example (passing ExtraArgs):

        .. code-block:: python

            upload_files = [
                {
                    "filename": "./image.png",
                    "object_name": "image.png",
                    "ExtraArgs": {"ContentType": "image/png", "Metadata": {"importance": "1"}},
                },
                {
                    "filename": "./doc.pdf",
                    "object_name": "doc.pdf",
                    "ExtraArgs": {"ContentType": "application/pdf"},
                },
            ]
            awslibrary.upload_files("mybucket", files=upload_files)
        """  # noqa: E501
        required_param([bucket_name, files], "upload_files")
        upload_count = 0
        for _, item in enumerate(files):
            # filepath = None
            # object_name = None
            parameters = {"filename": None, "object_name": None}
            if isinstance(item, dict):
                # filepath = item["filepath"]
                # object_name = item["object_name"]
                parameters = item
            elif isinstance(item, str):
                parameters["filename"] = item
                parameters["object_name"] = Path(item).name
            else:
                error = "incorrect input format for files"

            uploaded, error = self._s3_upload_file(bucket_name, **parameters, **kwargs)
            if uploaded:
                upload_count += 1
            if error:
                self.logger.warning("File upload failed with error: %s", error)
        return upload_count

    @aws_dependency_required
    def download_files(
        self,
        bucket_name: Optional[str] = None,
        files: Optional[list] = None,
        target_directory: Optional[str] = None,
        **kwargs,
    ) -> list:
        """Download files from bucket to local filesystem

        **note** This keyword accepts additional parameters in key=value format.

        More info on `additional parameters <https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.download_file/>`_.

        :param bucket_name: name for the bucket
        :param files: list of S3 object names
        :param target_directory: location for the downloaded files, default
            current directory
        :return: number of files downloaded
        """  # noqa: E501
        required_param([bucket_name, files, target_directory], "download_files")
        client = self._get_client_for_service("s3")
        download_count = 0

        for _, object_name in enumerate(files):
            try:
                object_as_path = Path(object_name)
                download_path = str(Path(target_directory) / object_as_path.name)
                response = client.download_file(
                    bucket_name, object_name, download_path, **kwargs
                )
                if response is None:
                    download_count += 1
            except ClientError as e:
                self.logger.error("Download error with '%s': %s", object_name, str(e))

        return download_count

    @aws_dependency_required
    def generate_presigned_url(
        self,
        bucket_name: str,
        object_name: str,
        expires_in: Optional[int] = None,
        **extra_params,
    ) -> tuple:
        """Generate presigned URL for the file.

        :param bucket_name: name for the bucket
        :param object_name: name of the file in the bucket
        :param expires_in: optional expiration time for the url (in seconds).
         The default expiration time is 3600 seconds (one hour).
        :param extra_params: allows setting any extra `Params`
        :return: URL for accessing the file
        """
        client = self._get_client_for_service("s3")
        response = None
        try:
            request_params = {
                "Params": {"Bucket": bucket_name, "Key": object_name, **extra_params}
            }
            if expires_in:
                request_params["ExpiresIn"] = int(expires_in)
            response = client.generate_presigned_url(
                "get_object",
                **request_params,
            )
        except ClientError as e:
            self.logger.error("Client request error: %s", str(e))
        return response


class ServiceTextract(AWSBase):
    """Class for AWS Textract service"""

    def __init__(self):
        self.services.append("textract")
        self.logger.debug("ServiceTextract init")
        self.tables = {}
        self.cells = {}
        self.lines = {}
        self.words = {}
        self.pages = 0

    def init_textract_client(
        self,
        aws_key_id: Optional[str] = None,
        aws_key: Optional[str] = None,
        region: Optional[str] = None,
        use_robocorp_vault: bool = False,
        session_token: Optional[str] = None,
    ):
        """Initialize AWS Textract client

        :param aws_key_id: access key ID
        :param aws_key: secret access key
        :param region: AWS region
        :param use_robocorp_vault: use secret stored in `Robocorp Vault`
        :param session_token: a session token associated with temporary
            credentials, such as from ``Assume Role``.
        """
        self._init_client(
            "textract", aws_key_id, aws_key, region, use_robocorp_vault, session_token
        )

    @aws_dependency_required
    def analyze_document(
        self,
        image_file: Optional[str] = None,
        json_file: Optional[str] = None,
        bucket_name: Optional[str] = None,
        model: bool = False,
    ) -> bool:
        """Analyzes an input document for relationships between detected items

        :param image_file: filepath (or object name) of image file
        :param json_file: filepath to resulting json file
        :param bucket_name: if given then using `image_file` from the bucket
        :param model: set `True` to return Textract Document model, default `False`
        :return: analysis response in json or TextractDocument model

        Example:

        .. code-block:: robotframework

            ${response}    Analyze Document    ${filename}    model=True
            FOR    ${page}    IN    @{response.pages}
                Log Many    ${page.tables}
                Log Many    ${page.form}
                Log Lines    ${page.lines}
                Log Many    ${page}
                Log    ${page}
                Log    ${page.form}
            END
        """
        client = self._get_client_for_service("textract")
        if bucket_name:
            response = client.analyze_document(
                Document={"S3Object": {"Bucket": bucket_name, "Name": image_file}},
                FeatureTypes=["TABLES", "FORMS"],
            )
        else:
            with open(image_file, "rb") as img:
                response = client.analyze_document(
                    Document={"Bytes": img.read()}, FeatureTypes=["TABLES", "FORMS"]
                )
        self.pages = response["DocumentMetadata"]["Pages"]
        self._parse_response_blocks(response)
        if json_file:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(response, f)
        return self.convert_textract_response_to_model(response) if model else response

    def _parse_response_blocks(self, response):
        if "Blocks" not in response:
            return False
        blocks = response["Blocks"]
        raw_tables = {}
        self.cells = {}
        self.lines = {}
        self.words = {}
        for b in blocks:
            if b["BlockType"] == "TABLE":
                raw_tables[b["Id"]] = []
                if "Relationships" in b:
                    raw_tables[b["Id"]] = b["Relationships"][0]["Ids"]
            elif b["BlockType"] == "CELL":
                self.cells[b["Id"]] = {
                    "Content": None,
                    "RowIndex": b["RowIndex"],
                    "ColumnIndex": b["ColumnIndex"],
                    "RowSpan": b["RowSpan"],
                    "ColumnSpan": b["ColumnSpan"],
                    "Childs": [],
                }
                if "Relationships" in b:
                    self.cells[b["Id"]]["Childs"] = b["Relationships"][0]["Ids"]
            elif b["BlockType"] == "LINE":
                self.lines[b["Id"]] = [b["Text"], b["Confidence"]]
            elif b["BlockType"] == "WORD":
                self.words[b["Id"]] = b["Text"]
        self._process_cells()
        self._process_tables(raw_tables)
        return True

    def _process_cells(self):
        for idx, cell in self.cells.items():
            content = ""
            for cid in cell["Childs"]:
                content += "{} ".format(self.words[cid])
            # pylint: disable=unnecessary-dict-index-lookup
            self.cells[idx]["Content"] = content

    def _process_tables(self, raw_tables):
        self.tables = {}
        for idx, t in raw_tables.items():
            rows = {}
            for tid in t:
                row = self.cells[tid]["RowIndex"]
                col = self.cells[tid]["ColumnIndex"]
                val = self.cells[tid]["Content"]
                if row in rows.keys():
                    rows[row][col] = val
                else:
                    rows[row] = {col: val}

            tables = import_tables()
            if not tables:
                self.logger.info(
                    "Tables in the AWS response will be in a `dictionary` type, "
                    "because `RPA.Tables` library is not available in the scope."
                )
            data = [
                [rows[col][idx] for idx in sorted(rows[col])] for col in sorted(rows)
            ]
            self.tables[idx] = tables().create_table(data) if tables else data

    def get_tables(self):
        """Get parsed tables from the response

        Returns `RPA.Tables.Table` if possible otherwise returns an dictionary.

        :return: tables
        """
        return self.tables

    def get_words(self):
        """Get parsed words from the response

        :return: words
        """
        return self.words

    def get_cells(self):
        """Get parsed cells from the response

        :return: cells
        """
        return self.cells

    @aws_dependency_required
    def detect_document_text(
        self,
        image_file: Optional[str] = None,
        json_file: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> bool:
        """Detects text in the input document.

        :param image_file: filepath (or object name) of image file
        :param json_file: filepath to resulting json file
        :param bucket_name: if given then using `image_file` from the bucket
        :return: analysis response in json
        """
        client = self._get_client_for_service("textract")
        if bucket_name:
            response = client.detect_document_text(
                Document={"S3Object": {"Bucket": bucket_name, "Name": image_file}},
            )
        else:
            with open(image_file, "rb") as img:
                response = client.detect_document_text(
                    Document={"Bytes": img.read()},
                )
        self._parse_response_blocks(response)
        if json_file:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(response, f)
        return response

    @aws_dependency_required
    def start_document_analysis(
        self,
        bucket_name_in: Optional[str] = None,
        object_name_in: Optional[str] = None,
        object_version_in: Optional[str] = None,
        bucket_name_out: Optional[str] = None,
        prefix_object_out: str = "textract_output",
    ):
        """Starts the asynchronous analysis of an input document
        for relationships between detected items such as key-value pairs,
        tables, and selection elements.

        :param bucket_name_in: name of the S3 bucket for the input object,
            defaults to None
        :param object_name_in: name of the input object, defaults to None
        :param object_version_in: version of the input object, defaults to None
        :param bucket_name_out: name of the S3 bucket where to save analysis result
            object, defaults to None
        :param prefix_object_out: name of the S3 bucket for the analysis result object,
        :return: job identifier

        Input object can be in JPEG, PNG or PDF format. Documents should
        be located in the Amazon S3 bucket.

        By default Amazon Textract will save the analysis result internally
        to be accessed by keyword ``Get Document Analysis``. This can
        be overridden by giving parameter ``bucket_name_out``.
        """
        client = self._get_client_for_service("textract")
        s3_object_dict = {"Bucket": bucket_name_in, "Name": object_name_in}

        if object_version_in:
            s3_object_dict["Version"] = object_version_in
        method_arguments = {
            "DocumentLocation": {"S3Object": s3_object_dict},
            "FeatureTypes": ["TABLES", "FORMS"],
        }
        if bucket_name_out:
            method_arguments["OutputConfig"] = {
                "S3Bucket": bucket_name_out,
                "S3Prefix": prefix_object_out,
            }
        response = client.start_document_analysis(**method_arguments)
        return response["JobId"]

    @aws_dependency_required
    def get_document_analysis(
        self,
        job_id: Optional[str] = None,
        max_results: int = 1000,
        next_token: Optional[str] = None,
        collect_all_results: bool = False,
    ) -> dict:
        """Get the results of Textract asynchronous `Document Analysis` operation

        :param job_id: job identifier, defaults to None
        :param max_results: number of blocks to get at a time, defaults to 1000
        :param next_token: pagination token for getting next set of results,
         defaults to None
        :param collect_all_results: when set to True will wait until analysis is
         complete and returns all blocks of the analysis result, by default (False)
         the all blocks need to be specifically collected using `next_token` variable
        :return: dictionary

        Response dictionary has key `JobStatus` with value `SUCCEEDED` when analysis
        has been completed.

        Example:

        .. code-block:: robotframework

            Init Textract Client  %{AWS_KEY_ID}  %{AWS_KEY_SECRET}  %{AWS_REGION}
            ${jobid}=    Start Document Analysis  s3bucket_name  invoice.pdf
            # Wait for job completion and collect all blocks
            ${response}=    Get Document Analysis  ${jobid}  collect_all_results=True
            # Model will contain all pages of the invoice.pdf
            ${model}=    Convert Textract Response To Model    ${response}
        """
        client = self._get_client_for_service("textract")
        method_arguments = {"JobId": job_id, "MaxResults": max_results}
        if next_token:
            method_arguments["NextToken"] = next_token

        total_blocks = []
        response = {}
        while True:
            response = client.get_document_analysis(**method_arguments)
            if collect_all_results and response["JobStatus"] == "IN_PROGRESS":
                self.logger.debug("collecting all and job is still in progress")
                sleep(1)
            elif not collect_all_results:
                break
            else:
                self.logger.debug("Got %s blocks" % len(response["Blocks"]))
                total_blocks += response["Blocks"]
                self.logger.debug("Now having %s blocks" % len(total_blocks))
                if collect_all_results and "NextToken" in response.keys():
                    self.logger.debug("collecting all and there are more results")
                    method_arguments["NextToken"] = response["NextToken"]
                else:
                    break
        total_result = response
        if len(total_blocks) > 0:
            total_result["Blocks"] = total_blocks
        if "Blocks" in total_result.keys():
            self.logger.info("Returning %s blocks" % len(total_result["Blocks"]))
        return total_result

    def get_pages_and_text(self, textract_response: dict) -> dict:
        """Get pages and text out of Textract response json

        :param textract_response: JSON from Textract
        :return: dictionary, page numbers as keys and value is a list
         of text lines
        """
        document = OrderedDict()
        for item in textract_response["Blocks"]:
            if item["BlockType"] == "LINE":
                if item["Page"] in document.keys():
                    document[item["Page"]].append(item["Text"])
                else:
                    document[item["Page"]] = [item["Text"]]
        return document

    @aws_dependency_required
    def start_document_text_detection(
        self,
        bucket_name_in: Optional[str] = None,
        object_name_in: Optional[str] = None,
        object_version_in: Optional[str] = None,
        bucket_name_out: Optional[str] = None,
        prefix_object_out: str = "textract_output",
    ):
        """Starts the asynchronous detection of text in a document.
        Amazon Textract can detect lines of text and the words that make up a
        line of text.

        :param bucket_name_in: name of the S3 bucket for the input object,
            defaults to None
        :param object_name_in: name of the input object, defaults to None
        :param object_version_in: version of the input object, defaults to None
        :param bucket_name_out: name of the S3 bucket where to save analysis result
            object, defaults to None
        :param prefix_object_out: name of the S3 bucket for the analysis result object,
        :return: job identifier

        Input object can be in JPEG, PNG or PDF format. Documents should
        be located in the Amazon S3 bucket.

        By default Amazon Textract will save the analysis result internally
        to be accessed by keyword ``Get Document Text Detection``. This can
        be overridden by giving parameter ``bucket_name_out``.
        """
        client = self._get_client_for_service("textract")
        s3_object_dict = {"Bucket": bucket_name_in, "Name": object_name_in}
        if object_version_in:
            s3_object_dict["Version"] = object_version_in

        method_arguments = {"DocumentLocation": {"S3Object": s3_object_dict}}
        if bucket_name_out:
            method_arguments["OutputConfig"] = {
                "S3Bucket": bucket_name_out,
                "S3Prefix": prefix_object_out,
            }
        response = client.start_document_text_detection(**method_arguments)
        return response["JobId"]

    @aws_dependency_required
    def get_document_text_detection(
        self,
        job_id: Optional[str] = None,
        max_results: int = 1000,
        next_token: Optional[str] = None,
        collect_all_results: bool = False,
    ) -> dict:
        """Get the results of Textract asynchronous `Document Text Detection` operation

        :param job_id: job identifier, defaults to None
        :param max_results: number of blocks to get at a time, defaults to 1000
        :param next_token: pagination token for getting next set of results,
         defaults to None
        :param collect_all_results: when set to True will wait until analysis is
         complete and returns all blocks of the analysis result, by default (False)
         the all blocks need to be specifically collected using `next_token` variable
        :return: dictionary

        Response dictionary has key `JobStatus` with value `SUCCEEDED` when analysis
        has been completed.

        Example:

        .. code-block:: robotframework

            Init Textract Client  %{AWS_KEY_ID}  %{AWS_KEY_SECRET}  %{AWS_REGION}
            ${jobid}=    Start Document Text Detection  s3bucket_name  invoice.pdf
            # Wait for job completion and collect all blocks
            ${response}=   Get Document Text Detection    ${jobid}  collect_all_results=True
            # Model will contain all pages of the invoice.pdf
            ${model}=    Convert Textract Response To Model    ${response}
        """  # noqa: E501
        client = self._get_client_for_service("textract")
        method_arguments = {"JobId": job_id, "MaxResults": max_results}
        if next_token:
            method_arguments["NextToken"] = next_token

        total_blocks = []
        response = {}
        while True:
            response = client.get_document_text_detection(**method_arguments)
            if collect_all_results and response["JobStatus"] == "IN_PROGRESS":
                self.logger.debug("collecting all and job is still in progress")
                sleep(1)
            elif not collect_all_results:
                break
            else:
                self.logger.debug("Got %s blocks" % len(response["Blocks"]))
                total_blocks += response["Blocks"]
                self.logger.debug("Now having %s blocks" % len(total_blocks))
                if collect_all_results and "NextToken" in response.keys():
                    self.logger.debug("collecting all and there are more results")
                    method_arguments["NextToken"] = response["NextToken"]
                else:
                    break
        total_result = response
        if len(total_blocks) > 0:
            total_result["Blocks"] = total_blocks
        if "Blocks" in total_result.keys():
            self.logger.info("Returning %s blocks" % len(total_result["Blocks"]))
        return total_result

    def convert_textract_response_to_model(self, response):
        """Convert AWS Textract JSON response into TextractDocument object,
        which has following structure:

            - Document
            - Page
            - Tables
            - Rows
            - Cells
            - Lines
            - Words
            - Form
            - Field

        :param response: JSON response from AWS Textract service
        :return: `TextractDocument` object

        Example:

        .. code-block:: robotframework

            ${response}    Analyze Document    ${filename}
            ${model}=    Convert Textract Response To Model    ${response}
            FOR    ${page}    IN    @{model.pages}
                Log Many    ${page.tables}
                Log Many    ${page.form}
                Log Lines    ${page.lines}
                Log Many    ${page}
                Log    ${page}
                Log    ${page.form}
            END
        """
        doc = None
        try:
            doc = TextractDocument(response)
        except Exception as e:  # pylint: disable=broad-except
            self.logger.warning(
                "Textract response could not be converted into model: %s", str(e)
            )
        return doc


class ServiceComprehend(AWSBase):
    """Class for AWS Comprehend service"""

    def __init__(self):
        self.services.append("comprehend")
        self.logger.debug("ServiceComprehend init")

    def init_comprehend_client(
        self,
        aws_key_id: Optional[str] = None,
        aws_key: Optional[str] = None,
        region: Optional[str] = None,
        use_robocorp_vault: bool = False,
        session_token: Optional[str] = None,
    ):
        """Initialize AWS Comprehend client

        :param aws_key_id: access key ID
        :param aws_key: secret access key
        :param region: AWS region
        :param use_robocorp_vault: use secret stored in `Robocorp Vault`
        :param session_token: a session token associated with temporary
            credentials, such as from ``Assume Role``.
        """
        self._init_client(
            "comprehend",
            aws_key_id,
            aws_key,
            region,
            use_robocorp_vault,
            session_token,
        )

    @aws_dependency_required
    def detect_sentiment(self, text: Optional[str] = None, lang="en") -> dict:
        """Inspects text and returns an inference of the prevailing sentiment

        :param text: A UTF-8 text string. Each string must contain fewer
            that 5,000 bytes of UTF-8 encoded characters
        :param lang: language code of the text, defaults to "en"
        """
        required_param(text, "detect_sentiment")
        client = self._get_client_for_service("comprehend")
        response = client.detect_sentiment(Text=text, LanguageCode=lang)
        return {
            "Sentiment": response["Sentiment"] if "Sentiment" in response else False,
            "Score": response["SentimentScore"]
            if "SentimentScore" in response
            else False,
        }

    @aws_dependency_required
    def detect_entities(self, text: Optional[str] = None, lang="en") -> dict:
        """Inspects text for named entities, and returns information about them

        :param text: A UTF-8 text string. Each string must contain fewer
            that 5,000 bytes of UTF-8 encoded characters
        :param lang: language code of the text, defaults to "en"
        """
        required_param(text, "detect_entities")
        client = self._get_client_for_service("comprehend")
        response = client.detect_entities(Text=text, LanguageCode=lang)
        return response


class ServiceSQS(AWSBase):
    """Class for AWS SQS service"""

    def __init__(self):
        self.services.append("sqs")
        self.queue_url = None
        self.logger.debug("ServiceSQS init")

    def init_sqs_client(
        self,
        aws_key_id: Optional[str] = None,
        aws_key: Optional[str] = None,
        region: Optional[str] = None,
        queue_url: Optional[str] = None,
        use_robocorp_vault: bool = False,
        session_token: Optional[str] = None,
    ):
        """Initialize AWS SQS client

        :param aws_key_id: access key ID
        :param aws_key: secret access key
        :param region: AWS region
        :param queue_url: SQS queue url
        :param use_robocorp_vault: use secret stored into `Robocorp Vault`
        :param session_token: a session token associated with temporary
            credentials, such as from ``Assume Role``.
        """
        self._init_client(
            "sqs", aws_key_id, aws_key, region, use_robocorp_vault, session_token
        )
        self.queue_url = queue_url

    @aws_dependency_required
    def send_message(
        self, message: Optional[str] = None, message_attributes: Optional[dict] = None
    ) -> dict:
        """Send message to the queue

        :param message: body of the message
        :param message_attributes: attributes of the message
        :return: send message response as dict
        """
        required_param(message, "send_message")
        client = self._get_client_for_service("sqs")
        if message_attributes is None:
            message_attributes = {}
        response = client.send_message(
            QueueUrl=self.queue_url,
            DelaySeconds=10,
            MessageAttributes=message_attributes,
            MessageBody=message,
        )
        return response

    @aws_dependency_required
    def receive_message(self) -> dict:
        """Receive message from queue

        :return: message as dict
        """
        client = self._get_client_for_service("sqs")
        response = client.receive_message(
            QueueUrl=self.queue_url,
        )
        return response["Messages"][0] if "Messages" in response else None

    @aws_dependency_required
    def delete_message(self, receipt_handle: Optional[str] = None):
        """Delete message in the queue

        :param receipt_handle: message handle to delete
        :return: delete message response as dict
        """
        required_param(receipt_handle, "delete_message")
        client = self._get_client_for_service("sqs")
        response = client.delete_message(
            QueueUrl=self.queue_url, ReceiptHandle=receipt_handle
        )
        return response

    @aws_dependency_required
    def create_queue(self, queue_name: Optional[str] = None):
        """Create queue with name

        :param queue_name: [description], defaults to None
        :return: create queue response as dict
        """
        required_param(queue_name, "create_queue")
        client = self._get_client_for_service("sqs")
        response = client.create_queue(queue_name)
        return response

    @aws_dependency_required
    def delete_queue(self, queue_name: Optional[str] = None):
        """Delete queue with name

        :param queue_name: [description], defaults to None
        :return: delete queue response as dict
        """
        required_param(queue_name, "delete_queue")
        client = self._get_client_for_service("sqs")
        response = client.delete_queue(queue_name)
        return response


class ServiceRedshiftData(AWSBase):
    """Class for AWS Redshift Data API Service."""

    # TODO: Implement INSERT from RPA.Table

    def __init__(self) -> None:
        self.services.append("redshift_data")
        self.logger.debug("ServiceRedshiftData init")
        self.cluster_identifier = None
        self.database = None
        self.database_user = None
        self.secret_arn = None

    def init_redshift_data_client(
        self,
        aws_key_id: Optional[str] = None,
        aws_key: Optional[str] = None,
        region: Optional[str] = None,
        cluster_identifier: Optional[str] = None,
        database: Optional[str] = None,
        database_user: Optional[str] = None,
        secret_arn: Optional[str] = None,
        use_robocorp_vault: bool = False,
        session_token: Optional[str] = None,
    ) -> None:
        """Initialize AWS Redshift Data API client

        :param aws_key_id: access key ID
        :param aws_key: secret access key
        :param region: AWS region
        :param cluster_identifier: The cluster identifier. This parameter
            is required when connecting to a cluster and authenticating
            using either Secrets Manager or temporary credentials.
        :param database: The name of the database. This parameter is required
            when authenticating using either Secrets Manager or temporary
            credentials.
        :param database_user: The database user name. This parameter is
            required when connecting to a cluster and authenticating using
            temporary credentials.
        :param secret_arn: The name or ARN of the secret that enables access
            to the database. This parameter is required when authenticating
            using Secrets Manager.
        :param use_robocorp_vault: use secret stored in ``Robocorp Vault``
        :param session_token: a session token associated with temporary
            credentials, such as from ``Assume Role``.
        """
        if database_user and secret_arn:
            raise ValueError("You cannot provide both a secret ARN and database user.")
        self._init_client(
            "redshift-data",
            aws_key_id,
            aws_key,
            region,
            use_robocorp_vault,
            session_token,
        )
        self.cluster_identifier = cluster_identifier
        self.database = database
        self.database_user = database_user
        self.secret_arn = secret_arn

    @aws_dependency_required
    def execute_redshift_statement(
        self,
        sql: str,
        parameters: Optional[list] = None,
        statement_name: Optional[str] = None,
        with_event: bool = False,
        timeout: int = 40,
    ) -> Union[SqlTable, str]:
        r"""Runs an SQL statement, which can be data manipulation language
        (DML) or data definition language (DDL). This statement must be a
        single SQL statement.

        SQL statements can be parameterized with named parameters through
        the use of the ``parameters`` argument. Parameters must be dictionaries
        with the following two keys:

        * ``name``: The name of the parameter. In the SQL statement this
          will be referenced as ``:name``.
        * ``value``: The value of the parameter. Amazon Redshift implicitly
          converts to the proper data type. For more information, see
          `Data types`_ in the `Amazon Redshift Database Developer Guide`.

        For simplicity, a helper keyword, \`Create redshift statement parameters\`,
        is available and can be used more naturally in Robot Framework contexts.

        .. _Data types: https://docs.aws.amazon.com/redshift/latest/dg/c_Supported_data_types.html

        If tabular data is returned, this keyword tries to return it as
        a table (see ``RPA.Tables``), if ``RPA.Tables`` is not available
        in the keyword's scope, the data will be returned as a list of dictionaries.
        Other types of data (SQL errors and result statements) are returned
        as strings.

        **NOTE:** You may modify the max built-in wait time by providing
        a timeout in seconds (default 40 seconds)

        **Robot framework example:**

        .. code-block:: robotframework

            *** Tasks ***

                ${SQL}=    Set variable    insert into mytable values (:id, :address)
                ${params}=    Create redshift statement parameters
                ...    id=1
                ...    address=Seattle
                ${response}=    Execute redshift statement    ${SQL}    ${params}
                Log    ${response}

        **Python example:**

        .. code-block:: python

            sql = "insert into mytable values (:id, :address)"
            parameters = [
                {"name": "id", "value": "1"},
                {"name": "address", "value": "Seattle"},
            ]
            response = aws.execute_redshift_statement(sql, parameters)
            print(response)

        :param parameters: The parameters for the SQL statement. Must consist
            of a list of dictionaries with two keys: ``name`` and ``value``.
        :param sql: The SQL statement text to run.
        :param statement_name: The name of the SQL statement. You can name
            the SQL statement when you create it to identify the query.
        :param with_event: A value that indicates whether to send an event
            to the Amazon EventBridge event bus after the SQL statement runs.
        :param timeout: Used to calculate the maximum wait. Exact timing
            depends on system variability becuase the underlying waiter
            does not utilize a timeout directly.

        """  # noqa: W605, E501
        client = self._get_client_for_service("redshift-data")
        run_token = self._submit_statement(
            client, sql, parameters, statement_name, with_event
        )
        statement_name_string = f" with name {statement_name}" if statement_name else ""
        self.logger.info(
            f"'{run_token['Id']}' SQL statement execution on Redshift started"
            f"{statement_name_string}:\n{sql}"
        )
        self.logger.info(f"Parameters used in SQL statement:\n{parameters}")
        return self.get_redshift_statement_results(run_token["Id"], timeout)

    @aws_dependency_required
    def execute_redshift_statement_asyncronously(
        self,
        sql: str,
        parameters: Optional[list] = None,
        statement_name: Optional[str] = None,
        with_event: bool = False,
    ) -> str:
        """Submit a sql statement for Redshift to execute asyncronously.
        Returns the statement ID which can be used to retrieve statement
        results later.

        :param parameters: The parameters for the SQL statement. Must consist
            of a list of dictionaries with two keys: ``name`` and ``value``.
        :param sql: The SQL statement text to run.
        :param statement_name: The name of the SQL statement. You can name
            the SQL statement when you create it to identify the query.
        :param with_event: A value that indicates whether to send an event
            to the Amazon EventBridge event bus after the SQL statement runs.

        """
        client = self._get_client_for_service("redshift-data")
        run_token = self._submit_statement(
            client, sql, parameters, statement_name, with_event
        )
        self.logger.info(
            f"'{run_token['Id']}' SQL statement submitted to Redshift"
            f"{' with name ' + statement_name if statement_name else ''}:\n{sql}"
        )
        self.logger.info(f"Parameters used in SQL statement:\n{parameters}")
        return run_token["Id"]

    def _submit_statement(
        self,
        redshift_data_client,
        sql: str,
        parameters: Optional[list] = None,
        statement_name: Optional[str] = None,
        with_event: bool = False,
    ) -> Dict:
        """Submits SQL to the provided client and returns run token"""
        additional_params = self._create_auth_params()
        if parameters:
            additional_params["Parameters"] = parameters
        if statement_name:
            additional_params["StatementName"] = statement_name
        return redshift_data_client.execute_statement(
            Sql=sql,
            WithEvent=with_event,
            **additional_params,
        )

    @aws_dependency_required
    def get_redshift_statement_results(
        self, statement_id: str, timeout: int = 40
    ) -> Union[SqlTable, int]:
        r"""Retrieve the results of a SQL statement previously submitted
        to Redshift. If that statement has not yet completed, this keyword
        will wait for results. See \`Execute Redshift Statement\` for
        additional information.

        If the statement has tabular results, this keyword returns them
        as a table from ``RPA.Tables`` if that library is available, or
        as a list of dictionaries if not. If the statement does not have
        tabular results, it will return the number of rows affected.

        :param statement_id: The statement id to use to retreive results.
        :param timeout: An integer used to calculate the maximum wait.
            Exact timing depends on system variability becuase the
            underlying waiter does not utilize a timeout directly.
            Defaults to 40.
        """
        client = self._get_client_for_service("redshift-data")
        try:
            statement_waiter = self._create_waiter_for_results(
                client, delay=2, max_attempts=int(timeout / 2)
            )
            statement_waiter.wait(Id=statement_id)
        except WaiterError as e:
            error_message = (
                e.last_response.get("Error", "No error details available")
                if hasattr(e.last_response, "get")
                else "Unknown error"
            )
            query_string = (
                e.last_response.get("QueryString", "No query details available")
                if hasattr(e.last_response, "get")
                else "None"
            )
            raise RedshiftDatabaseError(
                f"While waiting for the statement to finish executing, "
                f"an error was encountered: \n{error_message}"
                f'\n\nFor statement: \n"{query_string}"'
            ) from e

        finished_statement = client.describe_statement(Id=statement_id)
        self.logger.info(
            "Statement finished, total rows affected: "
            + str(finished_statement.get("ResultRows", "NONE"))
        )
        if finished_statement["HasResultSet"]:
            paginator = client.get_paginator("get_statement_result")
            full_result = paginator.paginate(Id=statement_id).build_full_result()

            tables = import_tables()
            if not tables:
                self.logger.info(
                    "Tables in the AWS response will be in a `dictionary` type, "
                    "because `RPA.Tables` library is not available in the scope."
                )
            column_names = [
                m.get("name") for m in full_result.get("ColumnMetadata", {})
            ]
            data = [
                {c: self._parse_tagged_union(f) for c, f in zip(column_names, row)}
                for row in full_result.get("Records", [])
            ]
            return tables().create_table(data) if tables else data
        else:
            return finished_statement.get("ResultRows", 0)

    def create_redshift_statement_parameters(self, **params) -> List[Dict[str, str]]:
        r"""Returns a formatted dictionary to be used in
        Redshift Data Api SQL statements.

        **Example:**

        Assume the ``${SQL}`` statement has the parameters ``:id`` and
        ``:name``:

        .. code-block:: robotframework

            *** Tasks ***

            ${params}=    Create sql parameters    id=123    name=Nokia
            # params produces a data structure like so:
            #   [
            #        {"name":"id", "value":"123"},
            #        {"name":"name", "value":"Nokia"}
            #    ]

            # Which can be used for the 'parameters' argument.
            ${response}=    Execute redshift statement    ${SQL}    ${params}
        """
        return [{"name": k, "value": v} for (k, v) in params.items()]

    def _parse_tagged_union(self, tagged_union: dict):
        TAGGED_TYPES = {
            "blobValue": bytes,
            "booleanValue": bool,
            "doubleValue": float,
            "isNull": lambda a: None,
            "longValue": int,
            "stringValue": str,
            "SDK_UNKNOWN_MEMBER": lambda a: "UNKNOWN_DATA_MEMBER",
        }
        for item_key, item_value in tagged_union.items():
            try:
                output = TAGGED_TYPES[item_key](item_value)
            except KeyError:
                output = "UNKNOWN_DATA_MEMBER"
        return output

    def _create_waiter_for_results(
        self,
        redshift_data_client,
        delay: int = 2,
        max_attempts: int = 20,
    ) -> Waiter:
        waiter_name = "StatementFinished"
        waiter_config = {
            "version": 2,
            "waiters": {
                waiter_name: {
                    "operation": "DescribeStatement",
                    "delay": delay,
                    "maxAttempts": max_attempts,
                    "acceptors": [
                        {
                            "matcher": "path",
                            "expected": "ABORTED",
                            "argument": "Status",
                            "state": "failure",
                        },
                        {
                            "matcher": "path",
                            "expected": "FAILED",
                            "argument": "Status",
                            "state": "failure",
                        },
                        {
                            "matcher": "path",
                            "expected": "SUBMITTED",
                            "argument": "Status",
                            "state": "retry",
                        },
                        {
                            "matcher": "path",
                            "expected": "PICKED",
                            "argument": "Status",
                            "state": "retry",
                        },
                        {
                            "matcher": "path",
                            "expected": "STARTED",
                            "argument": "Status",
                            "state": "retry",
                        },
                        {
                            "matcher": "path",
                            "expected": "FINISHED",
                            "argument": "Status",
                            "state": "success",
                        },
                    ],
                }
            },
        }
        return create_waiter_with_client(
            waiter_name, WaiterModel(waiter_config), redshift_data_client
        )

    @aws_dependency_required
    def describe_redshift_table(
        self, database: str, schema: Optional[str] = None, table: Optional[str] = None
    ) -> Union[Dict, List[Dict]]:
        """Describes the detailed information about a table from metadata
        in the cluster. The information includes its columns.

        If ``schema`` and/or ``table`` is not provided, the API searches
        all schemas for the provided table, or returns all tables in the
        schema or entire database.

        The response object is provided as a list of table meta data objects,
        utilize dot-notation or the ``RPA.JSON`` library to access members:

        .. code-block:: json

            {
                "ColumnList": [
                    {
                        "columnDefault": "string",
                        "isCaseSensitive": true,
                        "isCurrency": false,
                        "isSigned": false,
                        "label": "string",
                        "length": 123,
                        "name": "string",
                        "nullable": 123,
                        "precision": 123,
                        "scale": 123,
                        "schemaName": "string",
                        "tableName": "string",
                        "typeName": "string"
                    },
                ],
                "TableName": "string"
            }

        :param database: The name of the database that contains the tables
            to be described. If ommitted, will use the connected Database.
        :param schema: The schema that contains the table. If no schema
            is specified, then matching tables for all schemas are returned.
        :param table: The table name. If no table is specified, then all
            tables for all matching schemas are returned. If no table and
            no schema is specified, then all tables for all schemas in the
            database are returned
        """
        client = self._get_client_for_service("redshift-data")
        additional_params = self._create_auth_params(database)
        if schema:
            additional_params["Schema"] = schema
        if table:
            additional_params["Table"] = table
        paginator = client.get_paginator("describe_table")
        return paginator.paginate(**additional_params).build_full_result()

    @aws_dependency_required
    def list_redshift_tables(
        self,
        database: Optional[str] = None,
        schema_pattern: Optional[str] = None,
        table_pattern: Optional[str] = None,
    ) -> List[Dict]:
        """List the tables in a database. If neither ``schema_pattern`` nor
        ``table_pattern`` are specified, then all tables in the database
        are returned.

        Returned objects are structured like the below JSON in a list:

        .. code-block:: json

            {
                "name": "string",
                "schema": "string",
                "type": "string"
            }

        :param database: The name of the database that contains the tables
            to be described. If ommitted, will use the connected Database.
        :param schema_pattern: A pattern to filter results by schema name.
            Within a schema pattern, "%" means match any substring of 0
            or more characters and "_" means match any one character.
            Only schema name entries matching the search pattern are returned.
            If ``schema_pattern`` is not specified, then all tables that match
            ``table_pattern`` are returned. If neither ``schema_pattern``
            or ``table_pattern`` are specified, then all tables are returned.
        :param table_pattern: A pattern to filter results by table name.
            Within a table pattern, "%" means match any substring of 0 or
            more characters and "_" means match any one character. Only
            table name entries matching the search pattern are returned.
            If ``table_pattern`` is not specified, then all tables that
            match ``schema_pattern`` are returned. If neither ``schema_pattern`` or
            ``table_pattern`` are specified, then all tables are returned.
        """
        client = self._get_client_for_service("redshift-data")
        additional_params = self._create_auth_params(database)
        if schema_pattern:
            additional_params["SchemaPattern"] = schema_pattern
        if table_pattern:
            additional_params["TablePattern"] = table_pattern
        paginator = client.get_paginator("list_tables")
        return paginator.paginate(**additional_params).build_full_result()["Tables"]

    @aws_dependency_required
    def list_redshift_databases(
        self,
    ) -> List[str]:
        """List the databases in a cluster.

        Database names are returned as a list of strings.
        """
        client = self._get_client_for_service("redshift-data")
        additional_params = self._create_auth_params()
        paginator = client.get_paginator("list_databases")
        return paginator.paginate(**additional_params).build_full_result()["Databases"]

    @aws_dependency_required
    def list_redshift_schemas(
        self,
        database: Optional[str] = None,
        schema_pattern: Optional[str] = None,
    ) -> List[Dict]:
        """Lists the schemas in a database.

        Schema names are returned as a list of strings.

        :param database: The name of the database that contains the schemas
            to list. If ommitted, will use the connected Database.
        :param schema_pattern: A pattern to filter results by schema name.
            Within a schema pattern, "%" means match any substring of 0
            or more characters and "_" means match any one character.
            Only schema name entries matching the search pattern are returned.
            If ``schema_pattern`` is not specified, then all schemas are returned.
        """
        client = self._get_client_for_service("redshift-data")
        additional_params = self._create_auth_params(database)
        if schema_pattern:
            additional_params["SchemaPattern"] = schema_pattern
        paginator = client.get_paginator("list_schemas")
        return paginator.paginate(**additional_params).build_full_result()["Schemas"]

    def _create_auth_params(self, alternate_database: Optional[str] = None) -> Dict:
        """Generates a dictionary of authentication params depending
        on which method was defined when initializing this class. It should
        be called before adding call-specific parameters. If an alternate
        database name is provided, this function checks if it matches the
        configured database name, and if it does not, adds the params
        `ConnectedDatabase` and `Database`, otherwise it only adds `Database`.
        """
        auth_params = {}
        if self.cluster_identifier:
            auth_params["ClusterIdentifier"] = self.cluster_identifier
        if self.secret_arn:
            auth_params["SecretArn"] = self.secret_arn
        elif self.database_user:
            auth_params["DbUser"] = self.database_user
        if alternate_database == self.database or not alternate_database:
            auth_params["Database"] = self.database
        else:
            auth_params["ConnectedDatabase"] = self.database
            auth_params["Database"] = alternate_database
        return auth_params


class ServiceSTS(AWSBase):
    """Class for AWS STS Service."""

    def __init__(self) -> None:
        self.services.append("sts")
        self.logger.debug("ServiceSts init")

    def init_sts_client(
        self,
        aws_key_id: Optional[str] = None,
        aws_key: Optional[str] = None,
        region: Optional[str] = None,
        use_robocorp_vault: bool = False,
        session_token: Optional[str] = None,
    ) -> None:
        """Initialize AWS STS client.

        :param aws_key_id: access key ID
        :param aws_key: secret access key
        :param region: AWS region
        :param use_robocorp_vault: use secret stored in `Robocorp Vault`
        :param session_token: a session token associated with temporary
            credentials, such as from ``Assume Role``.
        """
        self._init_client(
            "sts", aws_key_id, aws_key, region, use_robocorp_vault, session_token
        )

    @aws_dependency_required
    def assume_role(
        self,
        role_arn: str,
        role_session_name: str,
        policy_arns: Optional[List[Dict]] = None,
        policy: Optional[str] = None,
        duration: int = 900,
        tags: Optional[List[Dict]] = None,
        transitive_tag_keys: Optional[List[str]] = None,
        external_id: Optional[str] = None,
        serial_number: Optional[str] = None,
        token_code: Optional[str] = None,
        source_identity: Optional[str] = None,
    ) -> Dict:
        """Returns a set of temporary security credentials that you can
        use to access Amazon Web Services resources that you might not
        normally have access to. These temporary credentials consist of
        an access key ID, a secret access key, and a security token.
        Typically, you use ``Assume Role`` within your account or for
        cross-account access.

        The credentials are returned as a dictionary with data structure
        similar to the following JSON:

        .. code-block:: json

            {
                "Credentials": {
                    "AccessKeyId": "string",
                    "SecretAccessKey": "string",
                    "SessionToken": "string",
                    "Expiration": "2015-01-01"
                },
                "AssumedRoleUser": {
                    "AssumedRoleId": "string",
                    "Arn": "string"
                },
                "PackedPolicySize": 123,
                "SourceIdentity": "string"
            }

        These credentials can be used to re-initialize services available
        in this library with the assumed role instead of the original
        role.

        **NOTE**: For detailed information on the available arguments to this
        keyword, please see the `Boto3 STS documentation`_.

        .. _Boto3 STS documentation: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts.html

        :param role_arn: The Amazon Resource Name (ARN) of the role to assume.
        :param role_session_name: An identifier for the assumed role session.
        :param policy_arns: The Amazon Resource Names (ARNs) of the IAM
            managed policies that you want to use as managed session policies.
            The policies must exist in the same account as the role.
        :param policy: An IAM policy in JSON format that you want to use
            as an inline session policy.
        :param duration: The duration, in seconds, of the role session.
            The value specified can range from 900 seconds (15 minutes
            and the default) up to the maximum session duration set for
            the role.
        :param tags: A list of session tags that you want to pass. Each
            session tag consists of a key name and an associated value.
        :param transitive_tag_keys: A list of keys for session tags that
            you want to set as transitive. If you set a tag key as
            transitive, the corresponding key and value passes to
            subsequent sessions in a role chain.
        :param external_id: A unique identifier that might be required
            when you assume a role in another account. If the
            administrator of the account to which the role belongs
            provided you with an external ID, then provide that value in
            this parameter.
        :param serial_number: The identification number of the MFA device
            that is associated with the user who is making the
            using the ``assume_role`` keyword.
        :param token_code: The value provided by the MFA device, if the
            trust policy of the role being assumed requires MFA.
        :param source_identity: The source identity specified by the
            principal that is using the ``assume_role`` keyword.
        """  # noqa: E501
        other_params = {
            "PolicyArns": policy_arns,
            "Policy": policy,
            "DurationSeconds": duration if duration > 900 else 900,
            "Tags": tags,
            "TransitiveTagKeys": transitive_tag_keys,
            "ExternalId": external_id,
            "SerialNumber": serial_number,
            "TokenCode": token_code,
            "SourceIdentity": source_identity,
        }
        other_params = {k: v for k, v in other_params.items() if v}
        client = self._get_client_for_service("sts")
        return client.assume_role(
            RoleArn=role_arn, RoleSessionName=role_session_name, **other_params
        )


class AWS(
    ServiceS3,
    ServiceTextract,
    ServiceComprehend,
    ServiceSQS,
    ServiceRedshiftData,
    ServiceSTS,
):
    """`AWS` is a library for operating with Amazon AWS services S3, SQS,
    Textract and Comprehend.

    Services are initialized with keywords like ``Init S3 Client`` for S3.

    **AWS authentication**

    Authentication for AWS is set with `key id` and `access key` which can be given to the library
    in three different ways.

    - Method 1 as environment variables, ``AWS_KEY_ID`` and ``AWS_KEY``.
    - Method 2 as keyword parameters to ``Init Textract Client`` for example.
    - Method 3 as Robocorp vault secret. The vault name needs to be given in library init or
      with keyword ``Set Robocorp Vault``. Secret keys are expected to match environment variable
      names.

    **Note.** Starting from `rpaframework-aws` **1.0.3** `region` can be given as environment
    variable ``AWS_REGION`` or include as Robocorp Vault secret with the same key name.

    **Redshift Data authentication:** Depending on the authorization method, use
    one of the following combinations of request parameters, which can only
    be passed via method 2:

        * Secrets Manager - when connecting to a cluster, specify the Amazon
          Resource Name (ARN) of the secret, the database name, and the
          cluster identifier that matches the cluster in the secret. When
          connecting to a serverless endpoint, specify the Amazon Resource
          Name (ARN) of the secret and the database name.
        * Temporary credentials - when connecting to a cluster, specify the
          cluster identifier, the database name, and the database user name.
          Also, permission to call the ``redshift:GetClusterCredentials``
          operation is required. When connecting to a serverless endpoint,
          specify the database name.

    **Role Assumption:** With the use of the STS service client, you are able
    to assume another role, which will return temporary credentials. The
    temporary credentials will include an access key and session token, see
    keyword documentation for ``Assume Role`` for details of how the
    credentials are returned. You can use these temporary credentials
    as part of method 2, but you must also include the session token.

    Method 1. credentials using environment variable

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.AWS

        *** Tasks ***
        Init AWS services
            # NO parameters for client, expecting to get credentials
            # with AWS_KEY, AWS_KEY_ID and AWS_REGION environment variables
            Init S3 Client

    Method 2. credentials with keyword parameter

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.AWS   region=us-east-1

        *** Tasks ***
        Init AWS services
            Init S3 Client  aws_key_id=${AWS_KEY_ID}  aws_key=${AWS_KEY}

    Method 3. setting Robocorp Vault in the library init

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.AWS  robocorp_vault_name=aws

        *** Tasks ***
        Init AWS services
            Init S3 Client  use_robocorp_vault=${TRUE}

    Method 3. setting Robocorp Vault with keyword

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.AWS

        *** Tasks ***
        Init AWS services
            Set Robocorp Vault     vault_name=aws
            Init Textract Client    use_robocorp_vault=${TRUE}

    **Requirements**

    The default installation depends on `boto3`_ library. Due to the size of the
    dependency, this library is available separate package ``rpaframework-aws`` but can
    also be installed as an optional package for ``rpaframework``.

    Recommended installation is `rpaframework-aws` plus `rpaframework` package.
    Remember to check latest versions from `rpaframework Github repository`_.

    .. code-block:: yaml

        channels:
          - conda-forge
        dependencies:
          - python=3.7.5
          - pip=20.1
          - pip:
            - rpaframework==13.0.2
            - rpaframework-aws==1.0.3

    Following declaration, `rpaframework[aws]`, will install all rpaframework libraries
    plus `RPA.Cloud.AWS` as an optional package. The extras support is deprecated and will be
    removed in the future major release of `rpaframework`.

    .. code-block:: yaml

        channels:
          - conda-forge
        dependencies:
          - python=3.7.5
          - pip=20.1
          - pip:
            - rpaframework[aws]==13.0.2

    .. _boto3:
        https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
    .. _rpaframework Github repository:
        https://github.com/robocorp/rpaframework

    **Example**

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.AWS   region=us-east-1

        *** Variables ***
        ${BUCKET_NAME}        testbucket12213123123

        *** Tasks ***
        Upload a file into S3 bucket
            [Setup]   Init S3 Client
            Upload File      ${BUCKET_NAME}   ${/}path${/}to${/}file.pdf
            @{files}         List Files   ${BUCKET_NAME}
            FOR   ${file}  IN   @{files}
                Log  ${file}
            END
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(
        self, region: str = DEFAULT_REGION, robocorp_vault_name: Optional[str] = None
    ):
        self.set_robocorp_vault(robocorp_vault_name)
        self.logger = logging.getLogger(__name__)
        super().__init__()
        self.region = region
        listener = RobotLogListener()
        listener.register_protected_keywords(
            [f"init_{s}_client" for s in self.services]
        )
        listener.only_info_level(["list_files"])
        self.logger.info("AWS library initialized. Using region %s", self.region)
