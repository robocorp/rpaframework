import copy
import fnmatch
import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from shutil import copy2

import requests
from requests.exceptions import HTTPError
from robot.libraries.BuiltIn import BuiltIn

from RPA.FileSystem import FileSystem
from RPA.core.helpers import import_by_name, required_env
from RPA.core.notebook import notebook_print

# Undefined default value
UNDEFINED = object()


def url_join(*parts):
    """Join parts of URL and handle missing/duplicate slashes."""
    return "/".join(str(part).strip("/") for part in parts)


def json_dump_safe(data, **kwargs):
    """Convert data to JSON string, and skip invalid values."""

    def invalid(obj):
        name = type(obj).__qualname__
        logging.warning("Failed to serialize: %s", name)
        return f"<non-serializable: {name}>"

    if data is None:
        data = {}

    return json.dumps(data, default=invalid, **kwargs)


def is_json_equal(left, right):
    """Deep-compare two output JSONs."""
    return json_dump_safe(left, sort_keys=True) == json_dump_safe(right, sort_keys=True)


class BaseAdapter(ABC):
    """Abstract base class for work item adapters."""

    def __init__(self, workspace_id, item_id):
        self.workspace_id = workspace_id
        self.item_id = item_id

    @abstractmethod
    def load_data(self):
        """Load data payload from work item."""
        raise NotImplementedError

    @abstractmethod
    def save_data(self, data):
        """Save data payload to work item."""
        raise NotImplementedError

    @abstractmethod
    def list_files(self):
        """List attached files in work item."""
        raise NotImplementedError

    @abstractmethod
    def add_file(self, name, content):
        """Attach file to work item."""
        raise NotImplementedError

    @abstractmethod
    def get_file(self, name):
        """Read file's contents from work item."""
        raise NotImplementedError

    @abstractmethod
    def remove_file(self, name):
        """Remove attached file from work item."""
        raise NotImplementedError


