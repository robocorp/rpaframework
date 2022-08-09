try:
    import RPA.recognition as _unused

    del _unused
    HAS_RECOGNITION = True
except ImportError:
    HAS_RECOGNITION = False

from typing import Optional


class ElementNotFound(ValueError):
    """No matching elements were found."""


class MultipleElementsFound(ValueError):
    """Multiple matching elements were found, but only one was expected."""


class TimeoutException(ValueError):
    """Timeout reached while waiting for condition."""


class LibraryContext:
    """Shared context for all keyword libraries."""

    def __init__(self, ctx):
        self.ctx = ctx

    @property
    def logger(self):
        return self.ctx.logger

    @property
    def buffer(self):
        return self.ctx.buffer

    @property
    def locators_path(self) -> Optional[str]:
        return self.ctx.locators_path
