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

if platform.system() == "Windows":
    # Configure comtypes to not generate DLL bindings into
    # current environment, instead keeping them in memory.
    # Slower, but prevents dirtying environments.
    import comtypes.client

    comtypes.client.gen_dir = None

    # Ignore pywinauto warning about threading mode,
    # which comtypes initializes to STA instead of MTA on import.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        import uiautomation as auto
        from uiautomation.uiautomation import Control


class Windows(DynamicCore):
    """The `Windows` can be used for Windows desktop automation.

    This library is at this moment in "BETA" stage as an alternative
    library for `RPA.Desktop.Windows`. Main difference being that this
    library is using `uiautomation` dependency instead of `pywinauto`.
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
            ControlKeywords(self),
            LocatorKeywords(self),
            RecorderKeywords(self),
            WindowKeywords(self),
        ]
        super().__init__(libraries)
