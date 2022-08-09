import logging
from typing import Optional

from .helpers import IS_WINDOWS
from .inspect import ElementInspector
from .locators import Locator, LocatorMethods
from .window import WindowMethods
from ..vendor.robotlibcore import DynamicCore


if IS_WINDOWS:
    import uiautomation as auto
    from .inspect import RecordElement  # library exposure


class WindowsElementsMixin:
    """Windows elements mixin compatible with inspector and windows packages."""

    def __init__(self, locators_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.global_timeout: float = float(
            auto.uiautomation.TIME_OUT_SECOND if IS_WINDOWS else 10
        )
        self.window_element: Optional[Locator] = None
        self.anchor_element: Optional[Locator] = None

        # Register all "keyword" methods into this "library" class.
        libraries = self._get_libraries(locators_path)
        super().__init__(libraries)

    def _get_libraries(self, locators_path: Optional[str]):
        return [
            LocatorMethods(self, locators_path=locators_path),
            WindowMethods(self),
        ]


class WindowsElements(WindowsElementsMixin, DynamicCore):
    """Windows elements library compatible with inspector and windows packages."""
