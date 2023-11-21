import logging
from typing import Optional

from ..vendor.robotlibcore import DynamicCore
from .action import ActionMethods
from .elements import ElementMethods
from .helpers import IS_WINDOWS
from .locators import Locator, LocatorMethods
from .window import WindowMethods

if IS_WINDOWS:
    import uiautomation as auto


class WindowsElementsMixin:
    """Windows elements mixin compatible with inspector and windows packages."""

    def __init__(self, locators_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.list_processes = True
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
            ActionMethods(self),
            ElementMethods(self),
            LocatorMethods(self, locators_path=locators_path),
            WindowMethods(self),
        ]


class WindowsElements(WindowsElementsMixin, DynamicCore):
    """Windows elements library compatible with the inspector and windows packages."""
