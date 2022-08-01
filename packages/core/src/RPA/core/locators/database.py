import base64
import io
import json
import logging
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union

from RPA.core.locators import BrowserLocator, ImageLocator, Locator


@contextmanager
def open_stream(path_or_stream, *args, encoding="utf-8", **kwargs) -> io.IOBase:
    """Wrapper for built-in open(), which allows using
    existing IO streams.
    """
    if not isinstance(path_or_stream, io.IOBase):
        path_or_stream = open(path_or_stream, *args, encoding=encoding, **kwargs)

    with path_or_stream:  # closes the descriptor even if it errors
        yield path_or_stream


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

    def __init__(self, path: Optional[Union[str, io.IOBase]] = None):
        self.logger = logging.getLogger(__name__)
        self.path = path or self.default_path
        self.locators = {}
        self._error = None
        self._invalid = {}

    @classmethod
    def load_by_name(cls, name, path: Optional[str] = None) -> Locator:
        """Load locator entry from database with given name."""
        database = cls(path)
        database.load()

        if database.error:
            error_msg, error_args = database.error
            raise ValueError(error_msg % error_args)

        return database.resolve(name)

    @property
    def default_path(self) -> str:
        """Return default path for locators database file."""
        dirname = os.getenv("ROBOT_ROOT", "")
        filename = os.getenv("RPA_LOCATORS_DATABASE", "").strip() or "locators.json"
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
            setattr(locator, field_name, self._resolve_path(value))

        if isinstance(locator, BrowserLocator):
            to_absolute("screenshot")
        elif isinstance(locator, ImageLocator):
            to_absolute("path")
            to_absolute("source")

        return locator

    def _resolve_path(self, value):
        if value is not None and not Path(value).is_absolute():
            return str(Path(self.parent) / value)
        return value

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
            json.dump(data, fd, sort_keys=True, indent=4)

    def _load(self, data):
        """Load database content as Locator objects."""
        locators = {}
        invalid = {}

        # Migrate from old list-based file format
        if isinstance(data, list):
            data = {fields["name"]: fields for fields in data if "name" in fields}

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

        # Migrate base64 screenshots to files
        for name, locator in locators.items():
            self._convert_screenshot(name, locator)

        return locators, invalid

    def _convert_screenshot(self, name, locator):
        """Migrate base64 screenshot to file."""
        if not isinstance(locator, BrowserLocator) or not locator.screenshot:
            return

        try:
            path = self._resolve_path(locator.screenshot)
            if Path(path).is_file():
                return
        except Exception:  # pylint: disable=broad-except
            pass

        try:
            content = base64.b64decode(locator.screenshot)
        except Exception:  # pylint: disable=broad-except
            self.logger.info("Invalid screenshot: %s", locator.screenshot)
            return

        images = self.parent / ".images"
        path = images / "{}-{}.png".format(sanitize_name(name), "screenshot")

        os.makedirs(images, exist_ok=True)
        with open(path, "wb") as fd:
            fd.write(content)

        locator.screenshot = str(path.relative_to(self.parent))
