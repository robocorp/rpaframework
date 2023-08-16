"""Base utilities for COM applications like Word, Excel, Outlook."""

import atexit
import logging
import platform
import struct
from contextlib import contextmanager

if platform.system() == "Windows":
    import win32api
    import win32com.client
    from pywintypes import com_error as COMError
else:
    logging.getLogger(__name__).warning(
        "Any `RPA.*.Application` library works only on Windows platform"
    )
    COMError = Exception


def _to_unsigned(val):
    return struct.unpack("L", struct.pack("l", val))[0]


@contextmanager
def catch_com_error():
    """Try to convert COM errors to human-readable format."""
    try:
        yield
    except COMError as err:  # pylint: disable=no-member
        if err.excepinfo:
            try:
                msg = win32api.FormatMessage(_to_unsigned(err.excepinfo[5]))
            except Exception:  # pylint: disable=broad-except
                msg = err.excepinfo[2]
        else:
            try:
                msg = win32api.FormatMessage(_to_unsigned(err.hresult))
            except Exception:  # pylint: disable=broad-except
                msg = err.strerror
        raise RuntimeError(msg) from err


class BaseApplication:
    """Base library `Application` class for managing COM apps."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    APP_DISPATCH = None  # this has to be defined in every inheriting class

    def __init__(self, autoexit: bool = True):
        self.logger = logging.getLogger(__name__)
        self.app = None

        if platform.system() != "Windows":
            self.logger.warning(
                "This Application library requires Windows dependencies to work."
            )
        if autoexit:
            atexit.register(self.quit_application)

    def open_application(
        self, visible: bool = False, display_alerts: bool = False
    ) -> None:
        """Open the application.

        :param visible: Show the window on opening. (`False` by default)
        :param display_alerts: Display alert popups. (`False` by default)
        """
        with catch_com_error():
            self.app = win32com.client.gencache.EnsureDispatch(self.APP_DISPATCH)
            self.logger.debug("Opened application: %s", self.app)

            if hasattr(self.app, "Visible"):
                state = "visible" if visible else "invisible"
                self.logger.debug("Making the application %s.", state)
                self.app.Visible = visible

            # Show for e.g. a file overwrite warning or not.
            if hasattr(self.app, "DisplayAlerts"):
                state = "Displaying" is display_alerts else "Hiding"
                self.logger.debug("%s the application alerts.", state)
                self.app.DisplayAlerts = display_alerts

    def close_document(self, save_changes: bool = False) -> None:
        """Close the active document and app (if open).

        :param save_changes: Enable to save changes on quit. (defaults to `False`)
        """
        if not self.app:  # no app open at all
            return

        if hasattr(self.app, "ActiveDocument"):
            state = "saving" if save_changes else "not saving"
            self.logger.debug("Closing the opened document and %s changes.", state)
            with catch_com_error():
                self.app.ActiveDocument.Close(save_changes)

    def quit_application(self, save_changes: bool = False) -> None:
        """Quit the application.

        :param save_changes: Enable to save changes on quit. (defaults to False)
        """
        if not self.app:
            return

        self.close_document(save_changes)
        with catch_com_error():
            self.app.Quit()
        self.app = None
