# pylint: disable=missing-class-docstring
import logging
import platform
import pythoncom
import win32com
import time


if platform.system() == "Windows":
    from SapGuiLibrary import SapGuiLibrary
else:

    class SapGuiLibrary:
        """Keywords are only available in Windows."""

        def __init__(self, *args, **kwargs):
            del args, kwargs


class SAP(SapGuiLibrary):
    __doc__ = (
        "This library wraps the upstream "
        "[https://frankvanderkuur.github.io/SapGuiLibrary.html|SapGuiLibrary]."
        "\n\n" + SapGuiLibrary.__doc__
    )

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

        if platform.system() != "Windows":
            self.logger.warning("SAP requires Windows dependencies to work.")

    def connect_to_session(self, explicit_wait: int = 0):
        """Connects to an open session SAP.
        See `Opening a connection / Before running tests` for details about
        requirements before connecting to a session. Optionally `set explicit wait`
        can be used to set the explicit wait time.

        *Examples*:
        | *Keyword*             | *Attributes*          |
        | connect to session    |                       |
        | connect to session    | 3                     |
        | connect to session    | explicit_wait=500ms   |
        """
        lenstr = len("SAPGUI")
        rot = pythoncom.GetRunningObjectTable()
        rotenum = rot.EnumRunning()
        while True:
            monikers = rotenum.Next()
            if not monikers:
                break
            ctx = pythoncom.CreateBindCtx(0)
            name = monikers[0].GetDisplayName(ctx, None)

            if name[-lenstr:] == "SAPGUI":
                obj = rot.GetObject(monikers[0])
                sapgui = win32com.client.Dispatch(
                    obj.QueryInterface(pythoncom.IID_IDispatch)
                )
                self.sapapp = sapgui.GetScriptingEngine
                # Set explicit_wait after connection succeed
                self.set_explicit_wait(explicit_wait)

        if not hasattr(self.sapapp, "OpenConnection"):
            self.take_screenshot()
            message = "Could not connect to Session, is Sap Logon Pad open?"
            raise Warning(message)
        # run explicit wait last
        time.sleep(self.explicit_wait)
