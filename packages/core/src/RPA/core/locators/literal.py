from typing import Optional, Union

from RPA.core.locators import LocatorsDatabase, Locator, TYPES


LocatorType = Union[str, Locator]


def _unquote(text):
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    return text


def parse(locator: LocatorType, path: Optional[str] = None) -> Locator:
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
        return LocatorsDatabase.load_by_name(_unquote(value), path)
    else:
        klass = TYPES.get(typename)
        if not klass:
            raise ValueError(f"Unknown locator type: {typename}")

        args = [_unquote(arg) for arg in value.split(",")]
        return klass(*args)
