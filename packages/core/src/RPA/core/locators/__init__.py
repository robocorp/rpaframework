# flake8: noqa
from dataclasses import fields
from .containers import TYPES, Locator, BrowserDOM, ImageTemplate, Coordinates, Offset
from .database import LocatorsDatabase


def parse_locator(locator: str) -> Locator:
    """Construct locator from string format, e.g. 'coordinates:120,340'."""
    if isinstance(locator, Locator):
        return locator

    try:
        name, _, value = str(locator).partition(":")
        name = name.strip().lower()
    except ValueError as err:
        raise ValueError(f"Invalid locator format: {locator}") from err

    # Assume alias if only name given
    if not value:
        name, value = "alias", name

    if name == "alias":
        return LocatorsDatabase.load_by_name(value)
    else:
        klass = TYPES.get(name)
        if not klass:
            raise ValueError(f"Unknown locator type: {name}")

        args = value.split(",")
        args = [field.type(value) for field, value in zip(fields(klass), args)]

        return klass(*args)
