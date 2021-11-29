import os
import signal
import time
from typing import List, Dict, Union

from RPA.Windows.keywords import keyword, LibraryContext, WindowControlError
from RPA.Windows import utils
from .locators import WindowsElement

if utils.is_windows():
    import uiautomation as auto


class WindowKeywords(LibraryContext):
    """Keywords for handling Window controls"""

    @keyword(tags=["window"])
    def control_window(
        self, locator: Union[WindowsElement, str] = None, foreground: bool = True
    ) -> int:
        """Controls the window defined by the locator.

        This means that this window is used as a root element
        for all the following keywords using locators.

        Returns `WindowsElement`.

        :param locator: string locator or Control element
        :param foreground: True to bring window to foreground

        Example:

        .. code-block:: robotframework

            Control Window   Calculator
            Control Window   name:Calculator
            Control Window   subname:Notepad
            Control Window   regex:.*Notepad
            ${handle}=  Control Window   executable:Spotify.exe
        """
        if isinstance(locator, WindowsElement):
            self.ctx.window = locator
        else:
            window_locator = f"{locator}  and type:WindowControl"
            pane_locator = f"{locator}  and type:PaneControl"
            desktop = WindowsElement(auto.GetRootControl(), window_locator)
            self.ctx.window = self.ctx.get_element(window_locator, root_element=desktop)
            if not self.ctx.window.item.Exists():
                desktop = WindowsElement(auto.GetRootControl(), pane_locator)
                self.ctx.window = self.ctx.get_element(
                    pane_locator, root_element=desktop
                )
        if not self.ctx.window.item.Exists():
            raise WindowControlError(
                'Could not locate window with locator "%s"' % locator
            )
        if foreground:
            self.foreground_window()
        return self.ctx.window

    @keyword(tags=["window"])
    def foreground_window(self, locator: Union[WindowsElement, str] = None) -> None:
        """Bring the current active window or the window defined
        by the locator to the foreground.

        :param locator: string locator or Control element
        """
        if locator:
            self.control_window(locator, foreground=True)
            return
        if not self.ctx.window.item:
            raise WindowControlError("There is no active window")
        auto.WaitForExist(self.ctx.window.item, 5)
        if hasattr(self.ctx.window.item, "Restore"):
            self.ctx.window.item.Restore()
        self.ctx.window.item.SetFocus()
        self.ctx.window.item.SetActive()
        self.ctx.window.item.MoveCursorToMyCenter(simulateMove=self.ctx.simulate_move)

    @keyword(tags=["window"])
    def minimize_window(self, locator: Union[WindowsElement, str] = None) -> None:
        """Minimize the current active window or the window defined
        by the locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            Minimize Window   # Current active window
            Minimize Window   executable:Spotify.exe
        """
        if locator:
            self.control_window(locator)
        if not self.ctx.window:
            raise WindowControlError("There is no active window")
        if not hasattr(self.ctx.window.item, "Minimize"):
            self.logger.warning(
                "Control '%s' does not have attribute Minimize" % self.ctx.window
            )
            return
        self.ctx.window.item.Minimize()

    @keyword(tags=["window"])
    def maximize_window(self, locator: Union[WindowsElement, str] = None) -> None:
        """Minimize the current active window or the window defined
        by the locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            Maximize Window   # Current active window
            Maximize Window   executable:Spotify.exe
        """
        if locator:
            self.control_window(locator)
        if not self.ctx.window:
            raise WindowControlError("There is no active window")
        if not hasattr(self.ctx.window.item, "Maximize"):
            raise WindowControlError("Window does not have attribute Maximize")
        self.ctx.window.item.Maximize()

    @keyword(tags=["window"])
    def list_windows(self) -> List[Dict]:
        """List all window element on the system.

        :return: list of dictionaries containing information
         about Window elements

        Example:

        .. code-block:: robotframework

            ${windows}=  List Windows
            FOR  ${window}  IN  @{windows}
                Log  Window title:${window}[title]
                Log  Window process name:${window}[name]
                Log  Window process id:${window}[pid]
                Log  Window process handle:${window}[handle]
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
                "handle": win.NativeWindowHandle,
            }
            win_list.append(info)
        return win_list

    @keyword(tags=["window"])
    def windows_run(self, text: str, wait_time: float = 3.0) -> None:
        """Use Windows run window to launch application.

        Activated by pressing `win + r`.

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
        """Use Windows search window to launch application.

        Activated by pressing `win + s`.

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
        """Closes current active window or logs a warning message.

        Example:

        .. code-block:: robotframework

            Close Current Window
        """
        if not self.ctx.window:
            self.ctx.logger.warning("There is no active window")
            return False
        pid = self.ctx.window.item.ProcessId
        name = self.ctx.window.item.Name
        self.ctx.logger.info(
            'Closing window with Name:"%s", ProcessId: %s' % (name, pid)
        )
        os.kill(pid, signal.SIGTERM)
        self.ctx.window = None
        return True
