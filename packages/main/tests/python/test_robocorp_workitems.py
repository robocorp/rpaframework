import copy
import json
import os
import pytest
import tempfile
from contextlib import contextmanager

try:
    from contextlib import nullcontext
except ImportError:
    from contextlib import suppress as nullcontext
from pathlib import Path
from unittest import mock

from requests import HTTPError

from RPA.Robocorp.WorkItems import (
    BaseAdapter,
    EmptyQueue,
    Error,
    FileAdapter,
    RobocorpAdapter,
    State,
    WorkItems,
)
from RPA.Robocorp.utils import RequestsHTTPError


VARIABLES_FIRST = {"username": "testguy", "address": "guy@company.com"}
VARIABLES_SECOND = {"username": "another", "address": "dude@company.com"}

VALID_DATA = {
    "workitem-id-first": VARIABLES_FIRST,
    "workitem-id-second": VARIABLES_SECOND,
    "workitem-id-custom": [1, 2, 3],
}

VALID_FILES = {
    "workitem-id-first": {
        "file1.txt": b"data1",
        "file2.txt": b"data2",
        "file3.png": b"data3",
    },
    "workitem-id-second": {},
    "workitem-id-custom": {},
}

ITEMS_JSON = [{"payload": {"a-key": "a-value"}, "files": {"a-file": "file.txt"}}]


@contextmanager
def temp_filename(content=None):
    """Create temporary file and return filename, delete file afterwards.
    Needs to close file handle, since Windows won't allow multiple
    open handles to the same file.
    """
    with tempfile.NamedTemporaryFile(delete=False) as fd:
        path = fd.name
        if content:
            fd.write(content)

    try:
        yield path
    finally:
        os.unlink(path)


def is_equal_files(lhs, rhs):
    lhs = Path(lhs).resolve()
    rhs = Path(rhs).resolve()
    return lhs == rhs


class MockAdapter(BaseAdapter):
    DATA = {}
    FILES = {}
    INDEX = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._data_keys = []
        self.releases = []

    @classmethod
    def validate(cls, item, key, val):
        data = cls.DATA.get(item.id)
        assert data is not None
        assert data[key] == val

    @property
    def data_keys(self):
        if not self._data_keys:
            self._data_keys = list(self.DATA.keys())
        return self._data_keys

    def reserve_input(self) -> str:
        if self.INDEX >= len(self.data_keys):
            raise EmptyQueue("No work items in the input queue")

        try:
            return self.data_keys[self.INDEX]
        finally:
            self.INDEX += 1

    def release_input(self, item_id: str, state: State, exception: dict = None):
        self.releases.append((item_id, state, exception))  # purely for testing purposes

    def create_output(self, parent_id, payload=None) -> str:
        raise NotImplementedError

    def load_payload(self, item_id):
        return self.DATA[item_id]

    def save_payload(self, item_id, payload):
        self.DATA[item_id] = payload

    def list_files(self, item_id):
        return self.FILES[item_id]

    def get_file(self, item_id, name):
        return self.FILES[item_id][name]

    def add_file(self, item_id, name, *, original_name, content):
        self.FILES[item_id][name] = content

    def remove_file(self, item_id, name):
        del self.FILES[item_id][name]


