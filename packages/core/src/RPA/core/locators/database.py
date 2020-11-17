import base64
import io
import json
import logging
import os
import re
from contextlib import contextmanager
from pathlib import Path
from RPA.core.locators import Locator, BrowserDOM, ImageTemplate


@contextmanager
def open_stream(obj, *args, **kwargs):
    """Wrapper for built-in open(), which allows using
    existing IO streams.
    """
    try:
        is_open = False
        if not isinstance(obj, io.IOBase):
            obj = open(obj, *args, **kwargs)
            is_open = True

        yield obj
    finally:
        if is_open:
            obj.close()


def sanitize_name(name):
    """Sanitize locator name for use in filenames.
    Sanitized name should be unique in database.

    Examples:
        Google.Logo -> google-logo
        Cool Stuff -> cool-stuff
        What?? -> what
    """
    # Convert everything to lowercase
    name = str(name).lower()
    # Replace period delimiters with single space
    name = re.sub(r"\.+", " ", name)
    # Strip non-word characters
    name = re.sub(r"[^\w\s]", "", name)
    # Strip leading/trailing whitespace
    name = name.strip()
    # Convert whitespace runs to single dash
    name = re.sub(r"\s+", "-", name)

    return name


class ValidationError(ValueError):
    """Validation error from malformed database or locator entry."""


class LocatorsDatabase:
    """Container for storing locator information,
    and serializing/deserializing database file.
    """

    def __init__(self, path=None):
        self.logger = logging.getLogger(__name__)
        self.path = path or self.default_path
        self.locators = {}
        self._error = None
        self._invalid = {}

    @classmethod
    def load_by_name(cls, name, path=None) -> Locator:
        """Load locator entry from database with given name."""
        database = cls(path)
        database.load()

        if database.error:
            error_msg, error_args = database.error
            raise ValueError(error_msg % error_args)

        return database.resolve(name)

    @property
    def default_path(self):
        """Return default path for locators database file."""
        dirname = os.getenv("ROBOT_ROOT", "")
        filename = "locators.json"
        return os.path.join(dirname, filename)

    @property
    def parent(self):
        """Return parent directory for database."""
        return (
            Path(self.path).parent
            if not isinstance(self.path, io.IOBase)
            else Path(".")
        )

    @property
    def error(self):
        return self._error

    def resolve(self, name):
        """Fetch locator form database, and fix relative paths."""
        if name not in self.locators:
            raise ValueError(f"No locator with name: {name}")

        locator = self.locators[name]

        def to_absolute(field_name):
            value = getattr(locator, field_name)
            if value is not None and not Path(value).is_absolute():
                setattr(locator, field_name, str(Path(self.parent) / value))

        if isinstance(locator, BrowserDOM):
            to_absolute("screenshot")
        elif isinstance(locator, ImageTemplate):
            to_absolute("path")
            to_absolute("source")

        return locator

    def set_error(self, msg, *args):
        """Log an error message. Ensures the same message
        is not repeated multiple times.
        """
        message = (msg, args)
        if message != self._error:
            self.logger.error(msg, *args)
            self._error = message

    def reset_error(self):
        """Clear error state."""
        self._error = None

    def load(self):
        """Deserialize database from file."""
        try:
            with open_stream(self.path, "r") as fd:
                data = json.load(fd)

            if isinstance(data, list):
                locators, invalid = self._load_legacy(data)
            else:
                locators, invalid = self._load(data)

            self.locators = locators
            self._invalid = invalid
            self.reset_error()
        except FileNotFoundError:
            self.locators = {}
            self._invalid = {}
            self.reset_error()
        except Exception as err:  # pylint: disable=broad-except
            self.locators = {}
            self._invalid = {}
            self.set_error("Could not read database: %s", str(err))

    def save(self):
        """Serialize database into file."""
        data = {}

        for name, locator in self.locators.items():
            data[name] = locator.to_dict()

        for name, fields in self._invalid.items():
            if name not in data:
                data[name] = fields

        with open_stream(self.path, "w") as fd:
            output = json.dumps(data, sort_keys=True, indent=4)
            fd.write(output)

    def _load(self, data):
        """Load database content as Locator objects."""
        locators = {}
        invalid = {}

        sanitized = []
        for name, fields in data.items():
            try:
                sname = sanitize_name(name)
                if sname in sanitized:
                    raise ValueError(f"Duplicate sanitized name: {name} / {sname}")
                sanitized.append(sname)

                locators[name] = Locator.from_dict(fields)
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.warning('Failed to parse locator "%s": %s', name, exc)
                invalid[name] = fields

        return locators, invalid

    def _load_legacy(self, data):
        """Attempt to load database in legacy format."""
        data = {fields["name"]: fields for fields in data if "name" in fields}

        locators, invalid = self._load(data)

        for name, locator in locators.items():
            self._convert_screenshot(name, locator)

        return locators, invalid

    def _convert_screenshot(self, name, locator):
        """Migrate base64 screenshot to file."""
        if not isinstance(locator, BrowserDOM):
            return

        if not locator.screenshot:
            return

        images = self.parent / ".images"
        path = images / "{}-{}.png".format(sanitize_name(name), "screenshot")
        content = base64.b64decode(locator.screenshot)

        os.makedirs(images, exist_ok=True)
        with open(path, "wb") as fd:
            fd.write(content)

        locator.screenshot = path.relative_to(self.parent)
