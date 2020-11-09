from collections import OrderedDict
import json
import logging
from functools import wraps
from pathlib import Path
from typing import Any

try:
    import boto3
    from botocore.exceptions import ClientError
    from boto3.exceptions import S3UploadFailedError

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

from RPA.Robocloud.Secrets import Secrets
from RPA.RobotLogListener import RobotLogListener
from RPA.Tables import Tables
from RPA.core.helpers import required_param, required_env


try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass

DEFAULT_REGION = "eu-west-1"


def aws_dependency_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not HAS_BOTO3:
            raise ValueError(
                "Please install optional `aws` package, "
                "`pip install rpaframework[aws]` to use RPA.Cloud.AWS library"
            )
        return f(*args, **kwargs)

    return wrapper


class AWSBase:
    """AWS base class for generic methods"""

    logger = None
    services: list = []
    clients: dict = {}
    region: str = None
    robocloud_vault_name: str = None

    def _get_client_for_service(self, service_name: str = None):
        """Return client instance for servive if it has been initialized.

        :param service_name: name of the AWS service
        :return: client instance
        """
        if service_name not in self.clients.keys():
            raise KeyError(
                "AWS service %s has not been initialized" % service_name.upper()
            )
        return self.clients[service_name]

    def _set_service(self, service_name: str = None, client: Any = None):
        self.clients[service_name] = client

    @aws_dependency_required
    def _init_client(
        self,
        service_name: str,
        aws_key_id: str = None,
        aws_key: str = None,
        region: str = None,
        use_robocloud_vault: bool = False,
    ):
        if region is None:
            region = self.region
        if use_robocloud_vault:
            vault = Secrets()
            vault_items = vault.get_secret(self.robocloud_vault_name)
            vault_items = {k.upper(): v for (k, v) in vault_items.items()}
            aws_key_id = vault_items["AWS_KEY_ID"]
            aws_key = vault_items["AWS_KEY"]
        else:
            if aws_key_id is None or aws_key_id.strip() == "":
                aws_key_id = required_env("AWS_KEY_ID")
            if aws_key is None or aws_key.strip() == "":
                aws_key = required_env("AWS_KEY")
        if (
            aws_key_id is None
            or aws_key_id.strip() == ""
            or aws_key is None
            or aws_key.strip() == ""
        ):
            raise KeyError(
                "AWS key ID and secret access key are required "
                " to use AWS cloud service: %s" % service_name
            )
        client = boto3.client(
            service_name,
            region_name=region,
            aws_access_key_id=aws_key_id,
            aws_secret_access_key=aws_key,
        )
        self._set_service(service_name, client)

    def set_robocloud_vault(self, vault_name):
        """Set Robocloud Vault name

        :param vault_name: Robocloud Vault name
        """
        if vault_name:
            self.robocloud_vault_name = vault_name


