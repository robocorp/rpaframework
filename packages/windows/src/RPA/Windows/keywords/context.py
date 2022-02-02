import os

class ControlNotFound(ValueError):
    """No matching controls were found."""


class ElementNotFound(ValueError):
    """No matching elements were found."""


class MultipleControlsFound(ValueError):
    """Multiple matching controls were found, but only one was expected."""


class TimeoutException(ValueError):
    """Timeout reached while waiting for condition."""


class WindowControlError(ValueError):
    """Matching window was not found"""


class ActionNotPossible(ValueError):
    """Action is not possible for the given Control"""


class LibraryContext:
    """Shared context for all keyword libraries."""

    def __init__(self, ctx, locator_db_path: str = None):
        self.ctx = ctx
        self._locators_db_path = os.path.abspath(locator_db_path) if locator_db_path else None

    @property
    def logger(self):
        return self.ctx.logger

    @property
    def window(self):
        return self.ctx.window
