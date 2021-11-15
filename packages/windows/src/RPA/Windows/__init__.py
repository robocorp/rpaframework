import logging
import platform
import warnings

# pylint: disable=wrong-import-position
from robotlibcore import DynamicCore


from RPA.Windows.keywords import (
    ControlKeywords,
    LocatorKeywords,
    RecorderKeywords,
    WindowKeywords,
)


class Windows(DynamicCore):
    """The `Windows` can be used for Windows desktop automation.

    This library is at this moment in "BETA" stage as an alternative
    library for `RPA.Desktop.Windows`. Main difference being that this
    library is using `uiautomation`_ dependency instead of `pywinauto`.

    .. _uiautomation: https://github.com/yinkaisheng/Python-UIAutomation-for-Windows

    About terminology

    The most used term in uiautomation package is "Control" which means different
    objects of the application like Window, Button or ListItem.

    How to inspect

    xxxxxx

    Examples

    xxxxxx

    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self, timeout: float = None, simulate_move: bool = False):
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout or 0.5
        self.simulate_move = simulate_move
        self.window = None

        # Register keyword libraries to LibCore
        libraries = [
            # ControlKeywords(self),
            LocatorKeywords(self),
            RecorderKeywords(self),
            WindowKeywords(self),
        ]
        super().__init__(libraries)