class TestLibrary:
    @pytest.fixture
    def adapter(self):
        MockAdapter.DATA = copy.deepcopy(VALID_DATA)
        MockAdapter.FILES = copy.deepcopy(VALID_FILES)
        try:
            yield MockAdapter
        finally:
            MockAdapter.DATA = {}
            MockAdapter.FILES = {}
            MockAdapter.INDEX = 0

    @pytest.fixture
    def library(self, adapter):
        yield WorkItems(default_adapter=adapter)

    def test_autoload(self, library):
        # Called by Robot Framework listener
        library._start_suite(None, None)

        # Work item loaded using env variables
        env = library.current
        assert env is not None
        assert env.payload == VARIABLES_FIRST

    def test_autoload_disable(self, adapter):
        library = WorkItems(default_adapter=adapter, autoload=False)

        # Called by Robot Framework listener
        library._start_suite(None, None)
        assert library._current is None

    def test_keyword_get_input_work_item(self, library):
        first = library.get_input_work_item()
        assert first.payload == VARIABLES_FIRST
        assert first == library.current

        second = library.get_input_work_item()
        assert second.payload == VARIABLES_SECOND
        assert second == library.current

    def test_keyword_save_work_item(self, library):
        item = library.get_input_work_item()
        for key, value in VARIABLES_FIRST.items():
            MockAdapter.validate(item, key, value)

        modified = {"username": "changed", "address": "dude@company.com"}
        item.payload = modified

        library.save_work_item()
        for key, value in modified.items():
            MockAdapter.validate(item, key, value)

    def test_no_active_item(self):
        library = WorkItems(default_adapter=MockAdapter)
        with pytest.raises(RuntimeError) as err:
            library.save_work_item()

        assert str(err.value) == "No active work item"

    def test_list_variables(self, library):
        library.get_input_work_item()

        names = library.list_work_item_variables()

        assert len(names) == 2
        assert "username" in names
        assert "address" in names

    def test_get_variables(self, library):
        library.get_input_work_item()

        value = library.get_work_item_variable("username")
        assert value == "testguy"

        with pytest.raises(KeyError):
            library.get_work_item_variable("notexist")

    def test_get_variables_default(self, library):
        library.get_input_work_item()

        value = library.get_work_item_variable("username", default="doesntmatter")
        assert value == "testguy"

        value = library.get_work_item_variable("notexist", default="doesmatter")
        assert value == "doesmatter"

    def test_delete_variables(self, library):
        library.get_input_work_item()
        assert "username" in library.list_work_item_variables()

        library.delete_work_item_variables("username")
        assert "username" not in library.list_work_item_variables()

        library.delete_work_item_variables("doesntexist")

        with pytest.raises(KeyError):
            library.delete_work_item_variables("doesntexist", force=False)

    def test_delete_variables_single(self, library):
        library.get_input_work_item()

        assert "username" in library.list_work_item_variables()
        assert len(library.current.payload) == 2

        library.delete_work_item_variables("username")

        assert "username" not in library.list_work_item_variables()
        assert len(library.current.payload) == 1

    def test_delete_variables_multiple(self, library):
        library.get_input_work_item()

        names = library.list_work_item_variables()
        assert "username" in names
        assert "address" in names
        assert len(names) == 2

        library.delete_work_item_variables("username", "address")

        names = library.list_work_item_variables()
        assert "username" not in names
        assert "username" not in names
        assert len(names) == 0

    def test_delete_variables_unknown(self, library):
        library.get_input_work_item()
        assert len(library.list_work_item_variables()) == 2

        library.delete_work_item_variables("unknown-variable")
        assert len(library.list_work_item_variables()) == 2

        with pytest.raises(KeyError):
            library.delete_work_item_variables("unknown-variable", force=False)
        assert len(library.list_work_item_variables()) == 2

    def test_raw_payload(self, library):
        _ = library.get_input_work_item()
        _ = library.get_input_work_item()
        item = library.get_input_work_item()

        payload = library.get_work_item_payload()
        assert payload == [1, 2, 3]

        library.set_work_item_payload({"output": 0xBEEF})
        library.save_work_item()
        MockAdapter.validate(item, "output", 0xBEEF)

    def test_list_files(self, library):
        library.get_input_work_item()

        files = library.list_work_item_files()
        assert files == ["file1.txt", "file2.txt", "file3.png"]

    def test_get_file(self, library):
        library.get_input_work_item()

        with temp_filename() as path:
            result = library.get_work_item_file("file2.txt", path)
            with open(result) as fd:
                data = fd.read()

            assert is_equal_files(result, path)
            assert data == "data2"

    def test_get_file_notexist(self, library):
        library.get_input_work_item()

        with pytest.raises(FileNotFoundError):
            library.get_work_item_file("file5.txt")

    def test_add_file(self, library):
        item = library.get_input_work_item()

        with temp_filename(b"some-input-content") as path:
            library.add_work_item_file(path, "file4.txt")

            files = library.list_work_item_files()
            assert files == ["file1.txt", "file2.txt", "file3.png", "file4.txt"]
            assert "file4.txt" not in MockAdapter.FILES[item.id]

            library.save_work_item()
            assert MockAdapter.FILES[item.id]["file4.txt"] == b"some-input-content"

    def test_add_file_duplicate(self, library):
        item = library.get_input_work_item()

        def verify_files():
            files = library.list_work_item_files()
            assert files == ["file1.txt", "file2.txt", "file3.png", "file4.txt"]

        with temp_filename(b"some-input-content") as path:
            library.add_work_item_file(path, "file4.txt")
            assert "file4.txt" not in MockAdapter.FILES[item.id]
            verify_files()

            # Add duplicate for unsaved item
            library.add_work_item_file(path, "file4.txt")
            assert "file4.txt" not in MockAdapter.FILES[item.id]
            verify_files()

            library.save_work_item()
            assert MockAdapter.FILES[item.id]["file4.txt"] == b"some-input-content"
            verify_files()

            # Add duplicate for saved item
            library.add_work_item_file(path, "file4.txt")
            verify_files()

            library.save_work_item()
            verify_files()

    def test_add_file_notexist(self, library):
        library.get_input_work_item()

        with pytest.raises(FileNotFoundError):
            library.add_work_item_file("file5.txt", "doesnt-matter")

    def test_remove_file(self, library):
        item = library.get_input_work_item()

        library.remove_work_item_file("file2.txt")

        files = library.list_work_item_files()
        assert files == ["file1.txt", "file3.png"]
        assert "file2.txt" in MockAdapter.FILES[item.id]

        library.save_work_item()
        assert "file2.txt" not in MockAdapter.FILES[item.id]

    def test_remove_file_notexist(self, library):
        library.get_input_work_item()

        library.remove_work_item_file("file5.txt")

        with pytest.raises(FileNotFoundError):
            library.remove_work_item_file("file5.txt", missing_ok=False)

    def test_get_file_pattern(self, library):
        library.get_input_work_item()

        with tempfile.TemporaryDirectory() as outdir:
            file1 = os.path.join(outdir, "file1.txt")
            file2 = os.path.join(outdir, "file2.txt")

            paths = library.get_work_item_files("*.txt", outdir)
            assert is_equal_files(paths[0], file1)
            assert is_equal_files(paths[1], file2)
            assert os.path.exists(file1)
            assert os.path.exists(file2)

    def test_remove_file_pattern(self, library):
        item = library.get_input_work_item()

        library.remove_work_item_files("*.txt")

        files = library.list_work_item_files()
        assert files == ["file3.png"]
        assert list(MockAdapter.FILES[item.id]) == [
            "file1.txt",
            "file2.txt",
            "file3.png",
        ]

        library.save_work_item()

        files = library.list_work_item_files()
        assert files == ["file3.png"]
        assert list(MockAdapter.FILES[item.id]) == ["file3.png"]

    def test_clear_work_item(self, library):
        library.get_input_work_item()

        library.clear_work_item()
        library.save_work_item()

        assert library.get_work_item_payload() == {}
        assert library.list_work_item_files() == []

    def test_get_file_unsaved(self, library):
        library.get_input_work_item()

        with temp_filename(b"some-input-content") as path:
            library.add_work_item_file(path, "file4.txt")

            files = library.list_work_item_files()
            assert files == ["file1.txt", "file2.txt", "file3.png", "file4.txt"]
            assert "file4.txt" not in MockAdapter.FILES

            with tempfile.TemporaryDirectory() as outdir:
                names = ["file1.txt", "file2.txt", "file4.txt"]
                result = library.get_work_item_files("*.txt", outdir)
                expected = [os.path.join(outdir, name) for name in names]
                for lhs, rhs in zip(result, expected):
                    assert is_equal_files(lhs, rhs)
                with open(result[-1]) as fd:
                    assert fd.read() == "some-input-content"

    def test_get_file_unsaved_no_copy(self, library):
        library.get_input_work_item()

        with tempfile.TemporaryDirectory() as outdir:
            path = os.path.join(outdir, "nomove.txt")
            with open(path, "w") as fd:
                fd.write("my content")

            mtime = os.path.getmtime(path)
            library.add_work_item_file(path)

            files = library.list_work_item_files()
            assert files == ["file1.txt", "file2.txt", "file3.png", "nomove.txt"]

            paths = library.get_work_item_files("*.txt", outdir)
            assert is_equal_files(paths[-1], path)
            assert os.path.getmtime(path) == mtime

    def test_get_file_unsaved_relative(self, library):
        library.get_input_work_item()

        with tempfile.TemporaryDirectory() as outdir:
            curdir = os.getcwd()
            try:
                os.chdir(outdir)
                with open("nomove.txt", "w") as fd:
                    fd.write("my content")

                mtime = os.path.getmtime("nomove.txt")
                library.add_work_item_file(os.path.join(outdir, "nomove.txt"))

                files = library.list_work_item_files()
                assert files == ["file1.txt", "file2.txt", "file3.png", "nomove.txt"]

                paths = library.get_work_item_files("*.txt")
                assert is_equal_files(paths[-1], os.path.join(outdir, "nomove.txt"))
                assert os.path.getmtime("nomove.txt") == mtime
            finally:
                os.chdir(curdir)

    def test_get_file_no_matches(self, library):
        library.get_input_work_item()

        with tempfile.TemporaryDirectory() as outdir:
            paths = library.get_work_item_files("*.pdf", outdir)
            assert len(paths) == 0

    def test_create_output_work_item(self, library):
        input_item = library.get_input_work_item()
        output_item = library.create_output_work_item()

        assert output_item.id is None
        assert output_item.parent_id == input_item.id

    def test_create_output_work_item_no_input(self, library):
        with pytest.raises(RuntimeError):
            library.create_output_work_item()

    def test_custom_root(self, adapter):
        library = WorkItems(default_adapter=adapter, root="vars")
        item = library.get_input_work_item()

        variables = library.get_work_item_variables()
        assert variables == {}

        library.set_work_item_variables(cool="beans", yeah="boi")
        assert item.payload == {
            **VARIABLES_FIRST,
            "vars": {"cool": "beans", "yeah": "boi"},
        }

    @pytest.mark.parametrize("limit", [0, 1, 2, 3, 4])  # no, existing and over limit
    def test_iter_work_items(self, library, limit):
        usernames = []

        def func(a, b, r=3):
            assert a + b == r
            # Collects the "username" variable from the payload if provided and returns
            #   True if found, False otherwise.
            payload = library.get_work_item_payload()
            if not isinstance(payload, dict):
                return False

            username = payload.get("username")
            if username:
                usernames.append(username)

            return username is not None

        library.get_input_work_item()
        results = library.for_each_input_work_item(func, 1, 2, _limit=limit, r=3)

        expected_usernames = ["testguy", "another"]
        expected_results = [True, True, False]
        if limit:
            expected_usernames = expected_usernames[:limit]
            expected_results = expected_results[:limit]
        assert usernames == expected_usernames
        assert results == expected_results

    def test_iter_work_items_limit_and_state(self, library):
        def func():
            return 1

        # Pick one single item and make sure its state is set implicitly.
        results = library.for_each_input_work_item(func, _limit=1)
        assert len(results) == 1
        assert library.current.state is State.DONE

        def func2():
            library.release_input_work_item(State.FAILED)
            return 2

        # Pick-up the rest of the two inputs and set state explicitly.
        results = library.for_each_input_work_item(func2)
        assert len(results) == 2
        assert library.current.state is State.FAILED

    @pytest.mark.parametrize("collect_results", [True, False])
    def test_iter_work_items_collect_results(self, library, collect_results):
        def func():
            return 1

        library.get_input_work_item()
        results = library.for_each_input_work_item(
            func, _collect_results=collect_results
        )
        if collect_results:
            assert results == [1] * 3
        else:
            assert results is None

    @pytest.mark.parametrize("processed_items", [0, 1, 2, 3])
    def test_successive_work_items_iteration(self, library, processed_items):
        for _ in range(processed_items):
            library.get_input_work_item()
            library.release_input_work_item(State.DONE)

        def func():
            pass

        # Checks if all remaining input work items are processed once.
        results = library.for_each_input_work_item(func)
        assert len(results) == 3 - processed_items

        # Checks if there's no double processing of the last already processed item.
        results = library.for_each_input_work_item(func)
        assert len(results) == 0

    @pytest.fixture(
        params=[
            None,
            {"exception_type": "BUSINESS"},
            {
                "exception_type": "APPLICATION",
                "code": "ERR_UNEXPECTED",
                "message": "This is an unexpected error",
            },
            {
                "exception_type": "APPLICATION",
                "code": None,
                "message": "This is an unexpected error",
            },
            {
                "exception_type": "APPLICATION",
                "code": None,
                "message": None,
            },
            {
                "exception_type": None,
                "code": None,
                "message": None,
            },
            {
                "exception_type": None,
                "code": "APPLICATION",
                "message": None,
            },
            {
                "exception_type": None,
                "code": "",
                "message": "Not empty",
            },
        ]
    )
    def release_exception(self, request):
        exception = request.param or {}
        effect = nullcontext()
        success = True
        if not exception.get("exception_type") and any(
            map(lambda key: exception.get(key), ["code", "message"])
        ):
            effect = pytest.raises(RuntimeError)
            success = False
        return exception or None, effect, success

    def test_release_work_item_failed(self, library, release_exception):
        exception, effect, success = release_exception

        library.get_input_work_item()
        with effect:
            library.release_input_work_item(
                "FAILED", **(exception or {})
            )  # intentionally provide a string for the state
        if success:
            assert library.current.state == State.FAILED

        exception_type = (exception or {}).pop("exception_type", None)
        if exception_type:
            exception["type"] = Error(exception_type).value
            exception.setdefault("code", None)
            exception.setdefault("message", None)
        else:
            exception = None
        if success:
            assert library.adapter.releases == [
                ("workitem-id-first", State.FAILED, exception)
            ]

    @pytest.mark.parametrize("exception", [None, {"exception_type": Error.APPLICATION}])
    def test_release_work_item_done(self, library, exception):
        library.get_input_work_item()
        library.release_input_work_item(State.DONE, **(exception or {}))
        assert library.current.state is State.DONE
        assert library.adapter.releases == [
            # No exception sent for non failures.
            ("workitem-id-first", State.DONE, None)
        ]

    def test_auto_release_work_item(self, library):
        library.get_input_work_item()
        library.get_input_work_item()  # this automatically sets the state of the last

        assert library.current.state is None  # because the previous one has a state
        assert library.adapter.releases == [("workitem-id-first", State.DONE, None)]


