"""Base utilities for COM applications like Word, Excel, Outlook."""

import atexit
import gc
import logging
import platform
import struct
from contextlib import contextmanager
from pathlib import Path

if platform.system() == "Windows":
    import win32api
    import win32com.client
    from pywintypes import com_error as COMError  # pylint: disable=no-name-in-module
    from win32com.client import constants  # pylint: disable=unused-import
else:
    logging.getLogger(__name__).warning(
        "Any `RPA.*.Application` library works only on Windows platform!"
    )
    # As these are imported anyway from here and should be defined on non-Windows OSes.
    COMError = Exception
    constants = None


def rgb_to_excel_color(red, green, blue):
    return red + (green * 256) + (blue * 256**2)


def _to_unsigned(val):
    return struct.unpack("L", struct.pack("l", val))[0]


def to_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def to_str_path(path: str) -> str:
    return str(to_path(path))


# TODO(cmin764; 16 Aug 2023): Create a `handles_com_error` decorator if we get a little
#  too repetitive with context managers guarding. (to decorate the keywords)
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


class MetaApplication(type):
    """Metaclass enhancing every final class inheriting from a base using this."""

    def __new__(cls, *args, **kwargs) -> type:
        final_class = super().__new__(cls, *args, **kwargs)
        bases = final_class.__mro__[1:]
        if len(bases) < 2:  # not enhancing bases
            return final_class

        super_class = bases[0]
        final_class.__doc__ = (final_class.__doc__ or "") + (super_class.__doc__ or "")
        if final_class.APP_DISPATCH is None:
            raise ValueError(
                "An `APP_DISPATCH` has to be defined in this"
                f" {final_class.__name__!r} class"
            )
        return final_class


class BaseApplication(metaclass=MetaApplication):
    # Base library `Application` class for managing COM apps.
    # The docstring below is automatically appended at the end of every inheritor.
    """
    **Caveats**

    This library works on a Windows operating system with UI enabled only, and you must
    ensure that you open the app first with ``Open Application`` before running any
    other relevant keyword which requires to operate on an open app. The application is
    automatically closed at the end of the task execution, so this can be changed by
    importing the library with the `autoexit=${False}` setting.

    .. code-block:: robotframework

        *** Settings ***
        Library     RPA.Excel|Outlook|Word.Application    autoexit=${False}

    If you're running the Process by Control Room through a custom self-hosted Worker
    service, then please make sure that you enable an RDP session by ticking "Use
    Desktop Connection" under the Step configuration.

    If you still encounter issues with opening a document, please ensure that file can
    be opened first manually and dismiss any alert potentially blocking the process.

    Check the documentation below for more info:

    - https://robocorp.com/docs/control-room/unattended/worker-setups/windows-desktop
    - https://robocorp.com/docs/faq/windows-server-2016
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    APP_DISPATCH = None  # this has to be defined in every inheriting class

    def __init__(self, autoexit: bool = True):
        """Initialize the library instance by wrapping the COM Windows app.

        :param autoexit: Automatically close the app when the process finishes.
        """
        self.logger = logging.getLogger(__name__)
        self._app_name = self.APP_DISPATCH.split(".")[0]
        self._app = None

        if platform.system() != "Windows":
            self.logger.warning(
                "This %s application library requires Windows dependencies to work.",
                self._app_name,
            )
        if autoexit:
            atexit.register(self.quit_application)

    @property
    def app(self):
        if self._app is None:
            raise ValueError(f"{self._app_name} application is not open")

        return self._app

    def open_application(
        self, visible: bool = False, display_alerts: bool = False
    ) -> None:
        """Open the application.

        :param visible: Show the window on opening. (`False` by default)
        :param display_alerts: Display alert popups. (`False` by default)
        """
        with catch_com_error():
            self._app = win32com.client.gencache.EnsureDispatch(self.APP_DISPATCH)
            self.logger.debug("Opened application: %s", self.app)

            if hasattr(self.app, "Visible"):
                state = "visible" if visible else "invisible"
                self.logger.debug("Making the application %s.", state)
                self.app.Visible = visible
            elif visible:
                self.logger.warning("Visibility cannot be controlled on this app.")

            # Show for e.g. a file overwrite warning or not.
            if hasattr(self.app, "DisplayAlerts"):
                state = "Displaying" if display_alerts else "Hiding"
                self.logger.debug("%s the application alerts.", state)
                self.app.DisplayAlerts = display_alerts
            elif display_alerts:
                self.logger.warning(
                    "Alerts displaying cannot be controlled on this app."
                )

    @property
    def _active_document(self):
        # Retrieves the currently active document. (raises if there's none active)
        with catch_com_error():
            return getattr(self.app, "ActiveDocument", None)

    def _deactivate_document(self):
        # Cleans-up a just closed previously active document.
        pass

    def close_document(self, save_changes: bool = False) -> None:
        """Close the active document and app (if open).

        :param save_changes: Enable changes saving on quit. (`False` by default)
        """
        if not self._app:  # no app open at all
            return

        try:
            with catch_com_error():
                if self._active_document:
                    state = "saving" if save_changes else "not saving"
                    self.logger.debug(
                        "Closing the open document and %s changes.", state
                    )
                    self._active_document.Close(save_changes)
                    self._deactivate_document()
        except RuntimeError as exc:
            if "no document is open" in str(exc):
                self.logger.warning(
                    "Failed attempt on closing a document when there's none open!"
                )
            else:
                raise

    def quit_application(self, save_changes: bool = False) -> None:
        """Quit the application.

        :param save_changes: Enable to save changes on quit. (`False` by default)
        """
        if not self._app:
            return

        self.close_document(save_changes)
        with catch_com_error():
            gc.collect()
            self.app.Quit()
        self._app = None
        gc.collect()

    def set_object_property(self, object_instance, property_name: str, value: str):
        """Set the property of any object.

        This is a utility keyword for Robot Framework syntax to set object
        property values.

        .. code-block:: robotframework

            ${new_value}=    Replace String    ${value}    10.132.    5511.11.
            Set Object Property    ${result}    Value    ${new_value}

        :param object_instance: object instance to set the property
        :param property_name: property name to set
        :param value: value to set
        """
        if hasattr(object_instance, property_name):
            setattr(object_instance, property_name, value)
        else:
            raise AttributeError(
                f"Object {type(object_instance)} does not "
                f"have property '{property_name}'"
            )
