from enum import Enum
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List, Union, Any

from robot.api.deco import library, keyword
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

from RPA.HTTP import HTTP
from RPA.RobotLogListener import RobotLogListener

try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


class ConfigurationType(Enum):
    """Possible configuration types"""

    default = "default"
    work_items = "workItemIds"
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
    """A library for interacting with Control Room (CR) Process API endpoints.

    See https://robocorp.com/docs/control-room/operating-workforce for information
    about process run, step run and work item states.

    See https://robocorp.com/docs/control-room/apis-and-webhooks for information
    about Control Room APIs.

    **Examples**

    **Robot Framework**

    In the following example a task creates two input work items,
    and starts a process with those items. This results in 2 different
    process runs in the Control Room.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Robocorp.Process
        Library    RPA.Robocorp.Vault

        *** Keywords ***
        Initialize Process Library
            ${secrets}=  Get Secret  ProcessAPI
            Set Credentials
            ...   ${secrets}[workspace_id]
            ...   ${secrets}[process_id]
            ...   ${secrets}[apikey]

        *** Tasks ***
        Start process with work items
            [Setup]   Initialize Process Library
            &{item1}=  Create Dictionary  fname=Mark  lname=Monkey
            &{item2}=  Create Dictionary  fname=John  lname=Doe
            @{items}=  Create List  ${item1}   ${item2}
            Start Process  work_items=${items}  batch=True

    **Robot Framework**

    In the following example a task creates work item with files.
    To include files in a work item, the item needs to be created
    before starting the process (note. different start keyword than above).

    In this example I am using same keywords and settings from above example.

    .. code-block:: robotframework

        *** Tasks ***
        Start process with work items
            [Setup]   Initialize Process Library
            &{data}=  Create Dictionary  fname=Mark  lname=Monkey
            @{files}=  Create List
            ...   ${CURDIR}${/}workdata.xlsx
            ...   ${CURDIR}${/}other.csv
            ${item_id}=    Create Input Work Item
            ...   payload=${data}
            ...   files=${files}
            Start Configured Process
            ...  config_type=work_items
            ...  extra_info=${item_id}

    **Python**

    List work items in Control Room and retry failed items.

    .. code-block:: python

        from RPA.Robocorp.Process import Process
        from RPA.Robocorp.Vault import Vault

        secrets = Vault().get_secret("ProcessAPI")
        process = Process(
            secrets["workspace_id"],
            secrets["process_id"],
            secrets["apikey"]
        )


        def retry_failed_items():
            items = process.list_process_work_items()
            for item in items:
                if item["state"] == "FAILED":
                    print("FAILED work item: %s" % item["id"])
                    result = process.retry_work_item(item["id"])
                    print(result)

        if __name__ == "__main__":
            retry_failed_items()
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    # TODO. Add support for all Process API endpoints

    def __init__(
        self,
        workspace_id: str = None,
        process_id: str = None,
        workspace_api_key: str = None,
        **kwargs,
    ):
        self.workspace_id = None
        self.process_id = None
        self.workspace_api_key = None
        listener = RobotLogListener()
        listener.register_protected_keywords(
            [
                "RPA.Robocorp.Process.set_workspace_id",
                "RPA.Robocorp.Process.set_process_id",
                "RPA.Robocorp.Process.set_apikey",
                "RPA.Robocorp.Process.set_credentials",
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.robocorp_api_server = kwargs.pop(
            "robocorp_api_server", "https://api.eu1.robocorp.com/process-v1"
        )
        self.set_credentials(workspace_id, process_id, workspace_api_key)
        self.http = HTTP()

    @keyword(tags=["set"])
    def set_workspace_id(self, workspace_id: str = None):
        """Set Control Room workspace ID

        :param workspace_id: ID of the Control Room workspace
        """
        if workspace_id:
            self.workspace_id = workspace_id

    @keyword(tags=["set"])
    def set_process_id(self, process_id: str = None):
        """Set Control Room process ID

        :param process_id: ID of the Control Room process
        """
        if process_id:
            self.process_id = process_id

    @keyword(tags=["set"])
    def set_apikey(self, apikey: str = None):
        """Set Workspace API access key

        :param apikey: workspace API access key
        """
        if apikey:
            self.workspace_api_key = apikey

    @keyword(tags=["set"])
    def set_credentials(
        self, workspace_id: str = None, process_id: str = None, apikey: str = None
    ):
        """Set credentials needed by the Process API

        :param workspace_id: ID of the Control Room workspace
        :param process_id: ID of the Control Room process
        :param apikey: workspace API access key
        """
        self.set_workspace_id(workspace_id)
        self.set_process_id(process_id)
        self.set_apikey(apikey)

    @property
    def headers(self):
        return {"Authorization": f"RC-WSKEY {self.workspace_api_key}"}

    @property
    def base_api(self):
        return f"{self.robocorp_api_server}/workspaces/{self.workspace_id}"

    def process_api(self, process_id: str = None):
        pid = process_id or self.process_id
        return f"{self.base_api}/processes/{pid}"

    def workspace_api(self, workspace_id: str = None):
        wid = workspace_id or self.workspace_id
        return f"{self.robocorp_api_server}/workspaces/{wid}"

    @keyword(tags=["process", "post", "work item", "start"])
    def start_process(
        self,
        work_items: Union[Dict, List[Dict]] = None,
        batch: bool = False,
        process_id: str = None,
    ):
        """Start a Control Room process

        :param work_items: input work items for the process (default empty)
        :param batch: set to True if sending list of workitems to start each
         as a separate run
        :param process_id: specific process to start
        """
        endpoint = "runs-batch" if batch else "runs"
        response = self.http.session_less_post(
            url=f"{self.process_api(process_id)}/{endpoint}",
            headers=self.headers,
            json=work_items or [],
        )

        return response.json()

    @keyword(tags=["process", "post", "work item", "start"])
    def start_configured_process(
        self,
        config_type: ConfigurationType = ConfigurationType.default,
        extra_info: Optional[Union[str, List]] = None,
        process_id: str = None,
    ):
        """Start a Control Room process with the provided configuration

        :param config_type: type of the start, (ConfigurationType.default)
        :param extra_info: data to be sent with the start, for example. work item IDs
        :param process_id: specific process to start
        """
        ctype = to_configuration_type(config_type)
        request_data = {"type": ctype.value}
        if ctype == ConfigurationType.work_items:
            extra_info = (
                [extra_info] if isinstance(extra_info, str) else extra_info or []
            )
            request_data["workItemIds"] = extra_info
        # elif ctype == ConfigurationType.storages:
        #    request_data["storages"] = extra_info
        response = self.http.session_less_post(
            url=f"{self.process_api(process_id)}/run-request",
            headers=self.headers,
            data=json.dumps(request_data),
        )
        return response.text

    @keyword(tags=["process", "post", "work item"])
    def create_input_work_item(
        self,
        payload: Any = None,
        files: Optional[Union[str, List]] = None,
        process_id: str = None,
    ):
        """Create an input work item for a process

        :param payload: work item data
        :param files: absolute filepaths as single string or list
        :param process_id: specific process to which item belongs to
        """
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
        with open(filepath, "rb") as infile:
            url = data["url"]
            fields = data["fields"]
            files = {"file": (workitem_filename, infile.read())}
            response = self.http.session_less_post(url, data=fields, files=files)
            response.raise_for_status()
            return response.status_code, response.text

    @keyword(tags=["process", "get"])
    def list_processes(self, workspace_id: str = None):
        """List all processes in a workspace

        :param workspace_id: specific Control Room workspace to which process belongs to
        """
        response = self.http.session_less_get(
            url=f"{self.workspace_api(workspace_id)}/processes",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()["data"]

    @keyword(tags=["process", "get", "work item"])
    def list_process_work_items(
        self, process_id: str = None, include_data: bool = False, item_state: str = None
    ):
        """List work items belonging to a process

        :param include_data: include work item payload and files in
         the response (default False)
        :param item_state: state of work items to return (default all)
        :param process_id: specific process to which items belongs to
        """
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

    @keyword(tags=["process", "get", "work item"])
    def get_work_item(
        self, workitem_id: str, include_data: bool = False, process_id: str = None
    ):
        """Get work item from Control Room

        :param workitem_id: id of the work item
        :param include_data: include work item payload and files in
         the response (default False)
        :param process_id: specific process to which runs belongs to
        """
        response = self.http.session_less_get(
            url=f"{self.process_api(process_id)}/work-items/{workitem_id}",
            headers=self.headers,
            params={"includeData": str(include_data).lower()},
        )
        response.raise_for_status()
        return response.json()

    @keyword(tags=["process", "get", "runs"])
    def list_process_runs(
        self,
        run_state: Optional[str] = None,
        limit: Optional[int] = 10,
        process_id: Optional[str] = None,
    ):
        """List of runs related to a process

        :param run_state: state of runs to return (default all)
        :param limit: number of runs to return (default 10)
        :param process_id: specific process to which runs belongs to
        """
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
        self,
        run_state: Optional[str] = None,
        limit: Optional[int] = 10,
        workspace_id: Optional[str] = None,
    ):
        """List all process runs in a workspace

        :param run_state: state of runs to return (default all)
        :param limit: number of runs to return (default 10)
        :param workspace_id: specific Control Room workspace to which process belongs to
        """
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

    @keyword(tags=["process", "get", "runs"])
    def get_process_run_status(
        self, process_run_id: str, process_id: Optional[str] = None
    ):
        """Get a process run status by run id

        :param process_run_id: id of the process run
        :param process_id: specific process to which runs belongs to
        """
        response = self.http.session_less_get(
            url=f"{self.process_api(process_id)}/runs/{process_run_id}",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()

    @keyword(tags=["process", "get"])
    def get_process_id_by_name(
        self, process_name: str, workspace_id: Optional[str] = None
    ):
        """Get a process id of the process by name

        :param process_name: name of the process in the Control Room
        :param workspace_id: specific Control Room workspace to which process belongs to
        """
        processes = self.list_processes(workspace_id)
        return next((p["id"] for p in processes if p["name"] == process_name), None)

    @keyword(tags=["process", "post", "work item", "retry"])
    def retry_work_item(
        self,
        work_item_id: str,
        process_id: str = None,
    ):
        """Retry processing of work item in FAILED state

        :param work_item_id: ID of the work item to retry
        :param process_id: specific process to start
        """
        response = self.http.session_less_post(
            url=f"{self.process_api(process_id)}/work-items/{work_item_id}/retry",
            headers=self.headers,
        )

        return response.json()
