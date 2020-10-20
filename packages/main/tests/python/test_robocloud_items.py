import copy
import json
import os
import pytest
import tempfile
from contextlib import contextmanager
from pathlib import Path
from RPA.Robocloud.Items import BaseAdapter, FileAdapter, Items


VARIABLES_FIRST = {"username": "testguy", "address": "guy@company.com"}
VARIABLES_SECOND = {"username": "another", "address": "dude@company.com"}

VALID_DATABASE = {
    ("workspace-id", "workitem-id-first"): {"variables": VARIABLES_FIRST},
    ("workspace-id", "workitem-id-second"): {"variables": VARIABLES_SECOND},
    ("workspace-id", "workitem-id-custom"): {"input": 0xCAFE},
}

VALID_FILES = {"file1.txt": b"data1", "file2.txt": b"data2", "file3.png": b"data3"}

ITEMS_JSON = {"1": {"1": {"key": "value"}}}


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
    DATABASE = {}
    FILES = {}

    @classmethod
    def validate(cls, item, key, val):
        data = cls.DATABASE.get((item.workspace_id, item.item_id))
        assert data is not None
        assert data[key] == val

    def load_data(self):
        return self.DATABASE.get((self.workspace_id, self.item_id), {})

    def save_data(self, data):
        self.DATABASE[(self.workspace_id, self.item_id)] = data

    def list_files(self):
        return list(self.FILES.keys())

    def add_file(self, name, content):
        self.FILES[name] = content

    def get_file(self, name):
        assert name in self.FILES
        return self.FILES[name]

    def remove_file(self, name):
        assert name in self.FILES
        del self.FILES[name]


