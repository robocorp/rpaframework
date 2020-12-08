from typing import Union
from RPA.core.locators import LocatorsDatabase, Locator, TYPES


def parse(locator: Union[str, Locator]) -> Locator:
    """Parse locator string literal into a ``Locator`` instance.

    For example: "image:path/to/image.png" -> ImageLocator(path="path/to/image-png")
    """
    if isinstance(locator, Locator):
        return locator

    try:
        typename, _, value = str(locator).partition(":")
    except ValueError as err:
        raise ValueError(f"Invalid locator format: {locator}") from err

    if not value:
        typename, value = "alias", typename

    typename = typename.strip().lower()
    if typename == "alias":
        return LocatorsDatabase.load_by_name(value)
    else:
        klass = TYPES.get(typename)
        if not klass:
            raise ValueError(f"Unknown locator type: {typename}")

        args = value.split(",")
        return klass(*args)
