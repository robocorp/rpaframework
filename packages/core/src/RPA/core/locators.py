import os
import io
import json
import logging
from contextlib import contextmanager


def default_locators_path():
    """Return default path for locators database file"""
    DEFAULT_DATABASE_NAME = "locators.json"
    PROJECT_PATH_ENV = "RLAB_PROJECT_PATH"

    if PROJECT_PATH_ENV in os.environ:
        # locators.json is found at root of project, use environment var
        # if available
        return os.path.join(os.environ[PROJECT_PATH_ENV], DEFAULT_DATABASE_NAME)
    else:
        return DEFAULT_DATABASE_NAME


@contextmanager
def open_stream(obj, *args, **kwargs):
    """Wrapper for built-in open(), which allows using
    existing IO streams.
    """
    try:
        if not isinstance(obj, io.IOBase):
            obj = open(obj, *args, **kwargs)
        yield obj
    finally:
        if isinstance(obj, io.IOBase):
            obj.close()


class ValidationError(ValueError):
    """Validation error from malformed database or locator entry."""


class LocatorsDatabase:
    """Container for storing locator information,
    and serializing/deserializing database file.
    """

    def __init__(self, path=default_locators_path()):
        self.logger = logging.getLogger(__name__)
        self.path = path
        self._locators = []
        self._error = None

    @property
    def locators(self):
        return list(self._locators)

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
            self._validate_all(data)
            self._locators = data
            self.reset_error()
        except FileNotFoundError:
            self._locators = []
            self.reset_error()
        except Exception as err:  # pylint: disable=broad-except
            self._locators = []
            self.set_error("Could not read database: %s", str(err))

    def save(self):
        """Serialize database into file."""
        self._validate_all(self._locators)
        with open_stream(self.path, "w") as fd:
            json.dump(self._locators, fd, indent=4)

    def find_by_id(self, locator_id):
        """Find locator entry by id."""
        locator_id = int(locator_id)
        for locator in self._locators:
            if locator["id"] == locator_id:
                return locator
        return None

    def find_by_name(self, name):
        """Find locator entry by name."""
        name = str(name)
        for locator in self._locators:
            if locator["name"] == name:
                return locator
        return None

    def add(self, locator):
        """Add a new locator entry."""
        self.validate(locator)

        if self._locators:
            locator_id = max(locator["id"] for locator in self._locators) + 1
        else:
            locator_id = 0

        locator["id"] = locator_id
        self._locators.append(locator)
        self.save()

        return locator

    def update(self, locator_id, locator):
        """Update an existing locator entry."""
        self.validate(locator)

        if "id" not in locator or locator["id"] != locator_id:
            raise ValidationError("Locator id does not match content")

        for index, entry in enumerate(self._locators):
            if entry["id"] == locator_id:
                self._locators[index] = locator
                break
        else:
            raise ValidationError(f"Unknown locator ID: {locator_id}")

        self.save()

    def delete(self, locator_id):
        """Delete an existing locator entry."""
        self._locators[:] = [loc for loc in self._locators if loc["id"] != locator_id]
        self.save()

    def validate(self, locator):
        """Validate given locator."""
        if "id" in locator and not isinstance(locator["id"], int):
            raise ValidationError("Missing or invalid locator id")
        if "name" not in locator:
            raise ValidationError("Missing locator name field")
        if "type" not in locator:
            raise ValidationError("Missing locator type field")
        if "value" not in locator:
            raise ValidationError("Missing locator value field")

    def _validate_all(self, locators):
        """Validate all given locators."""
        ids, names = set(), set()
        for locator in locators:
            self.validate(locator)
            locator_id = locator["id"]
            name = locator["name"]

            if locator_id in ids:
                raise ValidationError(f"Duplicate locator id: {locator_id}")
            if name in names:
                raise ValidationError(f"Duplicate locator name: {name}")

            ids.add(locator_id)
            names.add(name)
