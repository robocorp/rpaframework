import copy
import fnmatch
import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from shutil import copy2
from typing import Type, Any, Optional, Union, Dict, List, Tuple

import requests
from requests.exceptions import HTTPError
from robot.api.deco import library, keyword
from robot.libraries.BuiltIn import BuiltIn

from RPA.FileSystem import FileSystem
from RPA.core.helpers import import_by_name, required_env
from RPA.core.notebook import notebook_print
from .utils import JSONType, url_join, json_dumps, is_json_equal, truncate, resolve_path


UNDEFINED = object()  # Undefined default value


class EmptyQueue(IndexError):
    """Raised when trying to load an input item and none available."""


class BaseAdapter(ABC):
    """Abstract base class for work item adapters."""

    @abstractmethod
    def get_input(self) -> str:
        """Get next work item ID from input queue."""
        raise NotImplementedError

    @abstractmethod
    def create_output(self, parent_id: str, payload: Optional[JSONType] = None) -> str:
        """Create new output for work item, and return created ID."""
        raise NotImplementedError

    @abstractmethod
    def load_payload(self, item_id: str) -> JSONType:
        """Load JSON payload from work item."""
        raise NotImplementedError

    @abstractmethod
    def save_payload(self, item_id: str, payload: JSONType):
        """Save JSON payload to work item."""
        raise NotImplementedError

    @abstractmethod
    def list_files(self, item_id: str) -> List[str]:
        """List attached files in work item."""
        raise NotImplementedError

    @abstractmethod
    def get_file(self, item_id: str, name: str) -> bytes:
        """Read file's contents from work item."""
        raise NotImplementedError

    @abstractmethod
    def add_file(self, item_id: str, name: str, content: bytes):
        """Attach file to work item."""
        raise NotImplementedError

    @abstractmethod
    def remove_file(self, item_id: str, name: str):
        """Remove attached file from work item."""
        raise NotImplementedError