class ServiceS3(AWSBase):
    """Class for AWS S3 service"""

    def __init__(self) -> None:
        self.services.append("s3")
        self.logger.debug("ServiceS3 init")

    def init_s3_client(
        self,
        aws_key_id: str = None,
        aws_key: str = None,
        region: str = None,
        use_robocloud_vault: bool = False,
    ) -> None:
        """Initialize AWS S3 client

        :param aws_key_id: access key ID
        :param aws_key: secret access key
        :param region: AWS region
        :param use_robocloud_vault: use secret stored into `Robocloud Vault`
        """
        self._init_client("s3", aws_key_id, aws_key, region, use_robocloud_vault)

    @aws_dependency_required
    def create_bucket(self, bucket_name: str = None) -> bool:
        """Create S3 bucket with name

        :param bucket_name: name for the bucket
        :return: boolean indicating status of operation
        """
        required_param(bucket_name, "create_bucket")
        client = self._get_client_for_service("s3")
        try:
            response = client.create_bucket(Bucket=bucket_name)
            return response["ResponseMetadata"]["HTTPStatusCode"] == 204
        except ClientError as e:
            self.logger.error(e)
            return False

    @aws_dependency_required
    def delete_bucket(self, bucket_name: str = None) -> bool:
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
    def delete_files(self, bucket_name: str = None, files: list = None):
        """Delete files in the bucket

        :param bucket_name: name for the bucket
        :param files: list of files to delete
        :return: number of files deleted or `False`
        """
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
            response = client.delete_objects(Bucket=bucket_name, Delete=objects)
            return len(response["Deleted"]) if "Deleted" in response else 0
        except ClientError as e:
            self.logger.error(e)
            return False

    @aws_dependency_required
    def list_files(self, bucket_name) -> list:
        """List files in the bucket

        :param bucket_name: name for the bucket
        :return: list of files
        """
        required_param(bucket_name, "list_files")
        client = self._get_client_for_service("s3")
        files = []
        try:
            response = client.list_objects_v2(Bucket=bucket_name)
            files = response["Contents"] if "Contents" in response else []
        except ClientError as e:
            self.logger.error(e)
        return files

    @aws_dependency_required
    def _s3_upload_file(self, bucket_name, filename, object_name):
        client = self._get_client_for_service("s3")
        uploaded = False
        error = None
        try:
            client.upload_file(filename, bucket_name, object_name)
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
        self, bucket_name: str = None, filename: str = None, object_name: str = None
    ) -> tuple:
        """Upload single file into bucket

        :param bucket_name: name for the bucket
        :param filename: filepath for the file to be uploaded
        :param object_name: name of the object in the bucket, defaults to None
        :return: tuple of upload status and error

        If `object_name` is not given then basename of the file is
        used as `object_name`.
        """
        required_param([bucket_name, filename], "upload_file")
        if object_name is None:
            object_name = Path(filename).name
        return self._s3_upload_file(bucket_name, filename, object_name)

    @aws_dependency_required
    def upload_files(self, bucket_name: str = None, files: list = None) -> list:
        """Upload multiple files into bucket

        :param bucket_name: name for the bucket
        :param files: list of files (2 possible ways, see above)
        :return: number of files uploaded

        Giving files as list of filepaths:
            ['/path/to/file1.txt', '/path/to/file2.txt']

        Giving files as list of dictionaries (including filepath and object name):
            [{'filepath':'/path/to/file1.txt', 'object_name': 'file1.txt'},
            {'filepath': '/path/to/file2.txt', 'object_name': 'file2.txt'}]
        """
        required_param([bucket_name, files], "upload_files")
        upload_count = 0
        for _, item in enumerate(files):
            filepath = None
            object_name = None
            if isinstance(item, dict):
                filepath = item["filepath"]
                object_name = item["object_name"]
            elif isinstance(item, str):
                filepath = item
                object_name = Path(item).name
            else:
                error = "incorrect input format for files"

            if filepath and object_name:
                uploaded, error = self._s3_upload_file(
                    bucket_name, filepath, object_name
                )
                if uploaded:
                    upload_count += 1
            if error:
                self.logger.warning("File upload failed with error: %s", error)
        return upload_count

    @aws_dependency_required
    def download_files(
        self, bucket_name: str = None, files: list = None, target_directory: str = None
    ) -> list:
        """Download files from bucket to local filesystem

        :param bucket_name: name for the bucket
        :param files: list of S3 object names
        :param target_directory: location for the downloaded files, default
            current directory
        :return: number of files downloaded
        """
        required_param([bucket_name, files, target_directory], "download_files")
        client = self._get_client_for_service("s3")
        download_count = 0

        for _, object_name in enumerate(files):
            try:
                download_path = str(Path(target_directory) / object_name)
                response = client.download_file(bucket_name, object_name, download_path)
                if response is None:
                    download_count += 1
            except ClientError as e:
                self.logger.error("Download error with '%s': %s", object_name, str(e))

        return download_count


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
        aws_key_id: str = None,
        aws_key: str = None,
        region: str = None,
        use_robocloud_vault: bool = False,
    ):
        """Initialize AWS Textract client

        :param aws_key_id: access key ID
        :param aws_key: secret access key
        :param region: AWS region
        :param use_robocloud_vault: use secret stored into `Robocloud Vault`
        """
        self._init_client("textract", aws_key_id, aws_key, region, use_robocloud_vault)

    @aws_dependency_required
    def analyze_document(
        self, image_file: str = None, json_file: str = None, bucket_name: str = None
    ) -> bool:
        """Analyzes an input document for relationships between detected items

        :param image_file: filepath (or object name) of image file
        :param json_file: filepath to resulting json file
        :param bucket_name: if given then using `image_file` from the bucket
        :return: analysis response in json
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
            with open(json_file, "w") as f:
                json.dump(response, f)
        return response

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

            tables = Tables()
            data = [
                [rows[col][idx] for idx in sorted(rows[col])] for col in sorted(rows)
            ]
            table = tables.create_table(data)
            self.tables[idx] = table

    def get_tables(self):
        """[summary]

        :return: [description]
        """
        return self.tables

    def get_words(self):
        """[summary]

        :return: [description]
        """
        return self.words

    def get_cells(self):
        """[summary]

        :return: [description]
        """
        return self.cells

    @aws_dependency_required
    def detect_document_text(
        self, image_file: str = None, json_file: str = None, bucket_name: str = None
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
            with open(json_file, "w") as f:
                json.dump(response, f)
        return response

    @aws_dependency_required
    def start_document_analysis(
        self,
        bucket_name_in: str = None,
        object_name_in: str = None,
        object_version_in: str = None,
        bucket_name_out: str = None,
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
        self, job_id: str = None, max_results: int = 1000, next_token: str = None
    ) -> dict:
        """Get the results of Textract asynchronous `Document Analysis` operation

        :param job_id: job identifier, defaults to None
        :param max_results: number of blocks to get at a time, defaults to 1000
        :param next_token: pagination token for getting next set of results,
               defaults to None
        :return: dictionary

        Response dictionary has key `JobStatus` with value `SUCCEEDED` when analysis
        has been completed.

        Example:

        .. code-block:: robotframework

            Init Textract Client  %{AWS_KEY_ID}  %{AWS_KEY_SECRET}  %{AWS_REGION}
            ${jobid}=    Start Document Analysis  s3bucket_name  invoice.pdf
            FOR    ${i}    IN RANGE    50
                ${response}    Get Document Analysis  ${jobid}
                Exit For Loop If    "${response}[JobStatus]" == "SUCCEEDED"
                Sleep    1s
            END
        """
        client = self._get_client_for_service("textract")
        method_arguments = {"JobId": job_id, "MaxResults": max_results}
        if next_token:
            method_arguments["NextToken"] = next_token

        response = client.get_document_analysis(**method_arguments)
        return response

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
        bucket_name_in: str = None,
        object_name_in: str = None,
        object_version_in: str = None,
        bucket_name_out: str = None,
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
        self, job_id: str = None, max_results: int = 1000, next_token: str = None
    ) -> dict:
        """Get the results of Textract asynchronous `Document Text Detection` operation

        :param job_id: job identifier, defaults to None
        :param max_results: number of blocks to get at a time, defaults to 1000
        :param next_token: pagination token for getting next set of results,
               defaults to None
        :return: dictionary

        Response dictionary has key `JobStatus` with value `SUCCEEDED` when analysis
        has been completed.

        Example:

        .. code-block:: robotframework

            Init Textract Client  %{AWS_KEY_ID}  %{AWS_KEY_SECRET}  %{AWS_REGION}
            ${jobid}=    Start Document Text Detection  s3bucket_name  invoice.pdf
            FOR    ${i}    IN RANGE    50
                ${response}    Get Document Text Detection    ${jobid}
                Exit For Loop If    "${response}[JobStatus]" == "SUCCEEDED"
                Sleep    1s
            END
        """
        client = self._get_client_for_service("textract")
        method_arguments = {"JobId": job_id, "MaxResults": max_results}
        if next_token:
            method_arguments["NextToken"] = next_token

        response = client.get_document_text_detection(**method_arguments)
        return response


class ServiceComprehend(AWSBase):
    """Class for AWS Comprehend service"""

    def __init__(self):
        self.services.append("comprehend")
        self.logger.debug("ServiceComprehend init")

    def init_comprehend_client(
        self,
        aws_key_id: str = None,
        aws_key: str = None,
        region: str = None,
        use_robocloud_vault: bool = False,
    ):
        """Initialize AWS Comprehend client

        :param aws_key_id: access key ID
        :param aws_key: secret access key
        :param region: AWS region
        :param use_robocloud_vault: use secret stored into `Robocloud Vault`
        """
        self._init_client(
            "comprehend", aws_key_id, aws_key, region, use_robocloud_vault
        )

    @aws_dependency_required
    def detect_sentiment(self, text: str = None, lang="en") -> dict:
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
    def detect_entities(self, text: str = None, lang="en") -> dict:
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
        aws_key_id: str = None,
        aws_key: str = None,
        region: str = None,
        queue_url: str = None,
        use_robocloud_vault: bool = False,
    ):
        """Initialize AWS SQS client

        :param aws_key_id: access key ID
        :param aws_key: secret access key
        :param region: AWS region
        :param queue_url: SQS queue url
        :param use_robocloud_vault: use secret stored into `Robocloud Vault`
        """
        self._init_client("sqs", aws_key_id, aws_key, region, use_robocloud_vault)
        self.queue_url = queue_url

    @aws_dependency_required
    def send_message(
        self, message: str = None, message_attributes: dict = None
    ) -> dict:
        """Send message to the queue

        :param message: body of the message
        :param message_attributes: attributes of the message
        :return: send message response as dict
        """
        required_param(message, "send_message")
        client = self._get_client_for_service("sqs")
        if message_attributes is None:
            message_attributes = dict()
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
    def delete_message(self, receipt_handle: str = None):
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
    def create_queue(self, queue_name: str = None):
        """Create queue with name

        :param queue_name: [description], defaults to None
        :return: create queue response as dict
        """
        required_param(queue_name, "create_queue")
        client = self._get_client_for_service("sqs")
        response = client.create_queue(queue_name)
        return response

    @aws_dependency_required
    def delete_queue(self, queue_name: str = None):
        """Delete queue with name

        :param queue_name: [description], defaults to None
        :return: delete queue response as dict
        """
        required_param(queue_name, "delete_queue")
        client = self._get_client_for_service("sqs")
        response = client.delete_queue(queue_name)
        return response


class AWS(ServiceS3, ServiceTextract, ServiceComprehend, ServiceSQS):
    """`AWS` is a library for operating with Amazon AWS services S3, SQS,
    Textract and Comprehend.

    Services are initialized with keywords like ``Init S3 Client`` for S3.

    **AWS authentication**

    Authentication for AWS is set with `key id` and `access key` which can be given to the library
    in three different ways.

    - Method 1 as environment variables, ``AWS_KEY_ID`` and ``AWS_KEY``.
    - Method 2 as keyword parameters to ``Init Textract Client`` for example.
    - Method 3 as Robocloud vault secret. The vault name needs to be given in library init or
      with keyword ``Set Robocloud Vault``. Secret keys are expected to match environment variable
      names.

    Method 1. credentials using environment variable

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.AWS

        *** Tasks ***
        Init AWS services
            # NO parameters for client, expecting to get credentials
            # with AWS_KEY and AWS_KEY_ID environment variable
            Init S3 Client

    Method 2. credentials with keyword parameter

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.AWS

        *** Tasks ***
        Init AWS services
            Init S3 Client  aws_key_id=${AWS_KEY_ID}  aws_key=${AWS_KEY}

    Method 3. setting Robocloud Vault in the library init

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.AWS  robocloud_vault_name=aws

        *** Tasks ***
        Init AWS services
            Init S3 Client  use_robocloud_vault=${TRUE}

    Method 3. setting Robocloud Vault with keyword

    .. code-block:: robotframework

        *** Settings ***
        Library   RPA.Cloud.AWS

        *** Tasks ***
        Init Azure services
            Set Robocloud Vault         vault_name=aws
            Init Textract Client  use_robocloud_vault=${TRUE}

    **Requirements**

    The default installation depends on `boto3`_ library. Due to the size of the
    dependency, this library has been set as an optional package for ``rpaframework``.

    This can be installed by opting in to the `aws` dependency:

    ``pip install rpaframework[aws]``

    .. _boto3:
        https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

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

    def __init__(self, region: str = DEFAULT_REGION, robocloud_vault_name: str = None):
        self.set_robocloud_vault(robocloud_vault_name)
        self.logger = logging.getLogger(__name__)
        ServiceS3.__init__(self)
        ServiceTextract.__init__(self)
        ServiceComprehend.__init__(self)
        ServiceSQS.__init__(self)
        self.region = region
        listener = RobotLogListener()
        listener.register_protected_keywords(
            [f"init_{s}_client" for s in self.services]
        )
        listener.only_info_level(["list_files"])
        self.logger.info("AWS library initialized. Using region %s", self.region)
