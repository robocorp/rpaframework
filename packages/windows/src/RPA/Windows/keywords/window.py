import os
import signal
import time
from typing import List, Dict, Union

from RPA.Windows.keywords import (
    keyword,
    ElementNotFound,
    LibraryContext,
    WindowControlError,
)
from RPA.Windows import utils
from .locators import WindowsElement

if utils.is_windows():
    import uiautomation as auto


class WindowKeywords(LibraryContext):
    """Keywords for handling Window controls"""

    @keyword(tags=["window"])
    def control_window(
        self,
        locator: Union[WindowsElement, str] = None,
        foreground: bool = True,
        wait_time: float = None,
        timeout: float = None,
        main: bool = True,
    ) -> WindowsElement:
        """Controls the window defined by the locator.

        This means that this window is used as a root element
        for all the following keywords using locators.

        Returns `WindowsElement`.

        :param locator: string locator or Control element
        :param foreground: True to bring window to foreground
        :param wait_time: time to wait after activating a window
        :param timeout: float value in seconds, see keyword
         ``Set Global Timeout``
        :param main: on True (default) starts search from desktop level,
         on False will continue search on child elements of current
         active window
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            Control Window   Calculator
            Control Window   name:Calculator
            Control Window   subname:Notepad
            Control Window   regex:.*Notepad
            ${window}=  Control Window   executable:Spotify.exe
        """
        current_timeout = timeout or self.ctx.global_timeout
        if timeout:
            auto.SetGlobalSearchTimeout(timeout)
        if isinstance(locator, WindowsElement):
            self.ctx.window = locator
        elif "type:" in locator:
            self.ctx.window = self._find_window(locator, main)
        else:
            window_locator = f"{locator} and type:WindowControl"
            pane_locator = f"{locator} and type:PaneControl"
            self.ctx.window = self._find_window(window_locator, main)
            if not self.ctx.window:
                self.ctx.window = self._find_window(pane_locator, main)

        auto.SetGlobalSearchTimeout(self.ctx.global_timeout)
        if not self.ctx.window or not self.ctx.window.item.Exists():
            raise WindowControlError(
                'Could not locate window with locator: "%s" and timeout:%s'
                % (locator, current_timeout)
            )
        if foreground:
            self.foreground_window()
        if wait_time:
            time.sleep(wait_time)
        return self.ctx.window

    @keyword(tags=["window"])
    def control_child_window(
        self,
        locator: Union[WindowsElement, str] = None,
        foreground: bool = True,
        wait_time: float = None,
        timeout: float = None,
    ) -> WindowsElement:
        """Get control of child window of the active window
        by locator.

        :param locator: string locator or Control element
        :param foreground: True to bring window to foreground
        :param wait_time: time to wait after activeting a window
        :param timeout: float value in seconds, see keyword
         ``Set Global Timeout``
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            Control Window   subname:'Sage 50' type:Window
            # actions on the main application window
            # ...
            # get control of child window of Sage application
            Control Child Window   subname:'Test Company' depth:1
        """
        self.control_window(locator, foreground, timeout, wait_time, False)
        return self.ctx.window

    def _find_window(self, locator, main) -> bool:
        try:
            # root_element = None means using self.ctx.window as root
            root_element = (
                WindowsElement(auto.GetRootControl(), locator) if main else None
            )

            window = self.ctx.get_element(locator, root_element=root_element)
            return window
        except ElementNotFound:
            return None
        except LookupError:
            return None

    @keyword(tags=["window"])
    def foreground_window(
        self, locator: Union[WindowsElement, str] = None
    ) -> WindowsElement:
        """Bring the current active window or the window defined
        by the locator to the foreground.

        :param locator: string locator or Control element
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            ${window}=  Foreground Window   Calculator
        """
        if locator:
            return self.control_window(locator, foreground=True)
        if not self.ctx.window.item:
            raise WindowControlError("There is no active window")
        utils.call_attribute_if_available(self.ctx.window.item, "SetFocus")
        utils.call_attribute_if_available(self.ctx.window.item, "SetActive")
        self.ctx.window.item.MoveCursorToMyCenter(simulateMove=self.ctx.simulate_move)
        return self.ctx.window

    @keyword(tags=["window"])
    def minimize_window(
        self, locator: Union[WindowsElement, str] = None
    ) -> WindowsElement:
        """Minimize the current active window or the window defined
        by the locator.

        :param locator: string locator or Control element
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            ${window}=  Minimize Window   # Current active window
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
            return self.ctx.window
        self.ctx.window.item.Minimize()
        return self.ctx.window

    @keyword(tags=["window"])
    def maximize_window(
        self, locator: Union[WindowsElement, str] = None
    ) -> WindowsElement:
        """Minimize the current active window or the window defined
        by the locator.

        :param locator: string locator or Control element
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            Maximize Window   # Current active window
            ${window}=  Maximize Window   executable:Spotify.exe
        """
        if locator:
            self.control_window(locator)
        if not self.ctx.window:
            raise WindowControlError("There is no active window")
        if not hasattr(self.ctx.window.item, "Maximize"):
            raise WindowControlError("Window does not have attribute Maximize")
        self.ctx.window.item.Maximize()
        return self.ctx.window

    @keyword(tags=["window"])
    def restore_window(
        self, locator: Union[WindowsElement, str] = None
    ) -> WindowsElement:
        """Window restore the current active window or the window
        defined by the locator.

        :param locator: string locator or Control element
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            ${window}=  Restore Window   # Current active window
            Restore Window   executable:Spotify.exe
        """
        if locator:
            self.control_window(locator)
        if not self.ctx.window:
            raise WindowControlError("There is no active window")
        if not hasattr(self.ctx.window.item, "Restore"):
            raise WindowControlError("Window does not have attribute Restore")
        self.ctx.window.item.Restore()
        return self.ctx.window

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

        :return: True if close was successful, False if not

        Example:

        .. code-block:: robotframework

            ${status}=  Close Current Window
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
