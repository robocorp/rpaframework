import time
from typing import List, Dict

from RPA.Windows.keywords import (
    keyword,
    LibraryContext,
    WindowControlError,
)
from RPA.Windows import utils

if utils.is_windows():
    import uiautomation as auto


class WindowKeywords(LibraryContext):
    """Keywords for handling Window controls"""

    @keyword(tags=["window"])
    def control_window(self, locator: str = None) -> int:
        """Control window defined by the locator string.

        Returns process id of the window.

        :param locator: string locator

        Example:

        .. code-block:: robotframework

            Control Window   Calculator
            Control Window   name:Calculator
            Control Window   subname:Notepad
            Control Window   regex:.*Notepad
            ${pid}=  Control Window   executable:Spotify.exe
        """
        self.ctx.window = self.ctx.get_control(
            locator + " and type:WindowControl", root_control=auto
        )
        if not self.ctx.window.Exists():
            self.ctx.window = self.ctx.get_control(
                locator + " and type:PaneControl", root_control=auto
            )
        if not self.ctx.window.Exists():
            raise WindowControlError(
                "Could not locate window with locator '%s'" % locator
            )
        if hasattr(self.ctx.window, "Restore"):
            self.ctx.window.Restore()
        self.ctx.window.SetFocus()
        self.ctx.window.MoveCursorToMyCenter(simulateMove=self.ctx.simulate_move)
        time.sleep(1.0)
        return self.ctx.window.ProcessId

    @keyword(tags=["window"])
    def minimize_window(self, locator: str = None) -> None:
        """Minimize window defined by the locator string or the
        current active window.

        :param locator: string locator

        Example:

        .. code-block:: robotframework

            Minimize Window   # Current active window
            Minimize Window   executable:Spotify.exe
        """
        if locator:
            self.control_window(locator)
        if not self.ctx.window:
            raise WindowControlError("There is no active window")
        if not hasattr(self.ctx.window, "Minimize"):
            self.logger.warning(
                "Control '%s' does not have attribute Minimize" % self.ctx.window
            )
            return
        self.ctx.window.Minimize()

    @keyword(tags=["window"])
    def maximize_window(self, locator: str = None) -> None:
        """Maximize window defined by the locator string or the
        current active window.

        :param locator: string locator

        Example:

        .. code-block:: robotframework

            Maximize Window   # Current active window
            Maximize Window   executable:Spotify.exe
        """
        if locator:
            self.control_window(locator)
        if not self.ctx.window:
            raise WindowControlError("There is no active window")
        if not hasattr(self.ctx.window, "Maximize"):
            raise WindowControlError("Window does not have attribute Maximize")
        self.ctx.window.Maximize()

    @keyword(tags=["window"])
    def list_windows(self) -> List[Dict]:
        """List all window Controls on the system.

        :return: list of dictionaries containing information
         about Window controls

        Example:

        .. code-block:: robotframework

            ${windows}=  List Windows
            FOR  ${window}  IN  @{windows}
                Log  Window title:${window}[title]
                Log  Window process name:${window}[name]
                Log  Window process id:${window}[pid]
            END
        """
        windows = auto.GetRootControl().GetChildren()
        process_list = utils.get_process_list()
        win_list = []
        for win in windows:
            pid = win.ProcessId
            info = {
                "title": win.Name,
                "pid": win.ProcessId,
                "name": process_list[pid] if pid in process_list.keys() else None,
            }
            win_list.append(info)
        return win_list

    @keyword(tags=["window"])
    def windows_run(self, text: str, wait_time: float = 3.0) -> None:
        """Use Windows run window to launch application.

        :param text: text to enter into run input field
        :param wait_time: sleep time after search has been entered (default 3.0 seconds)

        Example:

        .. code-block:: robotframework

            Windows Run   explorer.exe
        """
        self.ctx.send_keys(None, "{Win}r")
        self.ctx.send_keys(None, text)
        self.ctx.send_keys(None, "{Enter}")
        time.sleep(wait_time)

    @keyword(tags=["window"])
    def windows_search(self, text: str, wait_time: float = 3.0) -> None:
        """Use Windows search window to launch application

        :param text: text to enter into search input field
        :param wait_time: sleep time after search has been entered (default 3.0 seconds)

        Example:

        .. code-block:: robotframework

            Windows Search   Outlook
        """
        self.ctx.send_keys(None, "{Win}s")
        self.ctx.send_keys(None, text)
        self.ctx.send_keys(None, "{Enter}")
        time.sleep(wait_time)

    @keyword(tags=["window"])
    def close_current_window(self) -> bool:
        """Closes current active window or log warning message

        Example:

        .. code-block:: robotframework

            Close Current Window
        """
        # TODO. Fix this keyword
        if not self.ctx.window:
            self.ctx.logger.warning("There is no active window")
            return False
        self.ctx.logger.warning(
            "Closing window process id = %s" % self.ctx.window.ProcessId
        )
        self.ctx.window.SetActive()
        self.ctx.window.SendKeys("{Alt}{F4}")
        return True
