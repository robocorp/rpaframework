import contextlib
import functools
from typing import Optional

from RPA.Windows.utils import IS_WINDOWS
from .locators import WindowsElement

if IS_WINDOWS:
    from comtypes import COMError  # noqa
    import uiautomation as auto
else:
    COMError = Exception


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
    def current_timeout(self) -> float:
        # This value can change based on `auto.SetGlobalSearchTimeout(...)` calls.
        return auto.uiautomation.TIME_OUT_SECOND

    def _window_or_none(self, window) -> Optional[WindowsElement]:
        if window and window.item:
            if hasattr(window.item, "Exists"):
                return (
                    window
                    if window.item.Exists(maxSearchSeconds=self.current_timeout)
                    else None
                )

            try:
                window.item.BoundingRectangle
            except COMError:  # pylint: disable=broad-except
                return None

            return window

        return None

    @property
    def anchor(self) -> Optional[WindowsElement]:
        return self._window_or_none(self.ctx.anchor_element)

    @property
    def window(self) -> Optional[WindowsElement]:
        return self._window_or_none(self.ctx.window)

    @contextlib.contextmanager
    def set_timeout(self, timeout: Optional[float] = None):
        """Context manager that sets a custom temporary `timeout`."""
        try:
            if timeout is not None:
                auto.SetGlobalSearchTimeout(timeout)
                self.logger.info("Locator timeout set to: %f", self.current_timeout)
            yield
        finally:
            if timeout is not None:
                auto.SetGlobalSearchTimeout(self.ctx.global_timeout)
                self.logger.debug(
                    "Locator timeout set back to global value: %f", self.current_timeout
                )


def with_timeout(func):
    """Applies a temporary `timeout` over the entire decorated context method."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        timeout = kwargs.pop("timeout")
        with self.set_timeout(timeout):
            return func(self, *args, **kwargs)

    return wrapper
