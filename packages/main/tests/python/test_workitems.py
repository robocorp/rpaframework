import copy
import pytest
from RPA.Robocloud.Items import BaseAdapter, Items


VARIABLES_FIRST = {"username": "testguy", "address": "guy@company.com"}
VARIABLES_SECOND = {"username": "another", "address": "dude@company.com"}

VALID_DATABASE = {
    ("workspace-id", "workitem-id-first"): {"variables": VARIABLES_FIRST},
    ("workspace-id", "workitem-id-second"): {"variables": VARIABLES_SECOND},
    ("workspace-id", "workitem-id-custom"): {"input": 0xCAFE},
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
def adapter(monkeypatch):
    monkeypatch.setenv("RC_WORKSPACE_ID", "workspace-id")
    monkeypatch.setenv("RC_WORKITEM_ID", "workitem-id-first")
    MockAdapter.DATABASE = copy.deepcopy(VALID_DATABASE)
    try:
        yield MockAdapter
    finally:
        MockAdapter.DATABASE = {}


@pytest.fixture
def library(adapter):
    yield Items(default_adapter=adapter)


def test_no_env(monkeypatch):
    monkeypatch.delenv("RC_WORKSPACE_ID", raising=False)
    monkeypatch.delenv("RC_WORKITEM_ID", raising=False)

    library = Items(default_adapter=MockAdapter)
    assert library.current is None


def test_load_env(library):
    # Called by Robot Framework listener
    library._start_suite(None, None)

    # Work item loaded using env variables
    env = library.current
    assert env is not None
    assert env.data["variables"] == VARIABLES_FIRST


def test_load_env_disable(adapter):
    library = Items(default_adapter=adapter, load_env=False)

    # Called by Robot Framework listener
    library._start_suite(None, None)
    assert library.current is None


def test_keyword_load_work_item(library):
    item = library.load_work_item("workspace-id", "workitem-id-second")
    assert item.workspace_id == "workspace-id"
    assert item.item_id == "workitem-id-second"
    assert item.data["variables"] == VARIABLES_SECOND
    assert item == library.current


def test_keyword_save_work_item(library):
    item = library.load_work_item("workspace-id", "workitem-id-second")
    MockAdapter.validate(item, "variables", VARIABLES_SECOND)

    modified = {"username": "changed", "address": "dude@company.com"}
    item.data["variables"] = modified

    library.save_work_item()
    MockAdapter.validate(item, "variables", modified)


def test_no_active_item():
    library = Items(default_adapter=MockAdapter)
    assert library.current is None

    with pytest.raises(AssertionError) as err:
        library.save_work_item()

    assert str(err.value) == "No active work item"


def test_list_variables(library):
    library.load_work_item("workspace-id", "workitem-id-second")

    names = library.list_work_item_variables()

    assert len(names) == 2
    assert "username" in names
    assert "address" in names


def test_get_variables(library):
    library.load_work_item("workspace-id", "workitem-id-second")

    value = library.get_work_item_variable("username")
    assert value == "another"

    with pytest.raises(KeyError):
        library.get_work_item_variable("notexist")


def test_get_variables_default(library):
    library.load_work_item("workspace-id", "workitem-id-second")

    value = library.get_work_item_variable("username", default="doesntmatter")
    assert value == "another"

    value = library.get_work_item_variable("notexist", default="doesmatter")
    assert value == "doesmatter"


def test_delete_variables(library):
    library.load_work_item("workspace-id", "workitem-id-second")
    assert "username" in library.list_work_item_variables()

    library.delete_work_item_variables("username")
    assert "username" not in library.list_work_item_variables()

    library.delete_work_item_variables("doesntexist")

    with pytest.raises(KeyError):
        library.delete_work_item_variables("doesntexist", force=False)


def test_delete_variables_multiple(library):
    library.load_work_item("workspace-id", "workitem-id-second")

    assert "username" in library.list_work_item_variables()
    assert len(library.current["variables"]) == 2

    library.delete_work_item_variables("username")

    assert "username" not in library.list_work_item_variables()
    assert len(library.current["variables"]) == 1


def test_delete_variables_multiple(library):
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


def test_delete_variables_unknown(library):
    library.load_work_item("workspace-id", "workitem-id-second")
    assert len(library.list_work_item_variables()) == 2

    library.delete_work_item_variables("unknown-variable")
    assert len(library.list_work_item_variables()) == 2

    with pytest.raises(KeyError):
        library.delete_work_item_variables("unknown-variable", force=False)
    assert len(library.list_work_item_variables()) == 2


def test_raw_payload(library):
    item = library.load_work_item("workspace-id", "workitem-id-custom")
    MockAdapter.validate(item, "input", 0xCAFE)

    payload = library.get_work_item_payload()
    assert payload == {"input": 0xCAFE}

    library.set_work_item_payload({"output": 0xBEEF})
    library.save_work_item()
    MockAdapter.validate(item, "output", 0xBEEF)