class RobocorpAdapter(BaseAdapter):
    """Adapter for saving/loading work items from Robocorp Control Room.

    Required environment variables:

    * RC_API_WORKITEM_HOST:     Work item API hostname
    * RC_API_WORKITEM_TOKEN:    Work item API access token

    * RC_API_PROCESS_HOST:      Process API hostname
    * RC_API_PROCESS_TOKEN:     Process API access token

    * RC_WORKSPACE_ID:          Control room worksapce ID
    * RC_PROCESS_ID:            Control room process ID

    * RC_WORKITEM_ID:           Control room work item ID (input)
    """

    def __init__(self):
        #: Endpoint for old work items API
        self.workitem_host = required_env("RC_API_WORKITEM_HOST")
        self.workitem_token = required_env("RC_API_WORKITEM_TOKEN")

        #: Endpoint for new process API
        self.process_host = required_env("RC_API_PROCESS_HOST")
        self.process_token = required_env("RC_API_PROCESS_TOKEN")

        #: Current execution IDs
        self.workspace_id = required_env("RC_WORKSPACE_ID")
        self.process_id = required_env("RC_PROCESS_ID")

        #: Input queue of work items
        #: NOTE: Only one input item currently supported, through runtime env
        self.input_queue = [required_env("RC_WORKITEM_ID")]

    def get_input(self) -> str:
        try:
            return self.input_queue.pop()
        except IndexError as err:
            raise EmptyQueue("No work items in input queue") from err

    def create_output(self, parent_id: str, payload: Optional[JSONType] = None) -> str:
        url = self.process_url(parent_id, "output")
        logging.info("Creating output item: %s", url)

        data = json_dumps({"payload": payload})
        response = requests.post(url, headers=self.process_headers, data=data)
        self.handle_error(response)

        fields = response.json()
        return fields["id"]

    def load_payload(self, item_id: str) -> JSONType:
        url = self.workitem_url(item_id, "data")
        logging.info("Loading work item payload: %s", url)

        response = requests.get(url, headers=self.workitem_headers)

        if response.ok:
            return response.json()
        elif response.status_code == 404:
            # NOTE: The API might return 404 if no payload is
            #       attached to the work item
            return {}
        else:
            return self.handle_error(response)

    def save_payload(self, item_id: str, payload: JSONType):
        url = self.workitem_url(item_id, "data")
        logging.info("Saving work item payload: %s", url)

        data = json_dumps(payload)
        response = requests.put(url, headers=self.workitem_headers, data=data)
        self.handle_error(response)

    def list_files(self, item_id: str) -> List[str]:
        url = self.workitem_url(item_id, "files")
        logging.info("Listing work item files: %s", url)

        response = requests.get(url, headers=self.workitem_headers)
        self.handle_error(response)

        return [item["fileName"] for item in response.json()]

    def get_file(self, item_id: str, name: str) -> bytes:
        # Robocorp API returns URL for S3 download
        file_id = self.file_id(item_id, name)
        url = self.workitem_url(item_id, "files", file_id)
        logging.info("Downloading work item file: %s", url)

        response = requests.get(url, headers=self.workitem_headers)
        self.handle_error(response)

        # Perform actual file download
        fields = response.json()
        logging.debug("File download URL: %s", fields["url"])

        response = requests.get(fields["url"])
        response.raise_for_status()

        return response.content

    def add_file(self, item_id: str, name: str, content: bytes):
        # Robocorp API returns pre-signed POST details for S3 upload
        url = self.workitem_url(item_id, "files")
        info = {"fileName": str(name), "fileSize": len(content)}
        logging.info(
            "Adding work item file: %s (name: %s, size: %s)",
            url,
            info["fileName"],
            info["fileSize"],
        )

        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {self.workitem_token}"},
            data=json.dumps(info),
        )
        self.handle_error(response)
        data = response.json()

        # Perform actual file upload
        url = data["url"]
        fields = data["fields"]
        files = {"file": (name, content)}
        logging.debug("File upload URL: %s", url)

        response = requests.post(url, data=fields, files=files)
        response.raise_for_status()

    def remove_file(self, item_id: str, name: str):
        file_id = self.file_id(item_id, name)
        url = self.workitem_url(item_id, "files", file_id)
        logging.info("Removing work item file: %s", url)

        response = requests.delete(url, headers=self.workitem_headers)
        self.handle_error(response)

    def file_id(self, item_id: str, name: str) -> str:
        url = self.workitem_url(item_id, "files")

        response = requests.get(url, headers=self.workitem_headers)
        self.handle_error(response)

        files = response.json()
        if not files:
            raise FileNotFoundError("No files in work item")

        matches = [item for item in files if item["fileName"] == name]
        if not matches:
            raise FileNotFoundError(
                "File with name '{name}' not in: {names}".format(
                    name=name, names=", ".join(item["fileName"] for item in files)
                )
            )

        # Duplicate filenames should never exist,
        # but use last item just in case
        return matches[-1]["fileId"]

    @property
    def workitem_headers(self):
        return {"Authorization": f"Bearer {self.workitem_token}"}

    def workitem_url(self, item_id: str, *parts: str):
        return url_join(
            self.workitem_host,
            "json-v1",
            "workspaces",
            self.workspace_id,
            "workitems",
            item_id,
            *parts,
        )

    @property
    def process_headers(self):
        return {"Authorization": f"Bearer {self.process_token}"}

    def process_url(self, item_id: str, *parts: str):
        return url_join(
            self.process_host,
            "process-v1",
            "workspaces",
            self.workspace_id,
            "processes",
            self.process_id,
            "work-items",
            item_id,
            *parts,
        )

    def handle_error(self, response: requests.Response):
        if response.ok:
            return

        fields = {}
        try:
            fields = response.json()
        except ValueError:
            response.raise_for_status()

        try:
            status_code = fields.get("status", response.status_code)
            status_msg = fields.get("error", {}).get("code", "Error")
            reason = fields.get("message") or fields.get("error", {}).get(
                "message", response.reason
            )

            raise HTTPError(f"{status_code} {status_msg}: {reason}")
        except Exception as err:  # pylint: disable=broad-except
            raise HTTPError(str(fields)) from err