class TestFileAdapter:
    """Tests the local dev env `FileAdapter` on Work Items."""

    @contextmanager
    def _input_work_items(self):
        with tempfile.TemporaryDirectory() as datadir:
            items_in = os.path.join(datadir, "items.json")
            with open(items_in, "w") as fd:
                json.dump(ITEMS_JSON, fd)
            with open(os.path.join(datadir, "file.txt"), "w") as fd:
                fd.write("some mock content")

            output_dir = os.path.join(datadir, "output_dir")
            os.makedirs(output_dir)
            items_out = os.path.join(output_dir, "items-out.json")

            yield items_in, items_out

    @pytest.fixture(
        params=[
            ("RPA_WORKITEMS_PATH", "N/A"),
            ("RPA_INPUT_WORKITEM_PATH", "RPA_OUTPUT_WORKITEM_PATH"),
        ]
    )
    def adapter(self, monkeypatch, request):
        with self._input_work_items() as (items_in, items_out):
            monkeypatch.setenv(request.param[0], items_in)
            monkeypatch.setenv(request.param[1], items_out)
            yield FileAdapter()

    @pytest.fixture
    def empty_adapter(self):
        # No work items i/o files nor envs set.
        return FileAdapter()

    def test_load_data(self, adapter):
        item_id = adapter.reserve_input()
        data = adapter.load_payload(item_id)
        assert data == {"a-key": "a-value"}

    def test_list_files(self, adapter):
        item_id = adapter.reserve_input()
        files = adapter.list_files(item_id)
        assert files == ["a-file"]

    def test_get_file(self, adapter):
        item_id = adapter.reserve_input()
        content = adapter.get_file(item_id, "a-file")
        assert content == b"some mock content"

    def test_add_file(self, adapter):
        item_id = adapter.reserve_input()
        adapter.add_file(
            item_id,
            "secondfile.txt",
            original_name="secondfile2.txt",
            content=b"somedata",
        )
        assert adapter.inputs[0]["files"]["secondfile.txt"] == "secondfile2.txt"
        assert os.path.isfile(Path(adapter.input_path).parent / "secondfile2.txt")

    def test_save_data_input(self, adapter):
        item_id = adapter.reserve_input()
        adapter.save_payload(item_id, {"key": "value"})
        with open(adapter.input_path) as fd:
            data = json.load(fd)
            assert data == [
                {"payload": {"key": "value"}, "files": {"a-file": "file.txt"}}
            ]

    def test_save_data_output(self, adapter):
        item_id = adapter.create_output("0", {})
        adapter.save_payload(item_id, {"key": "value"})

        output = os.getenv("RPA_OUTPUT_WORKITEM_PATH")
        if output:
            assert "output_dir" in output  # checks automatic dir creation
        else:
            output = Path(adapter.input_path).with_suffix(".output.json")

        assert os.path.isfile(output)
        with open(output) as fd:
            data = json.load(fd)
            assert data == [{"payload": {"key": "value"}, "files": {}}]

    def test_missing_file(self, monkeypatch):
        monkeypatch.setenv("RPA_WORKITEMS_PATH", "not-exist.json")
        adapter = FileAdapter()
        assert adapter.inputs == [{"payload": {}}]

    def test_empty_queue(self, monkeypatch):
        with tempfile.TemporaryDirectory() as datadir:
            items = os.path.join(datadir, "items.json")
            with open(items, "w") as fd:
                json.dump([], fd)

            monkeypatch.setenv("RPA_WORKITEMS_PATH", items)
            adapter = FileAdapter()
            assert adapter.inputs == [{"payload": {}}]

    def test_malformed_queue(self, monkeypatch):
        with tempfile.TemporaryDirectory() as datadir:
            items = os.path.join(datadir, "items.json")
            with open(items, "w") as fd:
                json.dump(["not-an-item"], fd)

            monkeypatch.setenv("RPA_WORKITEMS_PATH", items)
            adapter = FileAdapter()
            assert adapter.inputs == [{"payload": {}}]

    def test_without_items_paths(self, empty_adapter):
        assert empty_adapter.inputs == [{"payload": {}}]

        # Can't save inputs nor outputs since there's no path defined for them.
        with pytest.raises(RuntimeError):
            empty_adapter.save_payload("0", {"input": "value"})
        with pytest.raises(RuntimeError):
            _ = empty_adapter.output_path
        with pytest.raises(RuntimeError):
            empty_adapter.create_output("1", {"var": "some-value"})


