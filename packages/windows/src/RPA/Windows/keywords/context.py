from typing import Optional

from RPA.Windows.utils import window_or_none


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

    def __init__(self, ctx):
        self.ctx = ctx

    @property
    def logger(self):
        return self.ctx.logger

    @property
    def anchor(self) -> Optional["WindowsElement"]:  # noqa: F821
        return window_or_none(self.ctx.anchor_element)

    @property
    def window(self) -> Optional["WindowsElement"]:  # noqa: F821
        return window_or_none(self.ctx.window)
