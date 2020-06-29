import copy
import io
import json
import pytest
from RPA.core import locators


CONTENT = [
    {
        "id": 0,
        "name": "RobotSpareBin.Username",
        "type": "browser",
        "strategy": "id",
        "value": "username",
        "source": "https://robotsparebinindustries.com/",
    },
    {
        "id": 1,
        "name": "RobotSpareBin.Password",
        "type": "browser",
        "strategy": "id",
        "value": "password",
        "source": "https://robotsparebinindustries.com/",
    },
    {
        "id": 2,
        "name": "RobotSpareBin.Login",
        "type": "browser",
        "strategy": "class",
        "value": "btn-primary",
        "source": "https://robotsparebinindustries.com/",
    },
]


def to_stream(data):
    return io.StringIO(json.dumps(data))


@pytest.fixture
def valid_database():
    database = locators.LocatorsDatabase(to_stream(CONTENT))
    database.load()
    return database


def test_load_ok():
    database = locators.LocatorsDatabase(to_stream(CONTENT))
    database.load()

    assert database.error is None
    assert len(database.locators) == 3


def test_load_empty():
    database = locators.LocatorsDatabase(to_stream({}))
    database.load()

    assert database.error is None
    assert len(database.locators) == 0


def test_load_malformed():
    stream = io.StringIO("not-a-json{]}\\''")

    database = locators.LocatorsDatabase(stream)
    database.load()

    assert database.error is not None
    assert len(database.error) == 2
    assert len(database.locators) == 0


def test_load_missing():
    database = locators.LocatorsDatabase("not/a/valid/path")
    database.load()

    assert database.error is None
    assert len(database.locators) == 0


def test_duplicate_id():
    content = copy.deepcopy(CONTENT)
    content[0]["id"] = 2

    database = locators.LocatorsDatabase(to_stream(content))
    database.load()

    assert database.error is not None
    assert len(database.locators) == 0


def test_duplicate_name():
    content = copy.deepcopy(CONTENT)
    content[0]["name"] = content[2]["name"]

    database = locators.LocatorsDatabase(to_stream(content))
    database.load()

    assert database.error is not None
    assert len(database.locators) == 0


def test_missing_name():
    content = copy.deepcopy(CONTENT)
    del content[1]["name"]

    database = locators.LocatorsDatabase(to_stream(content))
    database.load()

    assert database.error is not None
    assert len(database.locators) == 0


def test_find_by_id(valid_database):
    locator = valid_database.find_by_id(1)
    assert locator["id"] == 1
    assert locator["name"] == "RobotSpareBin.Password"


def test_find_by_name(valid_database):
    locator = valid_database.find_by_name("RobotSpareBin.Password")
    assert locator["id"] == 1
    assert locator["name"] == "RobotSpareBin.Password"


def test_reset_error():
    database = locators.LocatorsDatabase()

    database.path = io.StringIO("some-error")
    database.load()

    assert database.error is not None
    assert len(database.locators) == 0

    database.path = to_stream(CONTENT)
    database.load()

    assert database.error is None
    assert len(database.locators) == 3


def test_update(valid_database):
    assert len(valid_database.locators) == 3
    assert valid_database.locators[1]["id"] == 1
    assert valid_database.locators[1]["name"] == "RobotSpareBin.Password"

    valid_database.path = io.StringIO()
    valid_database.update(
        1, {"id": 1, "name": "OtherName", "type": "OtherType", "value": "OtherValue"}
    )

    assert len(valid_database.locators) == 3
    assert valid_database.locators[1]["id"] == 1
    assert valid_database.locators[1]["name"] == "OtherName"


def test_update_missing(valid_database):
    valid_database.path = io.StringIO()

    with pytest.raises(locators.ValidationError):
        valid_database.update(
            4,
            {"id": 4, "name": "OtherName", "type": "OtherType", "value": "OtherValue"},
        )
