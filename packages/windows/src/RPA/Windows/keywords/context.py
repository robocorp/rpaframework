# pylint: disable=unused-import
from RPA.core.windows.context import (  # noqa: F401
    ElementNotFound,
    WindowControlError,
    WindowsContext as LibraryContext,
    with_timeout,
)


class ActionNotPossible(ValueError):
    """Action is not possible for the given Control."""


# Not yet used exceptions:


class ControlNotFound(ValueError):
    """No matching controls were found."""


class MultipleControlsFound(ValueError):
    """Multiple matching controls were found, but only one was expected."""


class TimeoutException(ValueError):
    """Timeout reached while waiting for condition."""
