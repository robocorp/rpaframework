import copy
import io
import json
import pytest
from RPA.core.locators import (
    TYPES,
    LocatorsDatabase,
    Locator,
    BrowserDOM,
    ImageTemplate,
    sanitize_name,
)


def to_stream(data):
    return io.StringIO(json.dumps(data))


LEGACY = [
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

CURRENT = {
    "RobotSpareBin.Username": {
        "type": "browser",
        "strategy": "id",
        "value": "username",
        "source": "https://robotsparebinindustries.com/",
    },
    "RobotSpareBin.Password": {
        "type": "browser",
        "strategy": "id",
        "value": "password",
        "source": "https://robotsparebinindustries.com/",
    },
    "RobotSpareBin.Login": {
        "type": "browser",
        "strategy": "class",
        "value": "btn-primary",
        "source": "https://robotsparebinindustries.com/",
    },
}

ERRORS = {
    "MissingField": {
        "type": "browser",
        "strategy": "id",
        "source": "https://robotsparebinindustries.com/",
    },
    "DuplicateSanitized?": {
        "type": "browser",
        "strategy": "id",
        "value": "password",
        "source": "https://robotsparebinindustries.com/",
    },
    "DuplicateSanitized!": {
        "type": "browser",
        "strategy": "class",
        "value": "btn-primary",
        "source": "https://robotsparebinindustries.com/",
    },
}


NAMES = [
    ("Name", "name"),
    ("name", "name"),
    ("with space", "with-space"),
    ("multiple   spaces", "multiple-spaces"),
    ("     ", ""),
    ("123123", "123123"),
    ("what??", "what"),
    ("!! !!", ""),
    ("  strip  ", "strip"),
    ("Google.Logo", "google-logo"),
    (".Multiple..periods...again.", "multiple-periods-again"),
]


@pytest.fixture(params=NAMES, ids=lambda x: x[0])
def sanitized(request):
    yield request.param[0], request.param[1]


def test_sanitize_name(sanitized):
    name, result = sanitized
    assert sanitize_name(name) == result


class TestLocators:
    def test_types(self):
        assert "browser" in TYPES
        assert "image" in TYPES

    def test_from_dict(self):
        data = {
            "type": "browser",
            "strategy": "class",
            "value": "btn-primary",
            "source": "https://robotsparebinindustries.com/",
        }

        locator = Locator.from_dict(data)
        assert isinstance(locator, BrowserDOM)
        assert locator.strategy == "class"
        assert locator.value == "btn-primary"
        assert locator.source == "https://robotsparebinindustries.com/"

    def test_from_dict_extras(self):
        data = {
            "type": "browser",
            "strategy": "class",
            "value": "btn-primary",
            "source": "https://robotsparebinindustries.com/",
            "notvalid": "somevalue",
        }

        locator = Locator.from_dict(data)
        assert isinstance(locator, BrowserDOM)

    def test_from_dict_optional(self):
        data = {
            "type": "browser",
            "strategy": "class",
            "value": "btn-primary",
        }

        locator = Locator.from_dict(data)
        assert isinstance(locator, BrowserDOM)
        assert locator.strategy == "class"
        assert locator.value == "btn-primary"
        assert locator.source == None

    def test_from_dict_required(self):
        data = {
            "type": "browser",
            "strategy": "class",
        }

        with pytest.raises(ValueError):
            Locator.from_dict(data)

    def test_from_dict_no_type(self):
        data = {
            "strategy": "class",
            "value": "btn-primary",
        }

        with pytest.raises(ValueError):
            Locator.from_dict(data)

    def test_from_dict_image_template(self):
        data = {
            "type": "image",
            "path": "images/TestTemplate.png",
            "source": "images/TestSource.png",
        }
        locator = Locator.from_dict(data)
        assert isinstance(locator, ImageTemplate)
        assert locator.path == "images/TestTemplate.png"
        assert locator.source == "images/TestSource.png"


class TestDatabase:
    @pytest.fixture
    def legacy_database(self):
        database = LocatorsDatabase(to_stream(LEGACY))
        database.load()
        return database

    @pytest.fixture
    def current_database(self):
        database = LocatorsDatabase(to_stream(CURRENT))
        database.load()
        return database

    def test_load_legacy(self):
        database = LocatorsDatabase(to_stream(LEGACY))
        database.load()

        assert database.error is None
        assert len(database.locators) == 3

    def test_load_legacy_empty(self):
        database = LocatorsDatabase(to_stream({}))
        database.load()

        assert database.error is None
        assert len(database.locators) == 0

    def test_legacy_missing_name(self):
        content = copy.deepcopy(LEGACY)
        del content[1]["name"]

        database = LocatorsDatabase(to_stream(content))
        database.load()

        assert database.error is None
        assert len(database.locators) == 2

    def test_load_malformed(self):
        stream = io.StringIO("not-a-json{]}\\''")

        database = LocatorsDatabase(stream)
        database.load()

        assert database.error is not None
        assert len(database.error) == 2
        assert len(database.locators) == 0

    def test_load_missing(self):
        database = LocatorsDatabase("not/a/valid/path")
        database.load()

        assert database.error is None
        assert len(database.locators) == 0

    def test_reset_error(self):
        database = LocatorsDatabase()

        database.path = io.StringIO("some-error")
        database.load()

        assert database.error is not None
        assert len(database.locators) == 0

        database.path = to_stream(CURRENT)
        database.load()

        assert database.error is None
        assert len(database.locators) == 3

    def test_load_invalid(self):
        database = LocatorsDatabase(to_stream(ERRORS))
        database.load()

        assert database.error is None
        assert len(database.locators) == 1
        assert len(database._invalid) == 2
