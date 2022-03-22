import contextlib
import functools
from typing import Optional

from RPA.core.windows.helpers import IS_WINDOWS

if IS_WINDOWS:
    import uiautomation as auto
    from comtypes import COMError  # noqa


class ElementNotFound(ValueError):
    """No matching elements were found."""


class WindowControlError(ValueError):
    """Matching window was not found"""


class WindowsContext:
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

    def _window_or_none(
        self, window: "WindowsElement"  # noqa: F821
    ) -> Optional["WindowsElement"]:  # noqa: F821
        if window and window.item:
            try:
                window.item.BoundingRectangle
            except COMError:  # pylint: disable=broad-except
                # Failure to get the bounding rectangle proves that the window doesn't
                #  exist anymore.
                return None

            return window

        return None

    @property
    def anchor(self) -> Optional["WindowsElement"]:  # noqa: F821
        return self._window_or_none(self.ctx.anchor_element)

    @property
    def window(self) -> Optional["WindowsElement"]:  # noqa: F821
        return self._window_or_none(self.ctx.window_element)

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
        timeout: Optional[float] = kwargs.pop("timeout", None)
        with self.set_timeout(timeout):
            # Do not send on purpose the `timeout` back to the original decorated
            #  function. (as the temporary timeout setting is currently active)
            return func(self, *args, **kwargs)

    return wrapper