class RobocorpAdapter(BaseAdapter):
    """Adapter for saving/loading work items from Robocorp Cloud.

    Required environment variables:

    * RC_API_WORKITEM_HOST:     Work item API hostname
    * RC_API_WORKITEM_TOKEN:    Work item API access token
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = required_env("RC_API_WORKITEM_HOST")
        self.token = required_env("RC_API_WORKITEM_TOKEN")

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def load_data(self):
        """Load data payload as JSON."""
        url = self.url("data")
        logging.info("Loading work item data: %s", url)

        response = requests.get(url, headers=self.headers)
        if response.ok:
            return response.json()
        elif response.status_code == 404:
            return {}
        else:
            return self.handle_error(response)

    def save_data(self, data):
        """Save data payload as JSON."""
        url = self.url("data")
        data = json_dump_safe(data)
        logging.info("Saving work item data: %s", url)

        response = requests.put(url, headers=self.headers, data=data)
        self.handle_error(response)

        return response.json()

    def list_files(self):
        """List names of attached files."""
        url = self.url("files")
        logging.info("Listing work item files: %s", url)

        response = requests.get(url, headers=self.headers)
        self.handle_error(response)

        return [item["fileName"] for item in response.json()]

    def get_file(self, name):
        """Download attached file content.

        :param name: Name of file
        """
        # Robocorp API returns URL for S3 download
        url = self.url("files", self.file_id(name))
        logging.info("Downloading work item file: %s", url)

        response = requests.get(url, headers=self.headers)
        self.handle_error(response)
        data = response.json()

        # Perform actual file download
        url = data["url"]
        logging.debug("File download URL: %s", url)

        response = requests.get(url)
        response.raise_for_status()

        return response.content

    def add_file(self, name, content):
        """Attach and upload file.

        :param name:    Destination name
        :param content: Content of file
        """
        # Robocorp API returns pre-signed POST details for S3 upload
        url = self.url("files")
        info = {"fileName": str(name), "fileSize": len(content)}
        logging.info(
            "Adding work item file: %s (name: %s, size: %s)",
            url,
            info["fileName"],
            info["fileSize"],
        )

        response = requests.post(url, headers=self.headers, data=json.dumps(info))
        self.handle_error(response)
        data = response.json()

        # Perform actual file upload
        url = data["url"]
        fields = data["fields"]
        files = {"file": (name, content)}
        logging.debug("File upload URL: %s", url)

        response = requests.post(url, data=fields, files=files)
        response.raise_for_status()

    def remove_file(self, name):
        """Remove attached file.

        :param name: Name of file
        """
        url = self.url("files", self.file_id(name))
        logging.info("Removing work item file: %s", url)

        response = requests.delete(url, headers=self.headers)
        self.handle_error(response)

        return response.json()

    def file_id(self, name):
        """Convert filename to ID used by Robocorp API.

        :param name: Name of file
        """
        url = self.url("files")

        response = requests.get(url, headers=self.headers)
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

    def url(self, *parts):
        """Create full URL to Robocorp endpoint."""
        return url_join(
            self.host,
            "json-v1",
            "workspaces",
            self.workspace_id,
            "workitems",
            self.item_id,
            *parts,
        )

    def handle_error(self, response):
        """Handle response, and raise errors with human-friendly messages.

        :param response: Response returned by HTTP request
        """
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
    """Adapter for saving/loading work items from disk.

    Required environment variables:

    * RPA_WORKITEMS_PATH:   Path to work items database file
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = required_env("RPA_WORKITEMS_PATH")

    def load_data(self):
        """Load data payload from file."""
        content = self.read_database()
        try:
            return content[self.workspace_id][self.item_id]
        except KeyError:
            return {}

    def save_data(self, data):
        """Save data payload to file."""
        content = self.read_database()
        content.setdefault(self.workspace_id, {})[self.item_id] = data

        with open(self.path, "w") as outfile:
            outfile.write(json_dump_safe(content, indent=4))

    def list_files(self):
        """List files in the same folder as database."""
        files = []

        dirname = Path(self.path).parent
        for name in os.listdir(dirname):
            path = dirname / name
            if os.path.isfile(path) and path != Path(self.path):
                files.append(name)

        return files

    def get_file(self, name):
        """Read file from disk."""
        dirname = Path(self.path).parent
        with open(dirname / name, "rb") as infile:
            return infile.read()

    def add_file(self, name, content):
        """Write file to disk."""
        dirname = Path(self.path).parent
        with open(dirname / name, "wb") as outfile:
            outfile.write(content)

    def remove_file(self, name):
        """Do not remove local files."""
        del name

    def read_database(self):
        """Read JSON database from disk."""
        try:
            with open(self.path, "r") as infile:
                return json.load(infile)
        except IOError as err:
            logging.info("Failed to read database: %s", err)
            return {}


class WorkItem:
    """Container for a single work item, with local caching.

    :param workspace_id:    Workspace ID which contains item
    :param item_id:         Workitem ID
    :param adapter:         Adapter for storage backend
    """

    def __init__(self, workspace_id, item_id, adapter):
        self.workspace_id = workspace_id
        self.item_id = item_id
        self.adapter = adapter(workspace_id, item_id)

        #: Original data payload
        self._data = {}
        #: Local data payload cache
        self._data_cache = {}
        #: Attached files
        self._files = []
        #: Files pending upload
        self._files_to_add = {}
        #: Files pending removal
        self._files_to_remove = []

    def __str__(self):
        return f"WorkItem(workspace={self.workspace_id},id={self.item_id})"

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.save()

    @property
    def data(self):
        return self._data_cache

    @data.setter
    def data(self, value):
        self._data_cache = value

    @property
    def files(self):
        """List of filenames, including local files pending upload and
        excluding files pending removal.
        """
        current = [item for item in self._files if item not in self._files_to_remove]
        current.extend(self._files_to_add)
        return list(sorted(set(current)))

    @property
    def is_dirty(self):
        """Check if work item has unsaved changes."""
        return (
            not is_json_equal(self._data, self._data_cache)
            or self._files_to_add
            or self._files_to_remove
        )

    def load(self):
        """Load data payload and list of files."""
        self._data = self.adapter.load_data()
        self._data_cache = copy.deepcopy(self._data)

        self._files = self.adapter.list_files()
        self._files_to_add = {}
        self._files_to_remove = []

    def save(self):
        """Save data payload and attach/remove files."""
        self.adapter.save_data(self.data)

        for name in self._files_to_remove:
            self.adapter.remove_file(name)

        for name, path in self._files_to_add.items():
            with open(path, "rb") as infile:
                self.adapter.add_file(name, infile.read())

        # Empty unsaved values
        self._data = self._data_cache
        self._data_cache = copy.deepcopy(self._data)

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
            data = self.adapter.get_file(name)
            with open(path, "wb") as outfile:
                outfile.write(data)

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
            del self._files_to_remove[name]

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


