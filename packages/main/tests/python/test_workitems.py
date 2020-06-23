import copy
import pytest
from RPA.Robocloud.Items import BaseAdapter, Items


VARIABLES_FIRST = {"username": "testguy", "address": "guy@company.com"}
VARIABLES_SECOND = {"username": "another", "address": "dude@company.com"}

VALID_DATABASE = {
    ("workspace-id", "workitem-id-first"): {"variables": VARIABLES_FIRST},
    ("workspace-id", "workitem-id-second"): {"variables": VARIABLES_SECOND},
}


class MockAdapter(BaseAdapter):
    DATABASE = {}

    @classmethod
    def validate(cls, item, key, val):
        data = cls.DATABASE.get((item.workspace_id, item.item_id))
        assert data is not None
        assert data[key] == val

    def save(self, workspace_id, item_id, data):
        self.DATABASE[(workspace_id, item_id)] = data

    def load(self, workspace_id, item_id):
        return self.DATABASE.get((workspace_id, item_id), {})


@pytest.fixture
def valid_adapter(monkeypatch):
    monkeypatch.setenv("RC_WORKSPACE_ID", "workspace-id")
    monkeypatch.setenv("RC_WORKITEM_ID", "workitem-id-first")
    MockAdapter.DATABASE = copy.deepcopy(VALID_DATABASE)
    try:
        yield MockAdapter
    finally:
        MockAdapter.DATABASE = {}


def test_no_env(monkeypatch):
    monkeypatch.delenv("RC_WORKSPACE_ID", raising=False)
    monkeypatch.delenv("RC_WORKITEM_ID", raising=False)

    lib = Items(default_adapter=MockAdapter)
    assert lib.current is None


def test_load_env(valid_adapter):
    lib = Items(default_adapter=valid_adapter)

    # Called by Robot Framework listener
    lib._start_suite(None, None)

    # Work item loaded using env variables
    env = lib.current
    assert env is not None
    assert env.data["variables"] == VARIABLES_FIRST


def test_load_env_disable(valid_adapter):
    lib = Items(load_env=False, default_adapter=valid_adapter)

    # Called by Robot Framework listener
    lib._start_suite(None, None)
    assert lib.current is None


def test_keyword_load_work_item(valid_adapter):
    lib = Items(default_adapter=valid_adapter)

    item = lib.load_work_item("workspace-id", "workitem-id-second")
    assert item.data["variables"] == VARIABLES_SECOND
    assert item == lib.current


def test_keyword_save_work_item(valid_adapter):
    lib = Items(default_adapter=valid_adapter)
    item = lib.load_work_item("workspace-id", "workitem-id-second")
    MockAdapter.validate(item, "variables", VARIABLES_SECOND)

    modified = {"username": "changed", "address": "dude@company.com"}
    item.data["variables"] = modified

    lib.save_work_item()
    MockAdapter.validate(item, "variables", modified)


def test_no_active_item():
    lib = Items(default_adapter=MockAdapter)
    assert lib.current is None

    with pytest.raises(AssertionError) as err:
        lib.save_work_item()

    assert str(err.value) == "No active work item"


def test_list_variables(valid_adapter):
    lib = Items(default_adapter=valid_adapter)
    lib.load_work_item("workspace-id", "workitem-id-second")

    names = lib.list_work_item_variables()

    assert len(names) == 2
    assert "username" in names
    assert "address" in names


def test_delete_variables(valid_adapter):
    lib = Items(default_adapter=valid_adapter)
    lib.load_work_item("workspace-id", "workitem-id-second")

    assert "username" in lib.list_work_item_variables()
    lib.delete_work_item_variables("username")
    assert "username" not in lib.list_work_item_variables()

    lib.delete_work_item_variables("doesntexist")

    with pytest.raises(KeyError):
        lib.delete_work_item_variables("doesntexist", force=False)


def test_delete_variables_multiple(valid_adapter):
    lib = Items(default_adapter=valid_adapter)
    lib.load_work_item("workspace-id", "workitem-id-second")

    assert "username" in lib.list_work_item_variables()
    assert len(lib.current["variables"]) == 2

    lib.delete_work_item_variables("username")

    assert "username" not in lib.list_work_item_variables()
    assert len(lib.current["variables"]) == 1


def test_delete_variables_multiple(valid_adapter):
    lib = Items(default_adapter=valid_adapter)
    lib.load_work_item("workspace-id", "workitem-id-second")

    names = lib.list_work_item_variables()
    assert "username" in names
    assert "address" in names
    assert len(names) == 2

    lib.delete_work_item_variables("username", "address")

    names = lib.list_work_item_variables()
    assert "username" not in names
    assert "username" not in names
    assert len(names) == 0


def test_delete_variables_unknown(valid_adapter):
    lib = Items(default_adapter=valid_adapter)
    lib.load_work_item("workspace-id", "workitem-id-second")

    assert len(lib.list_work_item_variables()) == 2

    lib.delete_work_item_variables("unknown-variable")
    assert len(lib.list_work_item_variables()) == 2

    with pytest.raises(KeyError):
        lib.delete_work_item_variables("unknown-variable", force=False)
    assert len(lib.list_work_item_variables()) == 2
