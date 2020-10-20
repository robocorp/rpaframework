import base64
import io
import json
import logging
import os
import random
import string
from contextlib import contextmanager
from pathlib import Path
from RPA.core.locators import Locator, BrowserDOM


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

        if name not in database.locators:
            raise ValueError(f"No locator with name: {name}")

        return database.locators[name]

    @property
    def default_path(self):
        """Return default path for locators database file."""
        dirname = os.getenv("ROBOT_ROOT", "")
        filename = "locators.json"
        return os.path.join(dirname, filename)

    @property
    def error(self):
        return self._error

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
                locators, invalid = self._migrate_data(data)
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

        for name, fields in data.items():
            try:
                locators[name] = Locator.from_dict(fields)
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.warning('Failed to parse locator "%s": %s', name, exc)
                invalid[name] = fields

        return locators, invalid

    def _migrate_data(self, data):
        """Attempt to load database in legacy format."""
        data = {fields["name"]: fields for fields in data if "name" in fields}

        locators, invalid = self._load(data)

        for locator in locators.values():
            self._convert_screenshot(locator)

        self.save()
        self.logger.warning("Migrated locators database from legacy format")

        return locators, invalid

    def _convert_screenshot(self, locator):
        """Migrate base64 screenshot to file."""
        if not isinstance(locator, BrowserDOM):
            return

        if not locator.screenshot:
            return

        content = base64.b64decode(locator.screenshot)

        images = Path(self.path).parent / ".images"
        os.makedirs(images, exist_ok=True)

        # Brute-force unique name
        path = None
        while True:
            name = "".join(random.choice(string.hexdigits) for _ in range(8))
            path = (images / name).with_suffix(".png")
            if not path.exists():
                break

        with open(path, "wb") as fd:
            fd.write(content)

        locator.screenshot = path