class FileAdapter(BaseAdapter):
    """Adapter for mocking work item input queues.

    Reads inputs from the given database file, and writes
    all created output items into an adjacent file
    with the suffix ``<filename>.output.json``.

    Reads and writes all work item files from/to the same parent
    folder as the given input database.

    Required environment variables:

    * RPA_WORKITEMS_PATH:   Path to work items database file
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        path = required_env("RPA_WORKITEMS_PATH")
        logging.info("Resolving path: %s", path)
        self.path = resolve_path(path)

        self.inputs: List[Dict[str, Any]] = self.load_database()
        self.outputs: List[Dict[str, Any]] = []
        self.index: int = 0

    def _get_item(self, item_id: str) -> Tuple[str, Dict[str, Any]]:
        idx = int(item_id)
        if idx < len(self.inputs):
            return "input", self.inputs[idx]
        elif idx < (len(self.inputs) + len(self.outputs)):
            return "output", self.outputs[idx - len(self.inputs)]
        else:
            raise ValueError(f"Unknown work item ID: {item_id}")

    def get_input(self) -> str:
        try:
            idx = self.index
            _ = self.inputs[idx]
            self.index += 1
            return str(idx)
        except IndexError as err:
            raise EmptyQueue("No work items in input queue") from err

    def create_output(self, parent_id: str, payload: Optional[JSONType] = None) -> str:
        del parent_id

        item: Dict[str, Any] = {"payload": payload, "files": {}}
        self.outputs.append(item)

        logging.debug("Payload: %s", json_dumps(payload, indent=4))

        path = self.path.with_suffix(".output.json")
        with open(path, "w", encoding="utf-8") as fd:
            fd.write(json_dumps(self.outputs, indent=4))

        logging.info("Saved into file: %s", path)
        return str(len(self.inputs) + len(self.outputs) - 1)

    def load_payload(self, item_id: str) -> JSONType:
        _, item = self._get_item(item_id)
        return item.get("payload", {})

    def save_payload(self, item_id: str, payload: JSONType):
        source, item = self._get_item(item_id)

        item["payload"] = payload
        logging.debug("Payload: %s", json_dumps(payload, indent=4))

        if source == "input":
            path = self.path
            data = self.inputs
        else:
            path = self.path.with_suffix(".output.json")
            data = self.outputs

        with open(path, "w", encoding="utf-8") as fd:
            fd.write(json_dumps(data, indent=4))

        logging.info("Saved into file: %s", path)

    def list_files(self, item_id: str) -> List[str]:
        _, item = self._get_item(item_id)
        files = item.get("files", {})
        return list(files.keys())

    def get_file(self, item_id: str, name: str) -> bytes:
        _, item = self._get_item(item_id)
        files = item.get("files", {})

        path = files[name]
        if not Path(path).is_absolute():
            path = self.path.parent / path

        with open(path, "rb") as infile:
            return infile.read()

    def add_file(self, item_id: str, name: str, content: bytes):
        _, item = self._get_item(item_id)
        files = item.setdefault("files", {})

        path = self.path.parent / name
        with open(path, "wb") as fd:
            fd.write(content)

        logging.info("Created file: %s", path)
        files[name] = name

    def remove_file(self, item_id: str, name: str):
        _, item = self._get_item(item_id)
        files = item.get("files", {})

        path = files[name]
        logging.info("Would remove file: %s", path)

        del files[name]

    def load_database(self) -> List:
        try:
            try:
                with open(self.path, "r", encoding="utf-8") as infile:
                    data = json.load(infile)
            except FileNotFoundError:
                logging.warning("No work items file found: %s", self.path)
                data = []

            if isinstance(data, list):
                assert all(
                    isinstance(d, dict) for d in data
                ), "Items should be dictionaries"
                if len(data) == 0:
                    data.append({"payload": {}})
                return data

            def first(d: Dict[str, Any]) -> str:
                return list(d.keys())[0]

            # Attempt to migrate from old format
            assert isinstance(data, dict), "Not a list or dictionary"
            logging.warning("Work items file as mapping is deprecated")
            workspace = data[first(data)]
            work_item = workspace[first(workspace)]
            return [{"payload": work_item}]
        except Exception as exc:  # pylint: disable=broad-except
            logging.error("Invalid work items file: %s", exc)
            return [{"payload": {}}]


class WorkItem:
    """Base class for input and output work items.

    :param adapter:   Adapter instance
    :param item_id:   Work item ID (optional)
    :param parent_id: Parent work item's ID (optional)
    """

    def __init__(self, adapter, item_id=None, parent_id=None):
        #: Adapter for loading/saving content
        self.adapter = adapter
        #: This item's ID, if created
        self.id: Optional[str] = item_id
        self.parent_id: Optional[str] = parent_id
        assert self.id is not None or self.parent_id is not None
        #: Remote JSON payload, and queued changes
        self._payload: JSONType = {}
        self._payload_cache: JSONType = {}
        #: Remote attached files, and queued changes
        self._files: List[str] = []
        self._files_to_add: Dict[str, Path] = {}
        self._files_to_remove: List[str] = []

    def __repr__(self):
        payload = truncate(str(self.payload), 64)
        files = len(self.files)
        return f"WorkItem(id={self.id}, payload={payload}, files={files})"

    @property
    def is_dirty(self):
        """Check if work item has unsaved changes."""
        return (
            self.id is None
            or not is_json_equal(self._payload, self._payload_cache)
            or self._files_to_add
            or self._files_to_remove
        )

    @property
    def payload(self):
        return self._payload_cache

    @payload.setter
    def payload(self, value):
        self._payload_cache = value

    @property
    def files(self):
        """List of filenames, including local files pending upload and
        excluding files pending removal.
        """
        current = [item for item in self._files if item not in self._files_to_remove]
        current.extend(self._files_to_add)
        return list(sorted(set(current)))

    def load(self):
        """Load data payload and list of files."""
        self._payload = self.adapter.load_payload(self.id)
        self._payload_cache = copy.deepcopy(self._payload)

        self._files = self.adapter.list_files(self.id)
        self._files_to_add = {}
        self._files_to_remove = []

    def save(self):
        """Save data payload and attach/remove files."""
        if self.id is None:
            self.id = self.adapter.create_output(self.parent_id, self.payload)
        else:
            self.adapter.save_payload(self.id, self.payload)

        for name in self._files_to_remove:
            self.adapter.remove_file(self.id, name)

        for name, path in self._files_to_add.items():
            with open(path, "rb") as infile:
                self.adapter.add_file(self.id, name, infile.read())

        # Empty unsaved values
        self._payload = self._payload_cache
        self._payload_cache = copy.deepcopy(self._payload)

        self._files = self.files
        self._files_to_add = {}
        self._files_to_remove = []

    def get_file(self, name, path=None):
        """Load an attached file and store it on the local filesystem.

        :param name: Name of attached file
        :param path: Destination path. Default to current working directory.
        :returns:    Path to created file
        """
        if name not in self.files:
            raise FileNotFoundError(f"No such file: {name}")

        if not path:
            root = os.getenv("ROBOT_ROOT", "")
            path = os.path.join(root, name)

        if name in self._files_to_add:
            local_path = self._files_to_add[name]
            if Path(local_path).resolve() != Path(path).resolve():
                copy2(local_path, path)
        else:
            content = self.adapter.get_file(self.id, name)
            with open(path, "wb") as outfile:
                outfile.write(content)

        # Always return absolute path
        return str(Path(path).resolve())

    def add_file(self, path, name=None):
        """Add file to current work item. Does not upload
        until ``save()`` is called.

        :param path: Path to file to upload
        :param name: Name of file in work item. If not given,
                     name of file on disk is used.
        """
        path = Path(path).resolve()

        if path in self._files_to_add.values():
            logging.warning("File already added: %s", path)

        if not path.is_file():
            raise FileNotFoundError(f"Not a valid file: {path}")

        name = name or path.name
        self._files_to_add[name] = path

        if name in self._files_to_remove:
            self._files_to_remove.remove(name)

        return name

    def remove_file(self, name, missing_ok=True):
        """Remove file from current work item. Change is not applied
        until ``save()`` is called.

        :param name: Name of attached file
        """
        if not missing_ok and name not in self.files:
            raise FileNotFoundError(f"No such file: {name}")

        if name in self._files:
            self._files_to_remove.append(name)

        if name in self._files_to_add:
            del self._files_to_add[name]

        return name


@library
class WorkItems:
    """A library for interacting with Control Room work items.

    Work items are used for managing data that go through multiple
    steps and tasks inside a process. Each step of a process receives
    input work items from the previous step, and creates output work items for
    the next step.

    **Item structure**

    A work item's data payload is JSON and allows storing anything that is
    serializable. This library by default interacts with payloads that
    are a dictionary of key-value pairs, which it treats as individual
    variables. These variables can be exposed to the Robot Framework task
    to be used directly.

    In addition to the data section, a work item can also contain files,
    which are stored by default in Robocorp Control Room. Adding and using
    files with work items requires no additional setup from the user.

    **Loading inputs**

    The library automatically loads the first input work item, if the
    library input argument ``autoload`` is truthy (default).

    After an input has been loaded its payload and files can be accessed
    through corresponding keywords, and optionally these values can be modified.

    **Creating outputs**

    It's possible to create multiple new work items as an output from a
    task. With the keyword ``Create output work item`` a new empty item
    is created as a child for the currently loaded input.

    All created output items are sent into the input queue of the next
    step in the process.

    **Active work item**

    Keywords that read or write from a work item always operate on the currently
    active work item. Usually that is the input item that has been automatically
    loaded when the execution started, but the currently active item is changed
    whenever the keywords ``Create output work item`` or ``Get input work item``
    are called. It's also possible to change the active item manually with the
    keyword ``Set current work item``.

    **Saving changes**

    While a work item is loaded automatically when a suite starts, changes are
    not automatically reflected back to the source. The work item will be modified
    locally and then saved when the keyword ``Save work item`` is called.
    This also applies to created output work items.

    It is recommended to defer saves until all changes have been made to prevent
    leaving work items in a half-modified state in case of failures.

    **Development and mocking**

    While Control Room is the default implementation, it can also be replaced
    with a custom adapter. The selection is based on either the ``default_adapter``
    argument for the library, or the ``RPA_WORKITEMS_ADAPTER`` environment
    variable. The library has a built-in alternative adapter called FileAdapter for
    storing work items to disk.

    **Examples**

    **Robot Framework**

    In the following example a task creates an output work item,
    and attaches some variables to it.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Robocorp.WorkItems

        *** Tasks ***
        Save variables to Control Room
            Create output work item
            Set work item variables    user=Dude    mail=address@company.com
            Save work item

    In the next step of the process inside a different robot, we can use
    previously saved work item variables. Also note how the input work item is
    loaded implicitly when the suite starts.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Robocorp.WorkItems

        *** Tasks ***
        Use variables from Control Room
            Set task variables from work item
            Log    Variables are now available: s${user}, ${mail}

    **Python**

    The library can also be used through Python, but it does not implicitly
    load the first work item.

    .. code-block:: python

        import logging
        from RPA.Robocorp.WorkItems import WorkItems

        def list_variables(item_id):
            library = WorkItems()
            library.get_input_work_item()

            variables = library.get_work_item_variables()
            for variable, value in variables.items():
                logging.info("%s = %s", variable, value)
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(
        self,
        autoload: bool = True,
        root: Optional[str] = None,
        default_adapter: Union[Type[BaseAdapter], str] = RobocorpAdapter,
    ):
        self.ROBOT_LIBRARY_LISTENER = self

        #: Current selected worok item
        self._current: Optional[WorkItem] = None
        #: Input work items
        self.inputs: List[WorkItem] = []
        #: Output work items
        self.outputs: List[WorkItem] = []
        #: Variables root object in payload
        self.root = root
        #: Auto-load first input item
        self.autoload: bool = autoload
        #: Adapter for reading/writing items
        self._adapter_class = self._load_adapter(default_adapter)
        self._adapter: Optional[BaseAdapter] = None

    @property
    def adapter(self):
        if self._adapter is None:
            self._adapter = self._adapter_class()
        return self._adapter

    @property
    def current(self):
        if self._current is None:
            raise RuntimeError("No active work item")

        return self._current

    @current.setter
    def current(self, value):
        if not isinstance(value, WorkItem):
            raise ValueError(f"Not a work item: {value}")

        self._current = value

    def _load_adapter(self, default) -> Type[BaseAdapter]:
        """Load adapter by name, using env or given default."""
        adapter = required_env("RPA_WORKITEMS_ADAPTER", default)

        if isinstance(adapter, str):
            adapter = import_by_name(adapter, __name__)

        assert issubclass(
            adapter, BaseAdapter
        ), "Adapter does not inherit from BaseAdapter"

        return adapter

    def _start_suite(self, data, result):
        """Robot Framework listener method, called when suite starts."""
        # pylint: disable=unused-argument, broad-except
        if not self.autoload:
            return

        try:
            self.get_input_work_item()
        except Exception as exc:
            logging.warning("Failed to load input work item: %s", exc)
        finally:
            self.autoload = False

    def _end_suite(self, data, result):
        """Robot Framework listener method, called when suite ends."""
        # pylint: disable=unused-argument
        for item in self.inputs + self.outputs:
            if item.is_dirty:
                logging.warning(
                    "%s has unsaved changes that will be discarded", self.current
                )

    def set_current_work_item(self, item: WorkItem):
        """Set the currently active work item.

        The current work item is used as the target by other keywords
        in this library.

        Keywords ``Get input work item`` and ``Create output work item``
        set the active work item automatically, and return the created
        instance.

        With this keyword the active work item can be set manually.

        Example:

        .. code-block:: robotframework

            ${input}=    Get input work item
            ${output}=   Create output work item
            Set current work item    ${input}
        """
        self.current = item

    @keyword
    def get_input_work_item(self):
        """Load the next work item from the input queue,
        and set it as the active work item.

        If the library import argument ``autoload`` is truthy (default),
        this is called automatically when the Robot Framework suite
        starts.

        **NOTE**: Currently only one input work item per execution is supported
                  by Control Room.
        """
        item_id = self.adapter.get_input()

        item = WorkItem(item_id=item_id, parent_id=None, adapter=self.adapter)
        item.load()

        self.inputs.append(item)
        self.current = item
        return self.current

    @keyword
    def create_output_work_item(self):
        """Create a new output work item.

        An output work item is always created as a child for an input item,
        and as such requires an input to be loaded.

        All changes to the work item are done locally, and are only sent
        to the output queue after the keyword ``Save work item`` is called.

        Example:

        .. code-block:: robotframework

            ${customers}=    Load customer data
            FOR    ${customer}    IN    @{customers}
                Create output work item
                Set work item variables    name=${customer.name}    id=${customer.id}
                Save work item
            END
        """
        if not self.inputs:
            raise RuntimeError(
                "Unable to create output work item without an input, "
                "call `Get input work item` first"
            )

        parent = self.inputs[-1]
        item = WorkItem(item_id=None, parent_id=parent.id, adapter=self.adapter)

        self.outputs.append(item)
        self.current = item
        return self.current

    @keyword
    def save_work_item(self):
        """Save the current data and files in the work item. If not saved,
        all changes are discarded when the library goes out of scope.
        """
        self.current.save()

    @keyword
    def clear_work_item(self):
        """Remove all data and files in the current work item.

        Example:

        .. code-block:: robotframework

            Clear work item
            Save work item
        """
        self.current.payload = {}
        self.remove_work_item_files("*")

    @keyword
    def get_work_item_payload(self):
        """Get the full JSON payload for a work item.

        **NOTE**: Most use cases should prefer higher-level keywords.

        Example:

        .. code-block:: robotframework

            ${payload}=    Get work item payload
            Log    Entire payload as dictionary: ${payload}
        """
        return self.current.payload

    @keyword
    def set_work_item_payload(self, payload):
        """Set the full JSON payload for a work item.

        :param payload: Content of payload, must be JSON-serializable

        **NOTE**: Most use cases should prefer higher-level keywords.

        Example:

        .. code-block:: robotframework

            ${output}=    Create dictionary    url=example.com    username=Mark
            Set work item payload    ${output}

        """
        self.current.payload = payload

    @keyword
    def list_work_item_variables(self):
        """List the variable names for the current work item.

        Example:

        .. code-block:: robotframework

            ${variables}=    List work item variables
            Log    Available variables in work item: ${variables}

        """
        return list(self.get_work_item_variables().keys())

    @keyword
    def get_work_item_variable(self, name, default=UNDEFINED):
        """Return a single variable value from the work item,
        or default value if defined and key does not exist.

        If key does not exist and default is not defined, raises `KeyError`.

        :param key: Name of variable
        :param default: Default value if key does not exist

        Example:

        .. code-block:: robotframework

            ${username}=    Get work item variable    username    default=guest
        """
        variables = self.get_work_item_variables()
        value = variables.get(name, default)

        if value is UNDEFINED:
            raise KeyError(f"Undefined variable: {name}")

        notebook_print(text=f"**{name}** = **{value}**")
        return value

    @keyword
    def get_work_item_variables(self):
        """Read all variables from the current work item and
        return their names and values as a dictionary.

        Example:

        .. code-block:: robotframework

            ${variables}=    Get work item variables
            Log    Username: ${variables}[username], Email: ${variables}[email]
        """

        payload = self.current.payload
        if not isinstance(payload, dict):
            raise ValueError(
                f"Expected work item payload to be `dict`, was `{type(payload)}`"
            )

        if self.root is not None:
            return payload.setdefault(self.root, {})

        return payload

    @keyword
    def set_work_item_variable(self, name, value):
        """Set a single variable value in the current work item.

        :param key: Name of variable
        :param value: Value of variable

        Example:

        .. code-block:: robotframework

            Set work item variable    username    MarkyMark
            Save work item
        """
        variables = self.get_work_item_variables()
        logging.info("%s = %s", name, value)
        variables[name] = value

    @keyword
    def set_work_item_variables(self, **kwargs):
        """Set multiple variables in the current work item.

        :param kwargs: Pairs of variable names and values

        Example:

        .. code-block:: robotframework

            Set work item variables    username=MarkyMark    email=mark@example.com
            Save work item
        """
        variables = self.get_work_item_variables()
        for name, value in kwargs.items():
            logging.info("%s = %s", name, value)
            variables[name] = value

    @keyword
    def delete_work_item_variables(self, *names, force=True):
        """Delete variable(s) from the current work item.

        :param names: Names of variables to remove
        :param force: Ignore variables that don't exist in work item

        Example:

        .. code-block:: robotframework

            Delete work item variables    username    email
            Save work item
        """
        variables = self.get_work_item_variables()
        for name in names:
            if name in variables:
                del variables[name]
                logging.info("Deleted variable: %s", name)
            elif not force:
                raise KeyError(f"No such variable: {name}")

    @keyword
    def set_task_variables_from_work_item(self):
        """Convert all variables in the current work item to
        Robot Framework task variables.

        Example:

        .. code-block:: robotframework

            # Work item has variable INPUT_URL
            Set task variables from work item
            Log    The variable is now available: ${INPUT_URL}
        """
        variables = self.get_work_item_variables()
        for name, value in variables.items():
            BuiltIn().set_task_variable(f"${{{name}}}", value)

    @keyword
    def list_work_item_files(self):
        """List the names of files attached to the current work item.

        Example:

        .. code-block:: robotframework

            ${names}=    List work item files
            Log    Work item has files with names: ${names}
        """
        return self.current.files

    @keyword
    def get_work_item_file(self, name, path=None):
        """Get attached file from work item to disk.
        Returns the absolute path to the created file.

        :param name: Name of attached file
        :param path: Destination path of file. If not given, current
                     working directory is used.

        Example:

        .. code-block:: robotframework

            ${path}=    Get work item file    input.xls
            Open workbook    ${path}
        """
        path = self.current.get_file(name, path)
        logging.info("Downloaded file to: %s", path)
        return path

    @keyword
    def add_work_item_file(self, path, name=None):
        """Add given file to work item.

        :param path: Path to file on disk
        :param name: Destination name for file. If not given, current name
                     of local file is used.

        **NOTE**: Files are not uploaded before work item is saved

        Example:

        .. code-block:: robotframework

            Add work item file    output.xls
            Save work item
        """
        logging.info("Adding file: %s", path)
        return self.current.add_file(path, name)

    @keyword
    def remove_work_item_file(self, name, missing_ok=True):
        """Remove attached file from work item.

        :param name: Name of attached file
        :param missing_ok: Do not raise exception if file doesn't exist

        **NOTE**: Files are not deleted before work item is saved

        Example:

        .. code-block:: robotframework

            Remove work item file    input.xls
            Save work item
        """
        logging.info("Removing file: %s", name)
        return self.current.remove_file(name, missing_ok)

    @keyword
    def get_work_item_files(self, pattern, dirname=None):
        """Get files attached to work item that match given pattern.
        Returns a list of absolute paths to the downloaded files.

        :param pattern: Filename wildcard pattern
        :param dirname: Destination directory, if not given robot root is used

        Example:

        .. code-block:: robotframework

            ${paths}=    Get work item files    customer_*.xlsx
            FOR  ${path}  IN  @{paths}
                Handle customer file    ${path}
            END
        """
        paths = []
        for name in self.list_work_item_files():
            if fnmatch.fnmatch(name, pattern):
                if dirname:
                    path = self.get_work_item_file(name, os.path.join(dirname, name))
                else:
                    path = self.get_work_item_file(name)
                paths.append(path)

        logging.info("Downloaded %d file(s)", len(paths))
        return paths

    @keyword
    def add_work_item_files(self, pattern):
        """Add all files that match given pattern to work item.

        :param pattern: Path wildcard pattern

        Example:

        .. code-block:: robotframework

            Add work item files    %{ROBOT_ROOT}/generated/*.csv
            Save work item
        """
        matches = FileSystem().find_files(pattern, include_dirs=False)

        paths = []
        for match in matches:
            path = self.add_work_item_file(match)
            paths.append(path)

        logging.info("Added %d file(s)", len(paths))
        return paths

    @keyword
    def remove_work_item_files(self, pattern, missing_ok=True):
        """Removes files attached to work item that match the given pattern.

        :param pattern: Filename wildcard pattern
        :param missing_ok: Do not raise exception if file doesn't exist

        Example:

        .. code-block:: robotframework

            Remove work item files    *.xlsx
            Save work item
        """
        names = []

        for name in self.list_work_item_files():
            if fnmatch.fnmatch(name, pattern):
                name = self.remove_work_item_file(name, missing_ok)
                names.append(name)

        logging.info("Removed %d file(s)", len(names))
        return names
