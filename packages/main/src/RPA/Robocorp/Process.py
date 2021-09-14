from enum import Enum
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Union, Any

from robot.api.deco import library, keyword
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

from RPA.HTTP import HTTP


class ConfigurationType(Enum):
    """Possible configuration types"""

    default = "default"
    workitems = "workItemIds"
    # storages is at the moment unsupported type by the API
    # storages = "storages"


def to_configuration_type(value):
    """Convert value to ConfigurationType enum."""
    if isinstance(value, ConfigurationType):
        return value

    sanitized = str(value).lower().strip().replace(" ", "_")
    try:
        return ConfigurationType[sanitized]
    except KeyError as err:
        raise ValueError(f"Unknown configuration type: {value}") from err


@library
class Process:
    """`Process` is a library for interacting with Robocorp public API endpoints."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(
        self,
        workspace_id: str = None,
        robocorp_api_key: str = None,
        process_id: str = None,
        **kwargs,
    ):
        """ """
        self.logger = logging.getLogger(__name__)

        self.robocorp_api_server = kwargs.pop(
            "robocorp_api_server", "https://api.eu1.robocorp.com/process-v1"
        )
        self.workspace_id = workspace_id
        self.robocorp_api_key = robocorp_api_key
        self.process_id = process_id
        self.http = HTTP()

        try:
            BuiltIn().import_library("RPA.RobotLogListener")
        except RobotNotRunningError:
            pass

    def set_workspace_id(self, workspace_id: str):
        self.workspace_id = workspace_id

    def set_process_id(self, process_id: str):
        self.process_id = process_id

    def set_apikey(self, apikey: str):
        self.robocorp_api_key = apikey

    @keyword(tags=["process", "set"])
    def set_credentials(self, workspace_id: str, process_id: str, apikey: str):
        self.set_workspace_id(workspace_id)
        self.set_process_id(process_id)
        self.set_apikey(apikey)

    @property
    def headers(self):
        return {"Authorization": f"RC-WSKEY {self.robocorp_api_key}"}

    @property
    def base_api(self):
        return f"{self.robocorp_api_server}/workspaces/{self.workspace_id}"

    def process_api(self, process_id: str = None):
        pid = process_id or self.process_id
        return f"{self.base_api}/processes/{pid}"

    def workspace_api(self, workspace_id: str = None):
        wid = workspace_id or self.workspace_id
        return f"{self.robocorp_api_server}/workspaces/{wid}"

    @keyword(tags=["process", "post", "workitems", "start"])
    def start_process(
        self,
        process_id: str = None,
        workitems: Union[Dict, List[Dict]] = None,
        batch: bool = False,
    ):
        endpoint = "runs-batch" if batch else "runs"
        response = self.http.session_less_post(
            url=f"{self.process_api(process_id)}/{endpoint}",
            headers=self.headers,
            json=workitems or [],
        )

        return response.json()

    @keyword(tags=["process", "post", "workitems", "start"])
    def start_configured_process(
        self,
        process_id: str = None,
        config_type: ConfigurationType = ConfigurationType.default,
        extra_info: Optional[List] = None,
    ):
        ctype = to_configuration_type(config_type)
        request_data = {"type": ctype.value}
        if ctype == ConfigurationType.workitems:
            request_data["workItemIds"] = extra_info
        # elif ctype == ConfigurationType.storages:
        #    request_data["storages"] = extra_info
        response = self.http.session_less_post(
            url=f"{self.process_api(process_id)}/run-request",
            headers=self.headers,
            data=json.dumps(request_data),
        )
        return response.text

    @keyword(tags=["process", "post", "workitems"])
    def create_input_work_item(
        self,
        process_id: str = None,
        payload: Any = None,
        files: Optional[Union[str, List]] = None,
    ):
        files = [files] if isinstance(files, str) else files or []
        response = self.http.session_less_post(
            url=f"{self.process_api(process_id)}/work-items",
            headers=self.headers,
            json={"payload": payload or {}},
        )
        response.raise_for_status()
        response_json = response.json()
        workitem_id = response_json["id"]
        for f in files:
            filepath = Path(f).absolute()
            filename = Path(f).name
            _, register_response = self.register_file_upload(
                filepath, filename, workitem_id
            )
            self.upload_file_to_s3(
                filepath,
                filename,
                register_response,
            )
        return workitem_id

    def register_file_upload(
        self,
        filepath: str,
        workitem_filename: str,
        workitem_id: str,
        process_id: str = None,
    ):
        upload_filesize = Path(filepath).stat().st_size
        response = self.http.session_less_post(
            url=f"{self.process_api(process_id)}/work-items/{workitem_id}/files/upload",
            headers=self.headers,
            data=json.dumps(
                {"fileName": workitem_filename, "fileSize": upload_filesize}
            ),
        )
        response.raise_for_status()
        return response.status_code, response.json()

    def upload_file_to_s3(self, filepath, workitem_filename, data):
        """Upload a file to an S3 bucket

        :param file_name: File to upload
        :param bucket: Bucket to upload to
        :param object_name: S3 object name. If not specified then file_name is used
        :return: True if file was uploaded, else False
        """

        # If S3 object_name was not specified, use file_name

        # Perform actual file upload
        with open(filepath, "rb") as infile:
            url = data["url"]
            fields = data["fields"]
            files = {"file": (workitem_filename, infile.read())}
            response = self.http.session_less_post(url, data=fields, files=files)
            response.raise_for_status()
            return response.status_code, response.text

    @keyword(tags=["process", "get"])
    def get_robot_artifact(
        self,
        run_id: str,
        artifact_id: str = None,
        filename: str = None,
        process_id: str = None,
    ):
        pass

    @keyword(tags=["process", "get"])
    def list_processes(self, workspace_id: str = None):
        response = self.http.session_less_get(
            url=f"{self.workspace_api(workspace_id)}/processes",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()["data"]

    @keyword(tags=["process", "get", "workitems"])
    def list_process_workitems(
        self, process_id: str = None, include_data: bool = False, item_state: str = None
    ):
        response = self.http.session_less_get(
            url=f"{self.process_api(process_id)}/work-items",
            headers=self.headers,
            params={"includeData": str(include_data).lower()},
        )
        response.raise_for_status()
        data = response.json()["data"]
        return (
            [d for d in data if d["state"].upper() == item_state.upper()]
            if item_state
            else data
        )

    @keyword(tags=["process", "get", "workitem"])
    def get_workitem(
        self, workitem_id: str, process_id: str = None, include_data: bool = False
    ):
        response = self.http.session_less_get(
            url=f"{self.process_api(process_id)}/work-items/{workitem_id}",
            headers=self.headers,
            params={"includeData": str(include_data).lower()},
        )
        response.raise_for_status()
        return response.json()

    @keyword(tags=["process", "get", "runs"])
    def list_process_runs(
        self, process_id: str = None, run_state: str = None, limit: int = 10
    ):
        response = self.http.session_less_get(
            url=f"{self.process_api(process_id)}/runs",
            headers=self.headers,
            params={"limit": limit},
        )
        response.raise_for_status()
        data = response.json()["data"]
        return (
            [d for d in data if d["state"].upper() == run_state.upper()]
            if run_state
            else data
        )

    @keyword(tags=["process", "get", "runs"])
    def list_process_runs_in_workspace(
        self, workspace_id: str = None, run_state: str = None, limit: int = 10
    ):
        response = self.http.session_less_get(
            url=f"{self.workspace_api(workspace_id)}/pruns",
            headers=self.headers,
            params={"limit": limit},
        )
        response.raise_for_status()
        data = response.json()
        return (
            [d for d in data if d["state"].upper() == run_state.upper()]
            if run_state
            else data
        )

    @keyword(tags=["process", "get"])
    def get_process_run_status(self, process_run_id: str, process_id: str = None):
        response = self.http.session_less_get(
            url=f"{self.process_api(process_id)}/runs/{process_run_id}",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()

    @keyword(tags=["process", "get"])
    def get_process_id_by_name(self, process_name: str, workspace_id: str = None):
        processes = self.list_processes(workspace_id)
        return next((p["id"] for p in processes if p["name"] == process_name), None)
