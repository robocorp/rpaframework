import copy
import pytest
from RPA.Robocloud.Items import BaseAdapter, Items


VALID_DATABASE = {
    ("test-ws", "test-item"): {"username": "testguy", "address": "guy@company.com"},
    ("test-ws", "second-item"): {"username": "another", "address": "dude@company.com"},
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
    monkeypatch.setenv("RC_WORKSPACE_ID", "test-ws")
    monkeypatch.setenv("RC_WORKITEM_ID", "test-item")
    MockAdapter.DATABASE = copy.deepcopy(VALID_DATABASE)
    yield MockAdapter
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
    assert env.data["username"] == "testguy"


def test_load_env_disable(valid_adapter):
    lib = Items(load_env=False, default_adapter=valid_adapter)

    # Called by Robot Framework listener
    lib._start_suite(None, None)
    assert lib.current is None


def test_keyword_load_item(valid_adapter):
    lib = Items(default_adapter=valid_adapter)

    item = lib.load_work_item("test-ws", "second-item")
    assert item.data["username"] == "another"
    assert item == lib.current


def test_keyword_save_item(valid_adapter):
    lib = Items(default_adapter=valid_adapter)
    item = lib.load_work_item("test-ws", "second-item")
    MockAdapter.validate(item, "username", "another")

    item.data["username"] = "changed"
    lib.save_work_item()
    MockAdapter.validate(item, "username", "changed")


def test_keyword_no_active_item():
    lib = Items(default_adapter=MockAdapter)
    assert lib.current is None

    with pytest.raises(AssertionError) as err:
        lib.save_work_item()

    assert str(err.value) == "No active work item"
