"""
WorkItem library skeleton

* Multiple adapters for different backend
* Default endpoints, tokens, ids from env (runtime)
"""
import json
import logging
from abc import ABC, abstractmethod

import requests
from requests.exceptions import HTTPError
from robot.libraries.BuiltIn import BuiltIn

from RPA.core.helpers import import_by_name, required_env
from RPA.core.notebook import notebook_print


def json_dump_safe(data, **kwargs):
    """Convert data to JSON string, and skip invalid values."""

    def invalid(obj):
        name = type(obj).__qualname__
        logging.warning("Failed to serialize: %s", name)
        return f"<non-serializable: {name}>"

    if data is None:
        data = {}

    return json.dumps(data, default=invalid, **kwargs)


class BaseAdapter(ABC):
    """Abstract base class for work item adapters."""

    @abstractmethod
    def load(self, workspace_id, item_id):
        raise NotImplementedError

    @abstractmethod
    def save(self, workspace_id, item_id, data):
        raise NotImplementedError


class RobocloudAdapter(BaseAdapter):
    """Adapter for saving/loading work items from Robocloud.

    Required environment variables:

    * RC_API_WORKITEM_HOST:     Work item data API hostname
    * RC_API_WORKITEM_TOKEN:    Work item data API access token
    """

    def __init__(self):
        self.host = required_env("RC_API_WORKITEM_HOST")
        self.token = required_env("RC_API_WORKITEM_TOKEN")

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def url(self, workspace_id, item_id):
        return f"{self.host}/json-v1/workspaces/{workspace_id}/workitems/{item_id}/data"

    def handle_response(self, request):
        if request.ok:
            return request.json()

        if request.status_code == 404:
            return {}

        try:
            response = request.json()
        except ValueError:
            request.raise_for_status()

        status_code = response.get("status", request.status_code)
        status_msg = response.get("error", {}).get("code", "Error")
        reason = response.get("message") or response.get("error", {}).get(
            "message", request.reason
        )

        raise HTTPError(f"{status_code} {status_msg}: {reason}")

    def load(self, workspace_id, item_id):
        url = self.url(workspace_id, item_id)
        logging.info("Loading item from %s", url)

        resp = requests.get(url, headers=self.headers)
        return self.handle_response(resp)

    def save(self, workspace_id, item_id, data):
        url = self.url(workspace_id, item_id)
        logging.info("Saving item to %s", url)

        data = json_dump_safe(data)
        logging.info("Payload: %s", data)

        resp = requests.put(url, headers=self.headers, data=data)
        return self.handle_response(resp)


class FileAdapter(BaseAdapter):
    """Adapter for saving/loading work items from disk.

    Required environment variables:

    * RPA_WORKITEMS_PATH:   Path to work items database file
    """

    def __init__(self):
        self.path = required_env("RPA_WORKITEMS_PATH")

    def _read(self):
        try:
            with open(self.path, "r") as infile:
                return json.load(infile)
        except IOError as err:
            logging.info("Failed to read database: %s", err)
            return {}

    def load(self, workspace_id, item_id):
        content = self._read()
        try:
            return content[workspace_id][item_id]
        except KeyError:
            return {}

    def save(self, workspace_id, item_id, data):
        content = self._read()
        content.setdefault(workspace_id, {})[item_id] = data

        with open(self.path, "w") as outfile:
            outfile.write(json_dump_safe(content, indent=4))


class WorkItem:
    """Container for a single work item.

    :param workspace_id:    Workspace ID which contains item
    :param item_id:         Workitem ID
    :param adapter:         Adapter for storage backend
    """

    def __init__(self, workspace_id, item_id, adapter):
        self.workspace_id = workspace_id
        self.item_id = item_id
        self.adapter = adapter

        #: Current item payload
        self.data = None

    def __str__(self):
        return f"WorkItem(workspace={self.workspace_id},id={self.item_id})"

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.save()

    def show(self):
        return "{item}: {data}".format(item=self, data=json.dumps(self.data, indent=4))

    def load(self):
        self.data = self.adapter.load(self.workspace_id, self.item_id)
        return self.data

    def save(self):
        self.adapter.save(self.workspace_id, self.item_id, self.data)


class Items:
    """A library for interacting with RPA work items.

    `Items` is a collection of keywords for handling data
    that is moved between different processes and Robot Framework
    tasks. It allows storing and restoring values to/from cloud or file based
    storage, and manipulating their contents.

    :param load_env: Automatically load work item using environment variables
    :param default_adapter: Set default adapter if not overriden by environment

    Environment variables:

    * RPA_WORKITEMS_ADAPTER: Import path to adapter, e.g. "mymodule.MyAdapter"
    * RC_WORKSPACE_ID:       Current default workspace ID
    * RC_WORKITEM_ID:        Current default work item ID
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, load_env=True, default_adapter=RobocloudAdapter):
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
        if self._load_env:
            try:
                self.load_work_item_from_environment()
            except Exception as exc:
                logging.warning("Failed to load item: %s", exc)
            finally:
                self._load_env = False

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
        """
        item = WorkItem(workspace_id, item_id, self.adapter())
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
        """Remove all data in the current work item."""
        assert self.current, "No active work item"
        self.current.data = {}

    def get_work_item_payload(self):
        """Get the full JSON payload for a work item.

        NOTE: Most use cases should prefer higher-level keywords.
        """
        assert self.current, "No active work item"
        return self.current.data

    def set_work_item_payload(self, payload):
        """Set the full JSON payload for a work item.

        NOTE: Most use cases should prefer higher-level keywords.

        :param payload: Content of payload, must be JSON-serializable
        """
        assert self.current, "No active work item"
        self.current.data = payload

    def list_work_item_variables(self):
        """List the variable names for the current work item."""
        return list(self.get_work_item_variables().keys())

    def get_work_item_variables(self):
        """Read all variables from the current work item and
        return their names and values as a dictionary.
        """
        assert self.current, "No active work item"
        return self.current.data.setdefault("variables", {})

    def get_work_item_variable(self, name, default=None):
        """Return a single variable value from the work item,
        or default value if defined and key does not exist.
        If key does not exist and default is not defined, raises `KeyError`.

        :param key:     Name of variable
        :param default: Default value if key does not exist
        """
        variables = self.get_work_item_variables()
        value = variables.get(name, default)
        if value is None:
            raise KeyError(f"Undefined variable: {name}")
        notebook_print(text=f"**{name}** = **{value}**")
        return value

    def set_work_item_variables(self, **kwargs):
        """Set multiple variables in the current work item.

        :param kwargs: Pairs of variable names and values
        """
        variables = self.get_work_item_variables()
        for name, value in kwargs.items():
            logging.info("%s = %s", name, value)
            variables[name] = value

    def set_work_item_variable(self, name, value):
        """Set a single variable value in the current work item.

        :param key:     Name of variable
        :param value:   Value of variable
        """
        variables = self.get_work_item_variables()
        logging.info("%s = %s", name, value)
        variables[name] = value

    def delete_work_item_variables(self, *names, force=True):
        """Delete variable(s) from the current work item.

        :param names:  names of variables to remove
        :param force:  ignore variables that don't exist in work item
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
        """
        variables = self.get_work_item_variables()
        for name, value in variables.items():
            BuiltIn().set_task_variable(f"${{{name}}}", value)
