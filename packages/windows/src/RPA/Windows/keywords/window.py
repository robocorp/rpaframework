import base64
import os
import signal
import time
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

from RPA.Windows import utils
from RPA.Windows.keywords import (
    ElementNotFound,
    LibraryContext,
    WindowControlError,
    keyword,
    with_timeout,
)
from .locators import Locator, WindowsElement

if utils.IS_WINDOWS:
    import uiautomation as auto
    import win32process
    import win32api
    import win32con
    import win32ui
    import win32gui


class WindowKeywords(LibraryContext):
    """Keywords for handling Window controls"""

    @staticmethod
    def _iter_locator(locator: Optional[Locator]) -> Optional[Locator]:
        if not locator:
            yield locator  # usually `None`
        elif isinstance(locator, WindowsElement):
            yield locator  # yields element as it is
        elif "type:" in locator or "control:" in locator:
            yield locator  # yields rigid string locator
        else:
            # yields flexible string locators with different types
            yield f"{locator} and type:WindowControl"
            yield f"{locator} and type:PaneControl"

    @keyword(tags=["window"])
    @with_timeout
    def control_window(
        self,
        locator: Optional[Locator] = None,
        foreground: bool = True,
        wait_time: Optional[float] = None,
        timeout: Optional[float] = None,  # pylint: disable=unused-argument
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
        for loc in self._iter_locator(locator):
            self.ctx.window_element = self._find_window(
                loc, main
            )  # works with windows too
            if self.ctx.window_element:
                break  # first window found is enough

        window = self.window
        if window is None:
            raise WindowControlError(
                f'Could not locate window with locator: "{locator}" '
                f"(timeout: {self.current_timeout})"
            )

        if foreground:
            self.foreground_window()
        if wait_time:
            time.sleep(wait_time)
        return window

    @keyword(tags=["window"])
    def control_child_window(
        self,
        locator: Optional[Locator] = None,
        foreground: bool = True,
        wait_time: Optional[float] = None,
        timeout: Optional[float] = None,
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
        return self.control_window(locator, foreground, wait_time, timeout, main=False)

    def _find_window(self, locator, main) -> Optional[WindowsElement]:
        try:
            # `root_element = None` means using the `anchor` or `window` as root later
            #  on. (fallbacks to Desktop)
            root_element = (
                WindowsElement(auto.GetRootControl(), locator) if main else None
            )
            window = self.ctx.get_element(locator, root_element=root_element)
            return window
        except (ElementNotFound, LookupError):
            return None

    @keyword(tags=["window"])
    def foreground_window(self, locator: Optional[Locator] = None) -> WindowsElement:
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
        window = self.window
        if window is None:
            raise WindowControlError("There is no active window")

        utils.call_attribute_if_available(window.item, "SetFocus")
        utils.call_attribute_if_available(window.item, "SetActive")
        window.item.MoveCursorToMyCenter(simulateMove=self.ctx.simulate_move)
        return window

    @keyword(tags=["window"])
    def minimize_window(self, locator: Optional[Locator] = None) -> WindowsElement:
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
        window = self.window
        if window is None:
            raise WindowControlError("There is no active window")

        if hasattr(window.item, "Minimize"):
            window.item.Minimize()
        else:
            self.logger.warning(
                "Control '%s' does not have attribute Minimize" % window
            )
        return window

    @keyword(tags=["window"])
    def maximize_window(self, locator: Optional[Locator] = None) -> WindowsElement:
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
        window = self.window
        if window is None:
            raise WindowControlError("There is no active window")

        if not hasattr(window.item, "Maximize"):
            raise WindowControlError("Window does not have attribute Maximize")

        window.item.Maximize()
        return window

    @keyword(tags=["window"])
    def restore_window(self, locator: Optional[Locator] = None) -> WindowsElement:
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
        window = self.window
        if window is None:
            raise WindowControlError("There is no active window")

        if not hasattr(window.item, "Restore"):
            raise WindowControlError("Window does not have attribute Restore")

        window.item.Restore()
        return window

    @keyword(tags=["window"])
    def list_windows(
        self, icons: bool = False, icon_save_directory: Optional[str] = None
    ) -> List[Dict]:
        """List all window element on the system.

        :param icons: on True dictionary will contain Base64
         string of the icon, default False
        :param icon_save_directory: if set will save retrieved icons
         into this filepath, by default icon files are not saved
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
            fullpath = None
            try:
                handle = win32api.OpenProcess(
                    win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid
                )
                fullpath = win32process.GetModuleFileNameEx(handle, 0)
            except Exception as err:  # pylint: disable=broad-except
                self.logger.info("Open process error in `List Windows`: %s", str(err))
            icon_string = (
                self.get_icon(fullpath, icon_save_directory) if icons else None
            )
            info = {
                "title": win.Name,
                "pid": pid,
                "name": process_list[pid] if pid in process_list else None,
                "path": fullpath,
                "handle": win.NativeWindowHandle,
                "icon": icon_string,
            }
            if icons and not icon_string:
                self.logger.info("Icon for %s returned empty", win.Name)
            win_list.append(info)
        return win_list

    @staticmethod
    def get_icon(
        filepath: str, icon_save_directory: Optional[str] = None
    ) -> Optional[str]:
        if not filepath:
            return None

        # TODO: Get different sized icons.
        small, large = win32gui.ExtractIconEx(filepath, 0, 10)
        if len(small) > 0:
            win32gui.DestroyIcon(small[0])
        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()

        ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)
        hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
        hdc = hdc.CreateCompatibleDC()

        hdc.SelectObject(hbmp)

        image_string = None
        if len(large) > 0:
            executable_path = Path(filepath)
            hdc.DrawIcon((0, 0), large[0])
            result_image_file = f"icon_{executable_path.name}.png"
            if icon_save_directory:
                result_image_file = Path(icon_save_directory) / result_image_file
                result_image_file = result_image_file.resolve()
            bmpstr = hbmp.GetBitmapBits(True)
            img = Image.frombuffer("RGBA", (32, 32), bmpstr, "raw", "BGRA", 0, 1)
            img.save(result_image_file)
            with open(result_image_file, "rb") as img_file:
                image_string = base64.b64encode(img_file.read())
            if not icon_save_directory:
                Path(result_image_file).unlink()

        return image_string

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
        search_cmd = "{Win}s"
        if utils.get_win_version() == "11":
            search_cmd = search_cmd.rstrip("s")
        self.ctx.send_keys(None, search_cmd)
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
        window = self.window
        if window is None:
            self.logger.warning("There is no active window!")
            self.ctx.window_element = None
            return False

        pid = window.item.ProcessId
        self.logger.info("Closing window with name: %s (PID: %d)", window.name, pid)
        os.kill(pid, signal.SIGTERM)
        self.ctx.window_element = None

        anchor = self.ctx.anchor_element
        if anchor and window.is_sibling(anchor):
            # We just closed the anchor (along with its relatives), so clear it out
            #  properly.
            self.ctx.clear_anchor()

        return True

    @keyword(tags=["window"])
    @with_timeout
    def close_window(
        self,
        locator: Optional[Locator] = None,
        timeout: Optional[float] = None,  # pylint: disable=unused-argument
    ) -> int:
        """Closes identified windows or logs the problems.

        :param locator: String locator or `Control` element.
        :param timeout: float value in seconds, see keyword
         ``Set Global Timeout``
        :return: How many windows were found and closed.

        Example:

        .. code-block:: robotframework

            ${closed_count} =     Close Window    Calculator
        """
        # Starts the search from Desktop level.
        root_element = WindowsElement(auto.GetRootControl(), locator)
        # With all flavors of locators. (if flexible)
        for loc in self._iter_locator(locator):
            try:
                elements: List[WindowsElement] = self.ctx.get_elements(
                    loc, root_element=root_element
                )
            except (ElementNotFound, LookupError):
                continue
            break
        else:
            raise WindowControlError(
                f"Couldn't find any window with locator: {locator}"
            )

        closed = 0
        for element in elements:
            self.logger.debug("Controlling and closing window: %s", element)
            try:
                self.control_window(element)
                closed += int(self.close_current_window())
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.warning("Couldn't close window %r due to: %s", element, exc)
        return closed

    @keyword(tags=["window"])
    def get_os_version(self) -> str:
        """Returns the current Windows major version as string.

        Example:

        .. code-block:: robotframework

            ${ver} =     Get OS Version
            Log     ${ver}  # 10
        """
        return utils.get_win_version()