class Items:
    """A library for interacting with RPA work items.

    Work items are used for managing data that go through multiple
    activities and tasks inside a process. Each execution of an activity receives
    a work item from the previous activity, and after the activity is finished, it
    is forwarded to the next one. During the execution, it can freely
    read and update the data contained in an item.

    The default implementation uses Robocloud to store the data, but the library
    allows using custom adapters.

    **Default environment**

    The library automatically loads the work item defined by its runtime
    environment if the argument ``load_env`` is truthy (enabled by default).
    This functionality is controlled by the following environment variables:

    * ``RC_WORKSPACE_ID``: The ID for the Robocloud workspace
    * ``RC_WORKITEM_ID``:  The ID for the Robocloud work item

    These values are dynamic and should be set by Robocloud, but can be
    overriden manually while developing an activity.

    **Item structure**

    A work item's data payload is JSON and allows storing anything that is
    serializable. This library creates an object with the key 'variables'
    that contains key-value pairs of a variable name and its contents.
    These variables can be exposed to the Robot Framework task to be used directly.

    In addition to the data section, a work item can also contain files,
    which are stored by default in Robocorp's cloud. Adding and using
    files with work items requires no additional setup from the user.

    **Workflow**

    While a work item is loaded automatically when a suite starts, changes are
    not automatically reflected back to the source. The work item will be modified
    locally and then saved when the corresponding keyword is explicitly called.
    It is recommended to defer all saves to the end of the task to prevent
    leaving work items in a half-modified state after failures.

    **Custom adapters**

    While Robocloud is the default implementation, it can also be replaced
    with a custom adapter. The selection is based on either the ``default_adapter``
    argument for the library, or the ``RPA_WORKITEMS_ADAPTER`` environment
    variable. A custom implementation should inherit from the ``BaseAdapter``
    class. The library has a built-in alternative adapter called FileAdapter for
    storing work items to disk.

    **Examples**

    **Robot Framework**

    In the following example the work item is modified locally and then saved
    back to Robocloud. Also note how the work item is loaded implicitly when
    the suite starts.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Robocloud.Items

        *** Tasks ***
        Save variables to Robocloud
            Add work item file    orders.xlsx
            Set work item variables    user=Dude    mail=address@company.com
            Save work item

    Later in the process inside a different robot, we can use previously saved
    work item variables and files. The library also allows injecting the variables
    directly into the current task execution.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Robocloud.Items

        *** Tasks ***
        Use variables from Robocloud
            Set task variables from work item
            Log    Variables are now available: ${user}, ${mail}
            ${path}=    Get work item file    orders.xlsx
            Log    Files are also stored to disk: ${path}

    **Python**

    The library can also be used through Python, but it does not implicitly
    load the work item for the current execution.

    .. code-block:: python

        import logging
        from RPA.Robocloud.Items import Items

        def list_variables(item_id):
            library = Items()
            library.load_work_item_from_environment()

            for variable, value in library.get_work_item_variables().items():
                logging.info("%s = %s", variable, value)
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, load_env=True, default_adapter=RobocorpAdapter):
        self.ROBOT_LIBRARY_LISTENER = self
        #: Adapter factory for new work items
        self.adapter = None
        #: The current active work item, set automatically to latest loaded item
        self.current = None

        self._load_env = load_env
        self._load_adapter(default_adapter)

    def _load_adapter(self, default):
        """Load adapter by name, using env or given default."""
        adapter = required_env("RPA_WORKITEMS_ADAPTER", default)
        if isinstance(adapter, str):
            self.adapter = import_by_name(adapter, __name__)
        else:
            self.adapter = adapter
        assert issubclass(
            self.adapter, BaseAdapter
        ), "Adapter does not inherit from BaseAdapter"

    def _start_suite(self, data, result):
        """Robot Framework listener method, called when suite starts."""
        # pylint: disable=unused-argument, broad-except
        if not self._load_env:
            return

        try:
            self.load_work_item_from_environment()
        except Exception as exc:
            logging.warning("Failed to load item: %s", exc)
        finally:
            self._load_env = False

    def _end_suite(self, data, result):
        """Robot Framework listener method, called when suite ends."""
        # pylint: disable=unused-argument
        if self.current and self.current.is_dirty:
            logging.warning("Work item has unsaved changes that will be discarded")

    def load_work_item_from_environment(self):
        """Load current work item defined by the runtime environment.

        The corresponding environment variables are:

        * RC_WORKSPACE_ID
        * RC_WORKITEM_ID
        """
        workspace_id = required_env("RC_WORKSPACE_ID")
        item_id = required_env("RC_WORKITEM_ID")
        return self.load_work_item(workspace_id, item_id)

    def load_work_item(self, workspace_id, item_id):
        """Load work item for reading/writing.

        :param workspace_id:    Workspace ID which contains item
        :param item_id:         Workitem ID to load

        **NOTE**: Currently only one work item per execution is supported
                  by Robocorp Cloud, which should be loaded automatically.
        """
        item = WorkItem(workspace_id, item_id, self.adapter)
        item.load()

        self.current = item
        return self.current

    def save_work_item(self):
        """Save the current data in the work item. If not saved,
        all changes are discarded when the library goes out of scope.
        """
        assert self.current, "No active work item"
        self.current.save()

    def clear_work_item(self):
        """Remove all data in the current work item.

        Example:

        .. code-block:: robotframework

            Clear work item
            Save work item
        """
        assert self.current, "No active work item"
        self.current.data = {}
        self.remove_work_item_files("*")

    def get_work_item_payload(self):
        """Get the full JSON payload for a work item.

        **NOTE**: Most use cases should prefer higher-level keywords.

        Example:

        .. code-block:: robotframework

            ${payload}=    Get work item payload
            Log    Entire payload as dictionary: ${payload}
        """
        assert self.current, "No active work item"
        return self.current.data

    def set_work_item_payload(self, payload):
        """Set the full JSON payload for a work item.

        :param payload: Content of payload, must be JSON-serializable

        **NOTE**: Most use cases should prefer higher-level keywords.

        Example:

        .. code-block:: robotframework

            ${output}=    Create dictionary    url=example.com    username=Mark
            Set work item payload    ${output}

        """
        assert self.current, "No active work item"
        self.current.data = payload

    def list_work_item_variables(self):
        """List the variable names for the current work item.

        Example:

        .. code-block:: robotframework

            ${variables}=    List work item variables
            Log    Available variables in work item: ${variables}

        """
        return list(self.get_work_item_variables().keys())

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

    def get_work_item_variables(self):
        """Read all variables from the current work item and
        return their names and values as a dictionary.

        Example:

        .. code-block:: robotframework

            ${variables}=    Get work item variables
            Log    Username: ${variables}[username], Email: ${variables}[email]
        """
        assert self.current, "No active work item"
        return self.current.data.setdefault("variables", {})

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

    def list_work_item_files(self):
        """List the names of files attached to the current work item.

        Example:

        .. code-block:: robotframework

            ${names}=    List work item files
            Log    Work item has files with names: ${names}
        """
        assert self.current, "No active work item"
        return self.current.files

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
        assert self.current, "No active work item"
        path = self.current.get_file(name, path)
        logging.info("Downloaded file to: %s", path)
        return path

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
        assert self.current, "No active work item"
        logging.info("Adding file: %s", path)
        return self.current.add_file(path, name)

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
        assert self.current, "No active work item"
        logging.info("Removing file: %s", name)
        return self.current.remove_file(name, missing_ok)

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

    def remove_work_item_files(self, pattern, missing_ok=True):
        """Removes files attached to work item that match given pattern.

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
