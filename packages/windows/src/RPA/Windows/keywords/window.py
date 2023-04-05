import os
import signal
import time
from typing import Dict, List, Optional

from RPA.core.windows.locators import Locator, LocatorMethods, WindowsElement
from RPA.core.windows.window import WindowMethods

from RPA.Windows import utils
from RPA.Windows.keywords import (
    ElementNotFound,
    WindowControlError,
    keyword,
    with_timeout,
)


class WindowKeywords(WindowMethods):
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
        :param main: on `True` (default) starts the search from desktop level, on
            `False` it will continue to search for child elements given the set anchor
            or current active window
        :return: `WindowsElement` object

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
                f"Could not locate window with locator: {locator!r} "
                f"(timeout: {self.current_timeout})"
            )

        if foreground:
            self.foreground_window()
        if wait_time:
            time.sleep(wait_time)
        return window

    @keyword(tags=["window"])
    @with_timeout
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

            Control Window   subname:"Sage 50" type:Window
            # actions on the main application window
            # ...
            # get control of child window of Sage application
            Control Child Window   subname:"Test Company" depth:1
        """
        return self.control_window(locator, foreground, wait_time, timeout, main=False)

    def _find_window(self, locator, main) -> Optional[WindowsElement]:
        try:
            # A `root_element=None` will use the `anchor` or `window` as root later
            #  on. (fallbacks to Desktop)
            root_element = None
            if main:
                root_element = LocatorMethods.get_desktop_element(locator)
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

    def _resize_window(
        self, locator: Optional[Locator] = None, *, attribute: str
    ) -> WindowsElement:
        if locator:
            self.control_window(locator)
        window = self.window
        if window is None:
            raise WindowControlError("There is no active window")

        attr_func = getattr(window.item, attribute, None)
        if attr_func:
            attr_func()
        else:
            self.logger.warning(
                "Element %r does not have the %r attribute", window, attribute
            )
        return window

    @keyword(tags=["window"])
    def minimize_window(self, locator: Optional[Locator] = None) -> WindowsElement:
        """Minimize the current active window or the window defined
        by the locator.

        :param locator: string locator or element
        :return: `WindowsElement` object

        Example:

        .. code-block:: robotframework

            ${window} =    Minimize Window  # Current active window
            Minimize Window    executable:Spotify.exe
        """
        return self._resize_window(locator, attribute="Minimize")

    @keyword(tags=["window"])
    def maximize_window(self, locator: Optional[Locator] = None) -> WindowsElement:
        """Maximize the current active window or the window defined
        by the locator.

        :param locator: string locator or element
        :return: `WindowsElement` object

        Example:

        .. code-block:: robotframework

            ${window} =    Maximize Window  # Current active window
            Maximize Window    executable:Spotify.exe
        """
        return self._resize_window(locator, attribute="Maximize")

    @keyword(tags=["window"])
    def restore_window(self, locator: Optional[Locator] = None) -> WindowsElement:
        """Window restore the current active window or the window
        defined by the locator.

        :param locator: string locator or element
        :return: `WindowsElement` object

        Example:

        .. code-block:: robotframework

            ${window} =    Restore Window  # Current active window
            Restore Window    executable:Spotify.exe
        """
        return self._resize_window(locator, attribute="Restore")

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
        return super().list_windows(
            icons=icons, icon_save_directory=icon_save_directory
        )

    @keyword(tags=["window"])
    def windows_run(self, text: str, wait_time: float = 3.0) -> None:
        """Use Windows Run window to launch an application.

        Activated by pressing `Win + R`. Then the app name is typed in and finally the
        "Enter" key is pressed.

        :param text: Text to enter into the Run input field. (e.g. `Notepad`)
        :param wait_time: Time to sleep after the searched app is executed. (3s by
            default)

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Run Notepad
                Windows Run   notepad

        **Example: Python**

        .. code-block:: python

            from RPA.Windows import Windows
            lib = Windows()

            def run_notepad():
                lib.windows_run("notepad")
        """
        # NOTE(cmin764): The waiting time after each key set sending can be controlled
        #  globally and individually with `Set Wait Time`.
        self.ctx.send_keys(keys="{Win}r")
        self.ctx.send_keys(keys=text, interval=0.01)
        self.ctx.send_keys(send_enter=True)
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
            # We just closed the anchor as well (along with its relatives), so clear
            #  it out properly.
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
        root_element = LocatorMethods.get_desktop_element(locator)
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
            raise WindowControlError(f"Couldn't find any window with {locator!r}")

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
