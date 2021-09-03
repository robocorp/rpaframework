import copy
import json
import os
import pytest
import tempfile
from contextlib import contextmanager
from pathlib import Path
from RPA.Robocorp.WorkItems import BaseAdapter, FileAdapter, WorkItems


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

    @classmethod
    def validate(cls, item, key, val):
        data = cls.DATA.get(item.id)
        assert data is not None
        assert data[key] == val

    def get_input(self) -> str:
        idx = self.INDEX
        self.INDEX += 1
        return list(self.DATA.keys())[idx]

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

    def add_file(self, item_id, name, content):
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

    def test_delete_variables_multiple(self, library):
        library.get_input_work_item()

        assert "username" in library.list_work_item_variables()
        assert len(library.current["variables"]) == 2

        library.delete_work_item_variables("username")

        assert "username" not in library.list_work_item_variables()
        assert len(library.current["variables"]) == 1

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


class TestFileAdapter:
    @pytest.fixture
    def adapter(self, monkeypatch):
        with tempfile.TemporaryDirectory() as datadir:
            items = os.path.join(datadir, "items.json")
            with open(items, "w") as fd:
                json.dump(ITEMS_JSON, fd)
            with open(os.path.join(datadir, "file.txt"), "w") as fd:
                fd.write("some mock content")

            monkeypatch.setenv("RPA_WORKITEMS_PATH", items)
            yield FileAdapter()

    def test_load_data(self, adapter):
        item_id = adapter.get_input()
        data = adapter.load_payload(item_id)
        assert data == {"a-key": "a-value"}

    def test_list_files(self, adapter):
        item_id = adapter.get_input()
        files = adapter.list_files(item_id)
        assert files == ["a-file"]

    def test_get_file(self, adapter):
        item_id = adapter.get_input()
        content = adapter.get_file(item_id, "a-file")
        assert content == b"some mock content"

    def test_add_file(self, adapter):
        item_id = adapter.get_input()
        adapter.add_file(item_id, "secondfile2.txt", b"somedata")
        assert adapter.inputs[0]["files"]["secondfile2.txt"] == "secondfile2.txt"
        assert os.path.isfile(Path(adapter.path).parent / "secondfile2.txt")

    def test_save_data_input(self, adapter):
        item_id = adapter.get_input()
        adapter.save_payload(item_id, {"key": "value"})
        with open(adapter.path) as fd:
            data = json.load(fd)
            assert data == [
                {"payload": {"key": "value"}, "files": {"a-file": "file.txt"}}
            ]

    def test_save_data_output(self, adapter):
        item_id = adapter.create_output(0, {})
        adapter.save_payload(item_id, {"key": "value"})

        output = Path(adapter.path).with_suffix(".output.json")
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