class TestLibrary:
    @pytest.fixture
    def adapter(self, monkeypatch):
        monkeypatch.setenv("RC_WORKSPACE_ID", "workspace-id")
        monkeypatch.setenv("RC_WORKITEM_ID", "workitem-id-first")
        MockAdapter.DATABASE = copy.deepcopy(VALID_DATABASE)
        MockAdapter.FILES = copy.deepcopy(VALID_FILES)
        try:
            yield MockAdapter
        finally:
            MockAdapter.DATABASE = {}
            MockAdapter.FILES = {}

    @pytest.fixture
    def library(self, adapter):
        yield Items(default_adapter=adapter)

    def test_no_env(self, monkeypatch):
        monkeypatch.delenv("RC_WORKSPACE_ID", raising=False)
        monkeypatch.delenv("RC_WORKITEM_ID", raising=False)

        library = Items(default_adapter=MockAdapter)
        assert library.current is None

    def test_load_env(self, library):
        # Called by Robot Framework listener
        library._start_suite(None, None)

        # Work item loaded using env variables
        env = library.current
        assert env is not None
        assert env.data["variables"] == VARIABLES_FIRST

    def test_load_env_disable(self, adapter):
        library = Items(default_adapter=adapter, load_env=False)

        # Called by Robot Framework listener
        library._start_suite(None, None)
        assert library.current is None

    def test_keyword_load_work_item(self, library):
        item = library.load_work_item("workspace-id", "workitem-id-second")
        assert item.workspace_id == "workspace-id"
        assert item.item_id == "workitem-id-second"
        assert item.data["variables"] == VARIABLES_SECOND
        assert item == library.current

    def test_keyword_save_work_item(self, library):
        item = library.load_work_item("workspace-id", "workitem-id-second")
        MockAdapter.validate(item, "variables", VARIABLES_SECOND)

        modified = {"username": "changed", "address": "dude@company.com"}
        item.data["variables"] = modified

        library.save_work_item()
        MockAdapter.validate(item, "variables", modified)

    def test_no_active_item(
        self,
    ):
        library = Items(default_adapter=MockAdapter)
        assert library.current is None

        with pytest.raises(AssertionError) as err:
            library.save_work_item()

        assert str(err.value) == "No active work item"

    def test_list_variables(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        names = library.list_work_item_variables()

        assert len(names) == 2
        assert "username" in names
        assert "address" in names

    def test_get_variables(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        value = library.get_work_item_variable("username")
        assert value == "another"

        with pytest.raises(KeyError):
            library.get_work_item_variable("notexist")

    def test_get_variables_default(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        value = library.get_work_item_variable("username", default="doesntmatter")
        assert value == "another"

        value = library.get_work_item_variable("notexist", default="doesmatter")
        assert value == "doesmatter"

    def test_delete_variables(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")
        assert "username" in library.list_work_item_variables()

        library.delete_work_item_variables("username")
        assert "username" not in library.list_work_item_variables()

        library.delete_work_item_variables("doesntexist")

        with pytest.raises(KeyError):
            library.delete_work_item_variables("doesntexist", force=False)

    def test_delete_variables_multiple(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        assert "username" in library.list_work_item_variables()
        assert len(library.current["variables"]) == 2

        library.delete_work_item_variables("username")

        assert "username" not in library.list_work_item_variables()
        assert len(library.current["variables"]) == 1

    def test_delete_variables_multiple(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

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
        library.load_work_item("workspace-id", "workitem-id-second")
        assert len(library.list_work_item_variables()) == 2

        library.delete_work_item_variables("unknown-variable")
        assert len(library.list_work_item_variables()) == 2

        with pytest.raises(KeyError):
            library.delete_work_item_variables("unknown-variable", force=False)
        assert len(library.list_work_item_variables()) == 2

    def test_raw_payload(self, library):
        item = library.load_work_item("workspace-id", "workitem-id-custom")
        MockAdapter.validate(item, "input", 0xCAFE)

        payload = library.get_work_item_payload()
        assert payload == {"input": 0xCAFE}

        library.set_work_item_payload({"output": 0xBEEF})
        library.save_work_item()
        MockAdapter.validate(item, "output", 0xBEEF)

    def test_list_files(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        files = library.list_work_item_files()
        assert files == ["file1.txt", "file2.txt", "file3.png"]

    def test_get_file(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        with temp_filename() as path:
            result = library.get_work_item_file("file2.txt", path)
            with open(result) as fd:
                data = fd.read()

            assert is_equal_files(result, path)
            assert data == "data2"

    def test_get_file_notexist(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        with pytest.raises(FileNotFoundError):
            library.get_work_item_file("file5.txt")

    def test_add_file(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        with temp_filename(b"some-input-content") as path:
            library.add_work_item_file(path, "file4.txt")

            files = library.list_work_item_files()
            assert files == ["file1.txt", "file2.txt", "file3.png", "file4.txt"]
            assert "file4.txt" not in MockAdapter.FILES

            library.save_work_item()
            assert MockAdapter.FILES["file4.txt"] == b"some-input-content"

    def test_add_file_duplicate(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        def verify_files():
            files = library.list_work_item_files()
            assert files == ["file1.txt", "file2.txt", "file3.png", "file4.txt"]

        with temp_filename(b"some-input-content") as path:
            library.add_work_item_file(path, "file4.txt")
            assert "file4.txt" not in MockAdapter.FILES
            verify_files()

            # Add duplicate for unsaved item
            library.add_work_item_file(path, "file4.txt")
            assert "file4.txt" not in MockAdapter.FILES
            verify_files()

            library.save_work_item()
            assert MockAdapter.FILES["file4.txt"] == b"some-input-content"
            verify_files()

            # Add duplicate for saved item
            library.add_work_item_file(path, "file4.txt")
            verify_files()

            library.save_work_item()
            verify_files()

    def test_add_file_notexist(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        with pytest.raises(FileNotFoundError):
            library.add_work_item_file("file5.txt", "doesnt-matter")

    def test_remove_file(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        library.remove_work_item_file("file2.txt")

        files = library.list_work_item_files()
        assert files == ["file1.txt", "file3.png"]
        assert "file2.txt" in MockAdapter.FILES

        library.save_work_item()
        assert "file2.txt" not in MockAdapter.FILES

    def test_remove_file_notexist(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        library.remove_work_item_file("file5.txt")

        with pytest.raises(FileNotFoundError):
            library.remove_work_item_file("file5.txt", missing_ok=False)

    def test_get_file_pattern(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        with tempfile.TemporaryDirectory() as outdir:
            file1 = os.path.join(outdir, "file1.txt")
            file2 = os.path.join(outdir, "file2.txt")

            paths = library.get_work_item_files("*.txt", outdir)
            assert is_equal_files(paths[0], file1)
            assert is_equal_files(paths[1], file2)
            assert os.path.exists(file1)
            assert os.path.exists(file2)

    def test_remove_file_pattern(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        library.remove_work_item_files("*.txt")

        files = library.list_work_item_files()
        assert files == ["file3.png"]
        assert list(MockAdapter.FILES) == ["file1.txt", "file2.txt", "file3.png"]

        library.save_work_item()

        files = library.list_work_item_files()
        assert files == ["file3.png"]
        assert list(MockAdapter.FILES) == ["file3.png"]

    def test_clear_work_item(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

        library.clear_work_item()
        library.save_work_item()

        assert library.get_work_item_payload() == {}
        assert library.list_work_item_files() == []

    def test_get_file_unsaved(self, library):
        library.load_work_item("workspace-id", "workitem-id-second")

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
        library.load_work_item("workspace-id", "workitem-id-second")

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
        library.load_work_item("workspace-id", "workitem-id-second")

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
        library.load_work_item("workspace-id", "workitem-id-second")

        with tempfile.TemporaryDirectory() as outdir:
            paths = library.get_work_item_files("*.pdf", outdir)
            assert len(paths) == 0


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
            yield FileAdapter(workspace_id="1", item_id="1")

    def test_load_data(self, adapter):
        data = adapter.load_data()
        assert data == {"key": "value"}

    def test_list_files(self, adapter):
        files = adapter.list_files()
        assert files == ["file.txt"]

    def test_get_file(self, adapter):
        content = adapter.get_file("file.txt")
        assert content == b"some mock content"

    def test_add_file(self, adapter):
        adapter.add_file("secondfile2.txt", b"somedata")
        assert os.path.isfile(Path(adapter.path).parent / "secondfile2.txt")
