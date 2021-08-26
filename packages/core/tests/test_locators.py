import copy
import io
import json
import os
import tempfile
import pytest
from contextlib import contextmanager
from pathlib import Path

from RPA.core.locators import (
    TYPES,
    LocatorsDatabase,
    Locator,
    PointLocator,
    OffsetLocator,
    RegionLocator,
    SizeLocator,
    BrowserLocator,
    ImageLocator,
    Coordinates,
    Offset,
    BrowserDOM,
    ImageTemplate,
    sanitize_name,
    literal,
)


def to_stream(data):
    return io.StringIO(json.dumps(data))


@contextmanager
def temp_cwd():
    cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            yield tmp
    finally:
        os.chdir(cwd)


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
    "RobotSpareBin.Logo": {
        "type": "image",
        "path": "relative/locator/path.png",
        "source": "/absolute/locator/path.png",
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


class TestLiteral:
    def test_parse_image(self):
        locator = literal.parse("image:path/to/file.png")
        assert isinstance(locator, ImageLocator)
        assert locator.path == "path/to/file.png"
        assert locator.confidence == None

    def test_parse_image_args(self):
        locator = literal.parse("image:path/to/file.png,80.0")
        assert isinstance(locator, ImageLocator)
        assert locator.path == "path/to/file.png"
        assert locator.confidence == 80.0

    def test_parse_point(self):
        locator = literal.parse("point:100,200")
        assert isinstance(locator, PointLocator)
        assert locator.x == 100
        assert locator.y == 200

    def test_parse_coordinates(self):
        # Kept for backwards compatibility
        locator = literal.parse("coordinates:100,200")
        assert isinstance(locator, PointLocator)
        assert locator.x == 100
        assert locator.y == 200

    def test_parse_offset(self):
        locator = literal.parse("offset:100,200")
        assert isinstance(locator, OffsetLocator)
        assert locator.x == 100
        assert locator.y == 200

    def test_parse_size(self):
        locator = literal.parse("region:50,75,100,200")
        assert isinstance(locator, RegionLocator)
        assert locator.left == 50
        assert locator.top == 75
        assert locator.right == 100
        assert locator.bottom == 200

    def test_parse_size(self):
        locator = literal.parse("size:100,200")
        assert isinstance(locator, SizeLocator)
        assert locator.width == 100
        assert locator.height == 200


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
        assert isinstance(locator, BrowserLocator)
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
        assert isinstance(locator, BrowserLocator)

    def test_from_dict_optional(self):
        data = {
            "type": "browser",
            "strategy": "class",
            "value": "btn-primary",
        }

        locator = Locator.from_dict(data)
        assert isinstance(locator, BrowserLocator)
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
        assert isinstance(locator, ImageLocator)
        assert locator.path == "images/TestTemplate.png"
        assert locator.source == "images/TestSource.png"
        assert locator.confidence == None

    def test_from_dict_image_template_optional(self):
        data = {
            "type": "image",
            "path": "images/TestTemplate.png",
            "source": "images/TestSource.png",
            "confidence": 90.0,
        }
        locator = Locator.from_dict(data)
        assert isinstance(locator, ImageLocator)
        assert locator.path == "images/TestTemplate.png"
        assert locator.source == "images/TestSource.png"
        assert locator.confidence == 90.0

    def test_image_to_dict(self):
        locator = ImageLocator("doesntmatter")
        data = locator.to_dict()
        assert data["path"] == "doesntmatter"
        assert data["type"] == "image"

    def test_coordinates_to_dict(self):
        locator = Coordinates(1, 2)
        data = locator.to_dict()
        assert data["x"] == 1
        assert data["y"] == 2
        assert data["type"] == "point"

    def test_point_to_dict(self):
        locator = PointLocator(1, 2)
        data = locator.to_dict()
        assert data["x"] == 1
        assert data["y"] == 2
        assert data["type"] == "point"

    def test_string_conversion(self):
        locator = PointLocator(1, 2)
        assert str(locator) == "point:1,2"

        locator = ImageLocator("path/to/something.png")
        assert str(locator) == "image:path/to/something.png"

        locator = BrowserLocator(strategy="class", value="btn-primary")
        assert str(locator) == "browser:class,btn-primary"


class TestDatabase:
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
        assert len(database.locators) == 4

    def test_load_invalid(self):
        database = LocatorsDatabase(to_stream(ERRORS))
        database.load()

        assert database.error is None
        assert len(database.locators) == 1
        assert len(database._invalid) == 2

    def test_resolve_paths(self):
        database = LocatorsDatabase(to_stream(CURRENT))
        database.load()

        database.path = "/example/root/path/locators.json"

        locator = database.resolve("RobotSpareBin.Logo")
        assert isinstance(locator, ImageLocator)
        assert Path(locator.path) == Path(
            "/example/root/path/relative/locator/path.png"
        )
        assert Path(locator.source) == Path("/absolute/locator/path.png")

    def test_migrate_screenshot(self):
        content = copy.deepcopy(CURRENT)
        content["RobotSpareBin.Username"]["screenshot"] = "not-exist.png"
        content["RobotSpareBin.Password"]["screenshot"] = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAA"
            "AACklEQVR42mMAAQAABQABoIJXOQAAAABJRU5ErkJggg=="
        )

        with temp_cwd() as cwd:
            images = Path(cwd) / ".images"
            screenshot_username = images / "robotsparebin-username-screenshot.png"
            screenshot_password = images / "robotsparebin-password-screenshot.png"

            database = LocatorsDatabase(to_stream(content))
            database.load()

            assert database.error is None
            assert len(database.locators) == 4

            assert images.is_dir()
            assert not (screenshot_username).is_file()
            assert (screenshot_password).is_file()

            username = database.locators["RobotSpareBin.Username"]
            assert username.screenshot == "not-exist.png"

            password = database.locators["RobotSpareBin.Password"]
            assert password.screenshot == str(screenshot_password.relative_to(cwd))

    def test_load_by_name(self):
        with temp_cwd() as cwd:
            path = Path(cwd) / "locators.json"
            with open(path, "w") as fd:
                fd.write(json.dumps(CURRENT))

            locator = LocatorsDatabase.load_by_name("RobotSpareBin.Password")
            assert isinstance(locator, BrowserLocator)
            assert locator.strategy == "id"
            assert locator.value == "password"

    def test_load_by_name_invalid_path(self):
        with pytest.raises(ValueError):
            LocatorsDatabase.load_by_name("RobotSpareBin.Password", "no-exist.json")

    def test_load_by_name_invalid_name(self):
        with temp_cwd() as cwd:
            path = Path(cwd) / "locators.json"
            with open(path, "w") as fd:
                fd.write(json.dumps(CURRENT))

            with pytest.raises(ValueError):
                LocatorsDatabase.load_by_name("RobotSpareBin.Paswerd")

    def test_save(self):
        stream = to_stream(CURRENT)
        database = LocatorsDatabase(stream)
        database.load()

        stream.truncate(0)
        stream.seek(0)
        database.locators["RobotSpareBin.Password"].value = "paswerd"
        database.save()

        data = stream.getvalue()
        content = json.loads(data)
        assert content["RobotSpareBin.Password"]["value"] == "paswerd"