class TestRobocorpAdapter:
    """Test control room API calls and retrying behaviour."""

    ENV = {
        "RC_WORKSPACE_ID": "1",
        "RC_PROCESS_RUN_ID": "2",
        "RC_ACTIVITY_RUN_ID": "3",
        "RC_WORKITEM_ID": "4",
        "RC_API_WORKITEM_HOST": "https://api.workitem.com",
        "RC_API_WORKITEM_TOKEN": "workitem-token",
        "RC_API_PROCESS_HOST": "https://api.process.com",
        "RC_API_PROCESS_TOKEN": "process-token",
        "RC_PROCESS_ID": "5",
    }

    HEADERS_WORKITEM = {
        "Authorization": f"Bearer {ENV['RC_API_WORKITEM_TOKEN']}",
        "Content-Type": "application/json",
    }
    HEADERS_PROCESS = {
        "Authorization": f"Bearer {ENV['RC_API_PROCESS_TOKEN']}",
        "Content-Type": "application/json",
    }

    @pytest.fixture
    def adapter(self, monkeypatch):
        for name, value in self.ENV.items():
            monkeypatch.setenv(name, value)

        with mock.patch("RPA.Robocorp.utils.requests.get") as mock_get, mock.patch(
            "RPA.Robocorp.utils.requests.post"
        ) as mock_post, mock.patch(
            "RPA.Robocorp.utils.requests.put"
        ) as mock_put, mock.patch(
            "RPA.Robocorp.utils.requests.delete"
        ) as mock_delete, mock.patch(
            "time.sleep", return_value=None
        ):
            self.mock_get = mock_get
            self.mock_post = mock_post
            self.mock_put = mock_put
            self.mock_delete = mock_delete
            yield RobocorpAdapter()

    def test_reserve_input(self, adapter):
        initial_item_id = adapter.reserve_input()
        assert initial_item_id == self.ENV["RC_WORKITEM_ID"]

        self.mock_post.return_value.json.return_value = {"workItemId": "44"}
        reserved_item_id = adapter.reserve_input()
        assert reserved_item_id == "44"

        url = "https://api.process.com/process-v1/workspaces/1/processes/5/runs/2/robotRuns/3/reserve-next-work-item"
        self.mock_post.assert_called_once_with(url, headers=self.HEADERS_PROCESS)

    @pytest.mark.parametrize(
        "exception", [None, {"type": "BUSINESS", "code": "ERR_UNEXPECTED"}]
    )
    def test_release_input(self, adapter, exception):
        item_id = "26"
        adapter.release_input(item_id, State.FAILED, exception=exception)

        url = "https://api.process.com/process-v1/workspaces/1/processes/5/runs/2/robotRuns/3/release-work-item"
        body = {
            "workItemId": item_id,
            "state": State.FAILED.value,
        }
        if exception:
            body["exception"] = exception
        self.mock_post.assert_called_once_with(
            url, headers=self.HEADERS_PROCESS, json=body
        )

    def test_load_payload(self, adapter):
        item_id = "4"
        expected_payload = {"name": "value"}
        self.mock_get.return_value.json.return_value = expected_payload
        payload = adapter.load_payload(item_id)
        assert payload == expected_payload

        response = self.mock_get.return_value
        response.ok = False
        response.status_code = 404
        payload = adapter.load_payload(item_id)
        assert payload == {}

    def test_save_payload(self, adapter):
        item_id = "1993"
        payload = {"Cosmin": "Poieana"}
        adapter.save_payload(item_id, payload)

        url = f"https://api.workitem.com/json-v1/workspaces/1/workitems/{item_id}/data"
        self.mock_put.assert_called_once_with(
            url, headers=self.HEADERS_WORKITEM, json=payload
        )

    def test_remove_file(self, adapter):
        item_id = "44"
        name = "procrastination.txt"
        file_id = "88"
        self.mock_get.return_value.json.return_value = [
            {"fileName": name, "fileId": file_id}
        ]
        adapter.remove_file(item_id, name)

        url = f"https://api.workitem.com/json-v1/workspaces/1/workitems/{item_id}/files/{file_id}"
        self.mock_delete.assert_called_once_with(url, headers=self.HEADERS_WORKITEM)

    def test_list_files(self, adapter):
        expected_files = ["just.py", "mark.robot", "it.txt"]
        self.mock_get.return_value.json.return_value = [
            {"fileName": expected_files[0], "fileId": "1"},
            {"fileName": expected_files[1], "fileId": "2"},
            {"fileName": expected_files[2], "fileId": "3"},
        ]
        files = adapter.list_files("4")
        assert files == expected_files

    @staticmethod
    def _failing_response(request):
        resp = mock.MagicMock()
        resp.ok = False
        resp.json.return_value = request.param[0]
        resp.raise_for_status.side_effect = request.param[1]
        return resp

    @pytest.fixture(
        params=[
            # Requests response attribute values for: `.json()`, `.raise_for_status()`
            ({}, None),
            (None, HTTPError()),
        ]
    )
    def failing_response(self, request):
        return self._failing_response(request)

    @pytest.mark.parametrize(
        "status_code,call_count",
        [
            # Retrying enabled:
            (429, 5),
            # Retrying disabled:
            (400, 1),
            (401, 1),
            (403, 1),
            (409, 1),
            (500, 1),
        ],
    )
    def test_list_files_retrying(
        self, adapter, failing_response, status_code, call_count
    ):
        self.mock_get.return_value = failing_response
        failing_response.status_code = status_code

        with pytest.raises(RequestsHTTPError) as exc_info:
            adapter.list_files("4")
        assert exc_info.value.status_code == status_code
        assert self.mock_get.call_count == call_count  # tried once or 5 times in a row

    @pytest.fixture(
        params=[
            # Requests response attribute values for: `.json()`, `.raise_for_status()`
            ({"error": {"code": "ERR_UNEXPECTED"}}, None),  # normal response
            ('{"error": {"code": "ERR_UNEXPECTED"}}', None),  # double serialized
            (r'"{\"error\": {\"code\": \"ERR_UNEXPECTED\"}}"', None),  # triple
            ('[{"some": "value"}]', HTTPError()),  # double serialized list
        ]
    )
    def failing_deserializing_response(self, request):
        return self._failing_response(request)

    def test_bad_response_payload(self, adapter, failing_deserializing_response):
        self.mock_get.return_value = failing_deserializing_response
        failing_deserializing_response.status_code = 429

        with pytest.raises(RequestsHTTPError) as exc_info:
            adapter.list_files("4")

        err = "ERR_UNEXPECTED"
        call_count = 1
        if err not in str(failing_deserializing_response.json.return_value):
            err = "Error"  # default error message in the absence of it
            call_count = 5
        assert exc_info.value.status_code == 429
        assert exc_info.value.status_message == err
        assert self.mock_get.call_count == call_count
