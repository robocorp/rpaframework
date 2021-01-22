# pylint: disable=c-extension-no-member
import json
import logging
import os
import platform
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

from RPA.Desktop.Clipboard import Clipboard
from RPA.Desktop.OperatingSystem import OperatingSystem
from RPA.Images import Images
from RPA.core.helpers import delay, clean_filename


if platform.system() == "Windows":
    import ctypes
    import win32api
    import win32com.client
    import win32con
    import win32security
    import pywinauto
    import win32gui
    from comtypes import COMError


def write_element_info_as_json(
    elements: Any, filename: str, path: str = "output/json"
) -> None:
    """Write list of elements into json file

    :param elements: list of elements to write
    :param filename: output file name
    :param path: output directory, defaults to "output/json"
    """
    elements = elements if isinstance(elements, list) else [elements]
    filename = Path(f"{path}/{filename}.json")
    os.makedirs(filename.parent, exist_ok=True)
    with open(filename, "w") as outfile:
        json.dump(elements, outfile, indent=4, sort_keys=True)


class ElementNotFoundError(Exception):
    """Raised when expected element is not found"""


class MenuItemNotFoundError(Exception):
    """Raised when expected menu item is not found"""


class UnknownWindowsBackendError(Exception):
    """Raised when unknown Windows backend is set"""


SUPPORTED_BACKENDS = ["uia", "win32"]
WINDOWS_LOCATOR_STRATEGIES = {
    "name": "name",
    "class_name": "class_name",
    "class": "class_name",
    "control_type": "control_type",
    "type": "control_type",
    "automation_id": "automation_id",
    "id": "automation_id",
    "partial name": "partial name",
    "regexp": "regexp",
}


class Windows(OperatingSystem):
    """`Windows` is a library for managing the Windows operating system.

    **Running Windows applications**

    Windows applications can be started in several ways. The library supports
    the following keywords:

    - Open Application (dispatch Office applications)
    - Open File (open the file as process which opens the associated application)
    - Open Executable (uses pywinauto start)
    - Open Using Run Dialog (uses Windows run dialog)
    - Open From Search (uses Windows search dialog)

    **Locators**

    `Locator` is used to identify the element for interaction - usually for a mouse click.

    Locators can investigated for application once it has been opened by calling
    the keyword `get_windows_elements` which can store locator information into JSON file
    and `screenshot` of the element into an image file.

    **Identifying locator**

    The element needs to be identified by a unique method, for example, "Three" for button 3
    in the Calculator application. It can be given either as `Three` or `name:Three`.

    Possible search criterias:

    - name
    - class (class_name)
    - type (control_type)
    - id (automation_id)
    - any if none was defined

    The current method of inspecting elements on Windows is `inspect.exe` which is part
    of `Windows SDK <https://docs.microsoft.com/en-us/windows/win32/winauto/inspect-objects>`_.

    **Keyboard**

    The keyword `send_keys` can be used to send keys to the active window. The keyword
    `type_keys` sends keys to the active window element.

    Special key codes are documented on `pywinauto <https://pywinauto.readthedocs.io/en/latest/code/pywinauto.keyboard.html#>`_
    documentation page.

    **FAQ**

    Q. I see error message `AttributeError: module 'win32com.gen_py.00020813-0000-0000-C000-000000000046x0x1x9' has no attribute 'CLSIDToClassMap'`

    A. From PowerShell run this command: `Remove-Item -path $env:LOCALAPPDATA\\Temp\\gen_py -recurse`

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library          RPA.Desktop.Windows
        Suite Teardown   Close all applications

        *** Tasks ***
        Open Calculator using run dialog
            ${result}=              Open using run dialog    calc.exe   Calculator
            ${result}=              Get Window Elements
            Send Keys               5*2=
            ${result}=              Get element             partial name:Display is
            Log Many                ${result}
            ${result}=              Get element rich text   id:CalculatorResults
            Should Be Equal As Strings  ${result}  Display is 10
            ${result}=              Get element rectangle   partial name:Display is
            ${result}=              Is Element Visible      CalculatorResults
            ${result}=              Is Element Enabled      partial name:Display is

    **Python**

    .. code-block:: python

        from RPA.Desktop.Windows import Windows

        win = Windows()

        def open_calculator():
            win.open_from_search("calc.exe", "Calculator")
            elements = win.get_window_elements()

        def make_calculations(expression):
            win.send_keys(expression)
            result = win.get_element_rich_text('id:CalculatorResults')
            return int(result.strip('Display is '))

        if __name__ == "__main__":
            open_calculator()
            exp = '5*2='
            result = make_calculations(exp)
            print(f"Calculation result of '{exp}' is '{result}'")
            win.close_all_applications()
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self, backend: str = "uia") -> None:
        OperatingSystem.__init__(self)
        self._apps = {}
        self._app_instance_id = 0
        self._active_app_instance = -1
        self.set_windows_backend(backend)
        self.app = None
        self.dlg = None
        self.windowtitle = None
        self.logger = logging.getLogger(__name__)
        self.clipboard = Clipboard()
        self.elements = None
        self.controls = None

    def set_windows_backend(self, backend: str) -> None:
        """Set Windows backend which is used to interact with Windows
        applications

        Allowed values defined by `SUPPORTED_BACKENDS`

        :param backend: name of the backend to use

        Example:

        .. code-block:: robotframework

            Set Windows Backend   uia
            Open Executable   calc.exe  Calculator
            Set Windows Backend   win32
            Open Executable   calc.exe  Calculator

        """
        if backend and backend.lower() in SUPPORTED_BACKENDS:
            self._backend = backend.lower()
        else:
            raise UnknownWindowsBackendError(
                "Unsupported Windows backend: %s" % backend
            )

    def _add_app_instance(
        self,
        app: Any = None,
        dialog: bool = True,
        params: dict = None,
    ) -> int:
        params = params or {}
        self._app_instance_id += 1
        process_id = None
        handle = None
        if app:
            self.app = app
            if hasattr(app, "process"):
                process_id = app.process
            handle = win32gui.GetForegroundWindow()

        default_params = {
            "app": app,
            "id": self._app_instance_id,
            "dialog": dialog,
            "process_id": process_id,
            "handle": handle,
            "dispatched": False,
        }

        self._apps[self._app_instance_id] = {**default_params, **params}

        self.logger.debug(
            "Added app instance %s: %s",
            self._app_instance_id,
            self._apps[self._app_instance_id],
        )
        self._active_app_instance = self._app_instance_id
        return self._active_app_instance

    def switch_to_application(self, app_id: int) -> None:
        """Switch to application by id.

        :param app_id: application's id
        :raises ValueError: if application is not found by given id

        Example:

        .. code-block:: robotframework

            ${app1}    Open Application   Excel
            ${app2}    Open Application   Word
            Switch To Application   ${app1}

        """
        if app_id and app_id in self._apps.keys():
            app = self.get_app(app_id)
            self._active_app_instance = app_id
            self.app = app["app"]
            if "windowtitle" in app:
                self.open_dialog(app["windowtitle"], existing_app=True)
                delay(0.5)
                self.restore_dialog(app["windowtitle"])
        else:
            raise ValueError(f"No open application with id '{app_id}'")

    def get_open_applications(self):
        """Get list of all open applications

        Returns a dictionary

        Example:

        .. code-block:: robotframework

            ${app1}    Open Application   Excel
            ${app2}    Open Executable    calc.exe  Calculator
            ${app3}    Open File          /path/to/myfile.txt
            &{apps}    Get Open Applications

        """
        return self._apps

    def get_app(self, app_id: int = None) -> Any:
        """Get application object by id

        By default returns active_application application object.

        :param app_id: id of the application to get, defaults to None
        :return: application object

        Example:

        .. code-block:: robotframework

            ${app1}        Open Application   Excel
            &{appdetails}  Get App   ${app1}

        """
        if app_id is None and self._active_app_instance != -1:
            return self._apps[self._active_app_instance]
        else:
            return self._apps[app_id]

    def open_application(self, application: str) -> int:
        """Open application by dispatch method

        This keyword is used to launch Microsoft applications like
        Excel, Word, Outlook and Powerpoint.

        :param application: name of the application as `str`
        :return: application instance id

        Example:

        .. code-block:: robotframework

            ${app1}    Open Application   Excel
            ${app2}    Open Application   Word

        """
        self.logger.info("Open application: %s", application)
        app = win32com.client.gencache.EnsureDispatch(f"{application}.Application")
        app.Visible = True
        # show eg. file overwrite warning or not
        if hasattr(self.app, "DisplayAlerts"):
            app.DisplayAlerts = False
        params = {
            "dispatched": True,
            "startkeyword": "Open Application",
        }
        return self._add_app_instance(app, dialog=False, params=params)

    def open_file(
        self,
        filename: str,
        windowtitle: str = None,
        wildcard: bool = False,
        timeout: int = 10,
    ) -> bool:
        """Open associated application when opening file

        :param filename: path to file
        :param windowtitle: name of the window
        :param wildcard: set True for inclusive window title search, default False
        :param timeout: time to wait for dialog to appear
        :return: True if application is opened, False if not

        Example:

        .. code-block:: robotframework

            ${app1}    Open File   /path/to/myfile.txt

        """
        self.logger.info("Open file: %s", filename)
        if platform.system() == "Windows":
            # pylint: disable=no-member
            os.startfile(filename)
        elif platform.system() == "Darwin":
            subprocess.call(["open", filename])
        else:
            subprocess.call(["xdg-open", filename])
        returnvalue = True
        if windowtitle:
            app_instance = self.open_dialog(
                windowtitle, wildcard=wildcard, timeout=timeout
            )
            if app_instance > 0:
                self._apps[app_instance]["executable"] = filename
                self._apps[app_instance]["startkeyword"] = "Open File"
            else:
                returnvalue = False
        return returnvalue

    def open_executable(
        self,
        executable: str,
        windowtitle: str,
        backend: str = None,
        work_dir: str = None,
        wildcard: bool = False,
    ) -> int:
        """Open Windows executable. Window title name is required
        to get handle on the application.

        :param executable: name of the executable
        :param windowtitle: name of the window
        :param backend: set Windows backend, default None means using
         library default value
        :param work_dir: path to working directory, default None
        :param wildcard: set True for inclusive window title search, default False
        :return: application instance id

        Example:

        .. code-block:: robotframework

            ${app1}    Open Executable   calc.exe  Calculator
            ${app2}    Open Executable   notepad.exe  Notepad   wildcard=True

        """
        self.logger.info("Opening executable: %s - window: %s", executable, windowtitle)
        if backend:
            self.set_windows_backend(backend)

        app = pywinauto.Application(backend=self._backend).start(
            cmd_line=executable, work_dir=work_dir
        )
        app_instance = self.open_dialog(windowtitle, wildcard=wildcard)
        self._apps[app_instance]["app"] = app
        self._apps[app_instance]["executable"] = executable
        self._apps[app_instance]["startkeyword"] = "Open Executable"
        return app_instance

    def open_using_run_dialog(
        self,
        executable: str,
        windowtitle: str,
        timeout: int = 10,
        wildcard: bool = False,
    ) -> int:
        """Open application using Windows run dialog.
        Window title name is required to get handle on the application.

        :param executable: name of the executable
        :param windowtitle: name of the window
        :param timeout: time to wait for dialog to appear
        :param wildcard: set True for inclusive window title search, default False
        :return: application instance id

        Example:

        .. code-block:: robotframework

            ${app1}    Open Using Run Dialog  notepad  Untitled - Notepad
            ${app2}    Open Using Run Dialog  notepad  Notepad    wildcard=True

        """
        self.send_keys("{VK_LWIN down}r{VK_LWIN up}")
        delay(1)

        self.send_keys_to_input(executable, send_delay=0.2, enter_delay=0.5)

        app_instance = self.open_dialog(windowtitle, timeout=timeout, wildcard=wildcard)
        self._apps[app_instance]["executable"] = executable
        self._apps[app_instance]["startkeyword"] = "Open Using Run Dialog"
        return app_instance

    def open_from_search(
        self,
        executable: str,
        windowtitle: str,
        timeout: int = 10,
        wildcard: bool = False,
    ) -> int:
        """Open application using Windows search dialog.
        Window title name is required to get handle on the application.

        :param executable: name of the executable
        :param windowtitle: name of the window
        :param timeout: time to wait for dialog to appear
        :param wildcard: set True for inclusive window title search, default False
        :return: application instance id

        Example:

        .. code-block:: robotframework

            ${app1}    Open From Search  calculator  Calculator
            ${app2}    Open From Search  notepad  Notepad  wildcard=True

        """
        self.logger.info("Run from start menu: %s", executable)
        self.send_keys("{LWIN}")
        delay(1)

        self.send_keys_to_input(executable)

        app_instance = self.open_dialog(windowtitle, timeout=timeout, wildcard=wildcard)
        self._apps[app_instance]["executable"] = executable
        self._apps[app_instance]["startkeyword"] = "Open From Search"
        return app_instance

    def get_spaced_string(self, text):
        """Replace spaces in a text with `pywinauto.keyboard`
        space characters `{VK_SPACE}`

        :param text: replace spaces in this string

        Example:

        .. code-block:: robotframework

            ${txt}    Get Spaced String   My name is Bond
            # ${txt} = My{VK_SPACE}name{VK_SPACE}is{VK_SPACE}Bond
            Send Keys To Input  ${txt}

        """
        return text.replace(" ", "{VK_SPACE}")

    def send_keys_to_input(
        self,
        keys_to_type: str,
        with_enter: bool = True,
        send_delay: float = 0.5,
        enter_delay: float = 1.5,
    ) -> None:
        """Send keys to windows and add ENTER if `with_enter` is True

        At the end of send_keys there is by default 0.5 second delay.
        At the end of ENTER there is by default 1.5 second delay.

        :param keys_to_type: keys to type into Windows
        :param with_enter: send ENTER if `with_enter` is True
        :param send_delay: delay after send_keys
        :param enter_delay: delay after ENTER

        Example:

        .. code-block:: robotframework

            ${txt}    Get Spaced String   My name is Bond, James Bond
            Send Keys To Input  ${txt}    with_enter=False
            Send Keys To Input  {ENTER}THE   send_delay=5.0  with_enter=False
            Send Keys To Input  {VK_SPACE}-{VK_SPACE}END   enter_delay=5.0

        """
        # Set keyboard layout for Windows platform
        if platform.system() == "Windows":
            win32api.LoadKeyboardLayout("00000409", 1)

        self.send_keys(keys_to_type)
        delay(send_delay)
        if with_enter:
            self.send_keys("{ENTER}")
            delay(enter_delay)

    def minimize_dialog(self, windowtitle: str = None) -> None:
        """Minimize window by its title

        :param windowtitle: name of the window, default `None` means that
         active window is going to be minimized

        Example:

        .. code-block:: robotframework

            Open Using Run Dialog  calc     Calculator
            Open Using Run Dialog  notepad  Untitled - Notepad
            Minimize Dialog    # Current window (Notepad)
            Minimize Dialog    Calculator

        """
        windowtitle = (
            windowtitle or self._apps[self._active_app_instance]["windowtitle"]
        )
        self.logger.info("Minimize dialog: %s", windowtitle)
        self.dlg = pywinauto.Desktop(backend=self._backend)[windowtitle]
        self.dlg.minimize()

    def restore_dialog(self, windowtitle: str = None) -> None:  # noqa: C901
        """Restore window by its title

        :param windowtitle: name of the window, default `None` means that
         active window is going to be restored

        Example:

        .. code-block:: robotframework

            Open Using Run Dialog  notepad  Untitled - Notepad
            Minimize Dialog
            Sleep             1s
            Restore Dialog
            Sleep             1s
            Restore Dialog    Untitled - Notepad

        """
        # TODO. Handle too compled method
        self.logger.info("Restore dialog: %s", windowtitle)
        if windowtitle is None and self._active_app_instance == -1:
            raise ValueError(
                "There are no applications opened by library or window title is empty"
            )
        app = None
        handle = None
        if windowtitle is None:
            app = self._apps[self._active_app_instance]["app"]
            handle = self._apps[self._active_app_instance]["handle"]
            windowtitle = self._apps[self._active_app_instance]["windowtitle"]
        else:
            for app_id, app in self._apps.items():
                if "windowtitle" in app.keys() and windowtitle == app["windowtitle"]:
                    application_id = app_id
                    app = self._apps[application_id]["app"]
                    handle = self._apps[application_id]["handle"]
        try:
            if app and handle > 0:
                app.window(handle=handle).restore()
            else:
                wins = self.get_window_list()
                for win in wins:
                    if windowtitle == win["title"]:
                        handle = win["handle"]
                        break
                if handle and handle > 0:
                    self.connect_by_handle(handle, windowtitle=windowtitle)
                    self.restore_dialog()
                else:
                    raise ValueError("Could not restore dialog: %s" % windowtitle)
        except pywinauto.findwindows.ElementAmbiguousError as e:
            self.logger.info("Could not restore dialog, %s", str(e))

    def open_dialog(
        self,
        windowtitle: str = None,
        highlight: bool = False,
        timeout: int = 10,
        existing_app: bool = False,
        wildcard: bool = False,
    ) -> Any:
        """Open window by its title.

        :param windowtitle: name of the window, defaults to active window if None
        :param highlight: draw outline for window if True, default False
        :param timeout: time to wait for dialog to appear
        :param existing_app: set True if selecting window which library has already
         accessed, default False
        :param wildcard: set True for inclusive window title search, default False

        Example:

        .. code-block:: robotframework

            Open Dialog       Untitled - Notepad
            Open Dialog       Untitled - Notepad   highlight=True   timeout=5
            Open Dialog       Notepad   wildcard=True

        """
        self.logger.info("Open dialog: '%s'", windowtitle)

        app_instance = None
        end_time = time.time() + float(timeout)
        while time.time() < end_time and app_instance is None:
            for window in self.get_window_list():
                if (not wildcard and windowtitle == window["title"]) or (
                    wildcard and windowtitle in window["title"]
                ):
                    self.windowtitle = window["title"]
                    app_instance = self.connect_by_handle(
                        window["handle"],
                        windowtitle=self.windowtitle,
                        existing_app=existing_app,
                    )
                    break
            time.sleep(0.1)

        if app_instance is None:
            raise ValueError(
                "No window with title '%s', wildcard: %s" % (windowtitle, wildcard)
            )

        if highlight:
            self.dlg.draw_outline()

        return app_instance

    def connect_by_pid(self, app_pid: str, windowtitle: str = None) -> Any:
        """Connect to application by its pid

        :param app_pid: process id of the application
        :param windowtitle: name of the window, defaults to active window if None

        Example:

        .. code-block:: robotframework

            ${appid}  Connect By PID  3231

        """
        self.logger.info("Connect to application pid: %s", app_pid)
        window_list = self.get_window_list()
        for win in window_list:
            if win["pid"] == app_pid:
                if windowtitle is None or (windowtitle and windowtitle in win["title"]):
                    self.logger.info(
                        "PID:%s matched window title:%s", win["pid"], win["title"]
                    )
                    return self.connect_by_handle(win["handle"], windowtitle)
        return None

    def connect_by_handle(
        self, handle: int, windowtitle: str = None, existing_app: bool = False
    ) -> Any:
        """Connect to application by its handle

        :param handle: handle of the application
        :param windowtitle: name of the window, defaults to active window if None
        :param existing_app: set True if selecting window which library has already
         accessed, default False

        Example:

        .. code-block:: robotframework

            ${appid}  Connect By Handle  88112

        """
        self.logger.info("Connect to application handle: %s", handle)
        app_instance = None
        app = pywinauto.Application(backend=self._backend).connect(
            handle=handle, visible_only=False
        )
        self.dlg = app.window(handle=handle)
        self.dlg.set_focus()
        params = None
        if existing_app:
            for key in self._apps:
                if self._apps[key]["handle"] == handle:
                    app_instance = key
                    break
        else:
            if windowtitle is not None:
                params = {"windowtitle": windowtitle}
            app_instance = self._add_app_instance(app=app, params=params, dialog=False)
        self.refresh_window()
        return app_instance

    def close_all_applications(self) -> None:
        """Close all applications

        Example:

        .. code-block:: robotframework

            Open Application   Excel
            Open Application   Word
            Open Executable    notepad.exe   Untitled - Notepad
            Close All Applications

        """
        self.logger.info("Closing all applications")
        self.logger.debug("Applications in memory: %d", len(self._apps))
        for aid in list(self._apps):
            self.quit_application(aid)
            del self._apps[aid]

    def quit_application(self, app_id: str = None, send_keys: bool = False) -> None:
        """Quit an application by application id or
        active application if `app_id` is None.

        :param app_id: application_id, defaults to None
        :param send_keys: if ALT+F4 should be used to quit, default False

        Example:

        .. code-block:: robotframework

            ${app1}   Open Application   Excel
            ${app2}   Open Application   Word
            Quit Application  ${app1}

        """
        app = self.get_app(app_id)
        self.logger.info("Quit application: %s (%s)", app_id, app)
        if send_keys:
            self.logger.info("Quit by F4 shortcut")
            self.switch_to_application(app_id)
            self.send_keys("%{F4}")
        else:
            if app["dispatched"]:
                self.logger.info("Quit by app.Quit()")
                app["app"].Quit()
            else:
                if "process_id" in app and app["process_id"] > 0:
                    # pylint: disable=E1101
                    pid = app["process_id"]
                    if self.process_id_exists(pid):
                        self.logger.info("Quit by killing process id")
                        self.kill_process_by_pid(pid)
                    else:
                        self.logger.info("Process pid '%s' did not exist anymore", pid)
                else:
                    self.logger.info("Quit by app.kill()")
                    app["app"].kill()
        self._active_app_instance = -1

    def type_keys(self, keys: str) -> None:
        """Type keys into active window element.

        :param keys: list of keys to type

        Example:

        .. code-block:: robotframework

            Open Executable  notepad.exe  Untitled - Notepad
            Type Keys   My text

        """
        if self.dlg is None:
            raise ValueError("No dialog open")
        self.dlg.type_keys(keys)

    def type_into(self, locator: str, keys: str, empty_field: bool = False) -> None:
        """Type keys into element matched by given locator.

        :param locator: element locator
        :param keys:    list of keys to type
        :param empty_field: if field should be emptied before typing, default False

        Example:

        .. code-block:: robotframework

            Open Executable  calc.exe  Calculator
            Type Into        CalculatorResults  11
            Type Into        CalculatorResults  22  empty_field=True

        """
        elements, _ = self.find_element(locator)
        if elements and len(elements) == 1:
            ctrl = elements[0]["control"]
            if empty_field:
                ctrl.type_keys("{VK_LBUTTON down}{VK_CLEAR}{VK_LBUTTON up}")
            ctrl.type_keys(keys)
        else:
            raise ValueError(f"Could not find unique element for '{locator}'")

    def send_keys(self, keys: str) -> None:
        """Send keys into active windows.

        :param keys: list of keys to send

        Example:

        .. code-block:: robotframework

            Open Executable  calc.exe  Calculator
            Send Keys        2{+}3{=}

        """
        pywinauto.keyboard.send_keys(keys)

    def get_text(self, locator: str) -> dict:
        """Get text from element

        :param locator: element locator

        Example:

        .. code-block:: robotframework

            Open Using Run Dialog  calc     Calculator
            Type Into    CalculatorResults   11
            Type Into    CalculatorResults   55
            &{val}       Get Text   CalculatorResults

        """
        elements, _ = self.find_element(locator)
        element_text = {}
        if elements and len(elements) == 1:
            ctrl = elements[0]["control"]
            element_text["value"] = (
                str(ctrl.get_value()) if hasattr(ctrl, "get_value") else None
            )
            element_text["children_texts"] = (
                "".join(ctrl.children_texts())
                if hasattr(ctrl, "children_texts")
                else None
            )
            legacy = (
                ctrl.legacy_properties() if hasattr(ctrl, "legacy_properties") else None
            )
            element_text["legacy_value"] = str(legacy["Value"]) if legacy else None
            element_text["legacy_name"] = str(legacy["Name"]) if legacy else None
        return element_text

    def mouse_click(
        self,
        locator: str = None,
        x: int = 0,
        y: int = 0,
        off_x: int = 0,
        off_y: int = 0,
        image: str = None,
        method: str = "locator",
        ctype: str = "click",
        focus: str = "center",
        **kwargs,
    ) -> None:
        # pylint: disable=C0301
        """Mouse click `locator`, `coordinates`, or `image`

        When using method `locator`,`image` or `ocr` mouse is clicked by default at
        center coordinates.

        Click types are:

        - `click` normal left button mouse click
        - `double`
        - `right`

        :param locator: element locator on active window
        :param x: coordinate x on desktop
        :param y: coordinate y on desktop
        :param off_x: offset x (used for locator and image clicks)
        :param off_y: offset y (used for locator and image clicks)
        :param image: image to click on desktop
        :param method: one of the available methods to mouse click, default "locator"
        :param ctype: type of mouse click
        :param focus: default point for element click is 'center', can be set to 'topleft'
         to click top left corner of the element
        :param kwargs: these keyword arguments can be used to pass arguments
         to underlying `Images` library to finetune image template matching,
         for example. `tolerance=0.5` would adjust image tolerance for the image
         matching

        Example:

        .. code-block:: robotframework

            Mouse Click  method=coordinates  100   100
            Mouse Click  CalculatorResults
            Mouse Click  method=image  image=myimage.png  off_x=10  off_y=10  ctype=right
            Mouse Click  method=image  image=myimage.png  tolerance=0.8
            ${elements}  ${other}=     Find Element  class:Button
            FOR  ${element}  IN  @{elements}
                Run Keyword If   ${element}[visible]   Mouse Click  ${element}
            END
            Mouse Click  id:TrickyCheckbox  focus=topleft

        """  # noqa: E501
        self.logger.info("Mouse click: %s", locator)

        if method == "locator":
            target_element = None
            if isinstance(locator, dict):
                target_element = locator
            else:
                element, _ = self.find_element(locator)
                if element and len(element) == 1:
                    target_element = element[0]
                else:
                    raise ValueError(f"Could not find unique element for '{locator}'")
            if target_element is None:
                raise ValueError("Could not find unique element to click")
            if focus == "topleft":
                x, y, _, _ = self._get_element_coordinates(target_element)
                x += 2
                y += 2
            else:
                x, y = self.get_element_center(target_element)
            self.click_type(x + off_x, y + off_y, ctype)
        elif method == "coordinates":
            self.mouse_click_coords(x, y, ctype)
        elif method == "image":
            self.mouse_click_image(image, off_x, off_y, ctype, **kwargs)

    def mouse_click_image(
        self,
        template: str,
        off_x: int = 0,
        off_y: int = 0,
        ctype: str = "click",
        **kwargs,
    ) -> None:
        """Click at template image on desktop

        :param image: image to click on desktop
        :param off_x: horizontal offset from top left corner to click on
        :param off_y: vertical offset from top left corner to click on
        :param ctype: type of mouse click
        :param kwargs: these keyword arguments can be used to pass arguments
         to underlying `Images` library to finetune image template matching,
         for example. `tolerance=0.5` would adjust image tolerance for the image
         matching

        Example:

        .. code-block:: robotframework

            Mouse Click  image=myimage.png  off_x=10  off_y=10  ctype=right
            Mouse Click  image=myimage.png  tolerance=0.8

        """
        matches = Images().find_template_on_screen(template, limit=1, **kwargs)

        center_x = matches[0].center.x + int(off_x)
        center_y = matches[0].center.y + int(off_y)

        self.click_type(center_x, center_y, ctype)

    def mouse_click_coords(
        self, x: int, y: int, ctype: str = "click", delay_time: float = None
    ) -> None:
        """Click at coordinates on desktop

        :param x: horizontal coordinate on the windows to click
        :param y: vertical coordinate on the windows to click
        :param ctype: click type "click", "right" or "double", defaults to "click"
        :param delay: delay in seconds after, default is no delay

        Example:

        .. code-block:: robotframework

            Mouse Click Coords  x=450  y=100
            Mouse Click Coords  x=300  y=300  ctype=right
            Mouse Click Coords  x=450  y=100  delay=5.0

        """
        self.click_type(x, y, ctype)
        if delay_time:
            delay(delay_time)

    def get_element(
        self, locator: str, screenshot: bool = False, open_dialog: bool = True
    ) -> Any:
        """Get element by locator.

        :param locator: name of the locator
        :param screenshot: takes element screenshot if True, defaults to False
        :param open_dialog: True if dialog should be reopened, default to True
        :return: element if element was identified, else False

        Example:

        .. code-block:: robotframework

            ${element}  Get Element  CalculatorResults
            ${element}  Get Element  Result      screenshot=True

        """
        self.logger.info("Get element: %s", locator)
        if open_dialog:
            self.open_dialog(self.windowtitle)
        self.dlg.wait("exists enabled visible ready")

        matching_elements, _ = self.find_element(locator)

        if len(matching_elements) == 0:
            self.logger.info(
                "Locator '%s' not found in '%s'.\n",
                locator,
                self.windowtitle,
            )
        elif len(matching_elements) == 1:
            element = matching_elements[0]
            if screenshot:
                self.screenshot(f"locator_{locator}", element=element)
            for key in element.keys():
                self.logger.debug("%s=%s", key, element[key])
            return element
        else:
            # TODO: return more valuable information about what should
            # be matching element ?
            self.logger.info(
                "Locator '%s' matched multiple elements in '%s'. ",
                locator,
                self.windowtitle,
            )
        return False

    def get_element_rich_text(self, locator: str) -> Any:
        """Get value of element `rich text` attribute.

        :param locator: element locator
        :return: `rich_text` value if found, else False

        Example:

        .. code-block:: robotframework

            ${text}  Get Element Rich Text  CalculatorResults

        """
        element = self.get_element(locator)
        if element is not False and "rich_text" in element:
            return element["rich_text"]
        elif element is False:
            self.logger.info("Did not find element with locator: %s", locator)
            return False
        else:
            self.logger.info(
                "Element for locator %s does not have 'rich_text' attribute", locator
            )
            return False

    def get_element_rectangle(self, locator: str, as_dict: bool = False) -> Any:
        # pylint: disable=C0301
        """Get value of element `rectangle` attribute.

        :param locator: element locator
        :param as_dict: return values in a dictionary, default `False`
        :return: (left, top, right, bottom) values if found, else False

        Example:

        .. code-block:: robotframework

            ${left}  ${top}  ${right}  ${bottom}=  Get Element Rectangle  CalculatorResults
            &{coords}  Get Element Rectangle  CalculatorResults  as_dict=True
            Log  top=${coords.top} left=${coords.left}

        """  # noqa: E501
        rectangle = self._get_element_attribute(locator, "rectangle")
        left, top, right, bottom = self._get_element_coordinates(rectangle)
        if as_dict:
            return {"left": left, "top": top, "right": right, "bottom": bottom}
        return left, top, right, bottom

    def _get_element_attribute(self, locator: str, attribute: str) -> Any:
        element = self.get_element(locator)
        if element is not False and attribute in element:
            return element[attribute]
        elif element is False:
            self.logger.info("Did not find element with locator %s", locator)
            return False
        else:
            self.logger.info(
                "Element for locator %s does not have 'visible' attribute", locator
            )
            return False

    def is_element_visible(self, locator: str) -> bool:
        """Is element visible.

        :param locator: element locator
        :return: True if visible, else False

        Example:

        .. code-block:: robotframework

            ${res}=   Is Element Visible  CalculatorResults

        """
        visible = self._get_element_attribute(locator, "visible")
        return bool(visible)

    def is_element_enabled(self, locator: str) -> bool:
        """Is element enabled.

        :param locator: element locator
        :return: True if enabled, else False

        Example:

        .. code-block:: robotframework

            ${res}=   Is Element Enabled  CalculatorResults

        """
        enabled = self._get_element_attribute(locator, "enabled")
        return bool(enabled)

    def menu_select(self, menuitem: str) -> None:
        """Select item from menu

        :param menuitem: name of the menu item

        Example:

        .. code-block:: robotframework

            Open Using Run Dialog   notepad     Untitled - Notepad
            Menu Select             File->Print

        """
        self.logger.info("Menu select: %s", menuitem)
        if self.dlg is None:
            raise ValueError("No dialog open")
        try:
            self.dlg.menu_select(menuitem)
        except AttributeError as e:
            raise MenuItemNotFoundError(
                "Unable to access menu item '%s'" % menuitem
            ) from e

    def wait_for_element(
        self,
        locator: str,
        search_criteria: str = None,
        timeout: float = 30.0,
        interval: float = 2.0,
    ) -> Any:
        """Wait for element to appear into the window.

        Can return 1 or more elements matching locator, or raises
        `ElementNotFoundError` if element is not found within timeout.

        :param locator: name of the locator
        :param search_criteria: criteria by which element is matched
        :param timeout: defines how long to wait for element to appear,
         defaults to 30.0 seconds
        :param interval: how often to poll for element,
         defaults to 2.0 seconds (minimum is 0.5 seconds)

        Example:

        .. code-block:: robotframework

            @{elements}  Wait For Element  CalculatorResults
            @{elements}  Wait For Element  Results   timeout=10  interval=1.5

        """
        self.refresh_window()
        end_time = time.time() + float(timeout)
        interval = max([0.5, interval])
        elements = None
        while time.time() < end_time:
            elements, _ = self.find_element(locator, search_criteria)
            if len(elements) > 0:
                break
            if interval >= timeout:
                self.logger.info(
                    "Wait For Element: interval has been set longer than timeout - "
                    "executing one cycle."
                )
                break
            if time.time() >= end_time:
                break
            time.sleep(interval)
        if elements:
            return elements
        raise ElementNotFoundError

    def find_element(self, locator: str, search_criteria: str = None) -> Any:
        """Find element from window by locator and criteria.

        :param locator: name of the locator
        :param search_criteria: criteria by which element is matched
        :return: list of matching elements and locators that were found on the window

        Example:

        .. code-block:: robotframework

            @{elements}   Find Element   CalculatorResults
            Log Many  ${elements[0]}     # list of matching elements
            Log Many  ${elements[1]}     # list of all available locators

        """
        match_type, search_locators = self._parse_locator(locator, search_criteria)
        if self.elements is None:
            controls, elements = self.get_window_elements()
        else:
            controls = self.controls
            elements = self.elements

        matching_elements, locators = [], []

        for ctrl, element in zip(controls, elements):
            match_results = {}
            for criteria, search_locator in search_locators:
                match_results[criteria] = self.is_element_matching(
                    element, search_locator, criteria
                )
            if (match_type == "all" and all(match_results.values())) or (
                match_type == "any" and any(match_results.values())
            ):
                element["control"] = ctrl
                matching_elements.append(element)
        return matching_elements, locators

    def _determine_search_criteria(self, locator: str) -> Any:
        """Check search criteria from locator.

        Possible search criterias:
            - name
            - class / class_name
            - type / control_type
            - id / automation_id
            - partial name (wildcard search for 'name' attribute)
            - any (if none was defined)

        :param locator: name of the locator
        :return: criteria and locator
        """
        if locator.startswith("name:"):
            search_criteria = "name"
            _, locator = locator.split(":", 1)
        elif locator.startswith(("class_name:", "class:")):
            search_criteria = "class_name"
            _, locator = locator.split(":", 1)
        elif locator.startswith(("control_type:", "type:")):
            search_criteria = "control_type"
            _, locator = locator.split(":", 1)
        elif locator.startswith(("automation_id:", "id:")):
            search_criteria = "automation_id"
            _, locator = locator.split(":", 1)
        elif locator.startswith("partial name:"):
            search_criteria = "partial name"
            _, locator = locator.split(":", 1)
        elif locator.startswith("regexp:"):
            search_criteria = "regexp"
            _, locator = locator.split(":", 1)
        else:
            search_criteria = "any"

        return search_criteria, locator

    # TODO: supporting multiple search criterias at same time to identify ONE element
    def _is_element_matching(
        self, itemdict: dict, locator: str, criteria: str, wildcard: bool = False
    ) -> bool:
        if criteria == "regexp":
            name_search = re.search(locator, itemdict["name"])
            class_search = re.search(locator, itemdict["class_name"])
            type_search = re.search(locator, itemdict["control_type"])
            id_search = re.search(locator, itemdict["automation_id"])
            return name_search or class_search or type_search or id_search
        elif criteria != "any" and criteria in itemdict:
            if (wildcard and locator in itemdict[criteria]) or (
                locator == itemdict[criteria]
            ):
                return True
        elif criteria == "any":
            name_search = self.is_element_matching(itemdict, locator, "name")
            class_search = self.is_element_matching(itemdict, locator, "class_name")
            type_search = self.is_element_matching(itemdict, locator, "control_type")
            id_search = self.is_element_matching(itemdict, locator, "automation_id")
            if name_search or class_search or type_search or id_search:
                return True
        elif criteria == "partial name":
            return self.is_element_matching(itemdict, locator, "name", True)
        return False

    # TODO: supporting multiple search criterias at same time to identify ONE element
    def is_element_matching(
        self, itemdict: dict, locator: str, criteria: str, wildcard: bool = False
    ) -> bool:
        """Is element matching. Check if locator is found in `any` field
        or `criteria` field in the window items.

        :param itemDict: dictionary of element items
        :param locator: name of the locator
        :param criteria: criteria on which to match element
        :param wildcard: whether to do reg exp match or not, default False
        :return: True if element is matching locator and criteria, False if not
        """
        return self._is_element_matching(itemdict, locator, criteria, wildcard)

    def get_dialog_rectangle(self, ctrl: Any = None, as_dict: bool = False) -> Any:
        """Get dialog rectangle coordinates

        If `ctrl` is None then get coordinates from `dialog`

        :param ctrl: name of the window control object, defaults to None
        :return: coordinates: left, top, right, bottom

        Example:

        .. code-block:: robotframework

            ${left}  ${top}  ${right}  ${bottom}=  Get Dialog Rectangle
            &{coords}  Get Dialog Rectangle  as_dict=True
            Log  top=${coords.top} left=${coords.left}

        """
        if ctrl:
            rect = ctrl.element_info.rectangle
        elif self.dlg:
            rect = self.dlg.element_info.rectangle
        else:
            raise ValueError("No dialog open")

        if as_dict:
            return {
                "left": rect.left,
                "top": rect.top,
                "right": rect.right,
                "bottom": rect.bottom,
            }
        else:
            return rect.left, rect.top, rect.right, rect.bottom

    def get_element_center(self, element: dict) -> Any:
        """Get element center coordinates

        :param element: dictionary of element items
        :return: coordinates, x and y

        Example:

        .. code-block:: robotframework

            @{element}   Find Element  CalculatorResults
            ${x}  ${y}=  Get Element Center  ${elements[0][0]}

        """
        return self.calculate_rectangle_center(element["rectangle"])

    def click_type(
        self, x: int = None, y: int = None, click_type: str = "click"
    ) -> None:
        """Mouse click on coordinates x and y.

        Default click type is `click` meaning `left`

        :param x: horizontal coordinate for click, defaults to None
        :param y: vertical coordinate for click, defaults to None
        :param click_type: "click", "right" or "double", defaults to "click"
        :raises ValueError: if coordinates are not valid

        Example:

        .. code-block:: robotframework

            Click Type  x=450  y=100
            Click Type  x=450  y=100  click_type=right
            Click Type  x=450  y=100  click_type=double

        """
        self.logger.info("Click type '%s' at (%s, %s)", click_type, x, y)
        if (x is None and y is None) or (x < 0 or y < 0):
            raise ValueError(f"Can't click on given coordinates: ({x}, {y})")
        if click_type == "click":
            pywinauto.mouse.click(coords=(x, y))
        elif click_type == "double":
            pywinauto.mouse.double_click(coords=(x, y))
        elif click_type == "right":
            pywinauto.mouse.right_click(coords=(x, y))

    def get_window_elements(
        self,
        screenshot: bool = False,
        element_json: bool = False,
        outline: bool = False,
    ) -> Any:
        # pylint: disable=C0301
        """Get element information about all window dialog controls
        and their descendants.

        :param screenshot: save element screenshot if True, defaults to False
        :param element_json: save element json if True, defaults to False
        :param outline: highlight elements if True, defaults to False
        :return: all controls and all elements

        Example:

        .. code-block:: robotframework

            @{elements}   Get Window Elements
            Log Many      ${elements[0]}     # list of all available locators
            Log Many      ${elements[1]}     # list of matching elements
            @{elements}   Get Window Elements  screenshot=True  element_json=True  outline=True

        """  # noqa: E501
        ctrls = self._get_all_window_controls()
        elements, controls = [], []
        for _, ctrl in enumerate(ctrls):
            try:
                if not hasattr(ctrl, "element_info"):
                    continue
            except COMError as ce:
                self.logger.info("Got COM error: %s", str(ce))
                continue

            filename = clean_filename(
                f"locator_{self.windowtitle}_ctrl_{ctrl.element_info.name}"
            )

            if screenshot and len(ctrl.element_info.name) > 0:
                self.screenshot(filename, ctrl=ctrl, overwrite=True)
            if outline:
                ctrl.draw_outline(colour="red", thickness=4)
                delay(0.2)
                ctrl.draw_outline(colour=0x000000, thickness=4)

            element = self._parse_element_attributes(element=ctrl)
            if element_json:
                write_element_info_as_json(element, filename)

            controls.append(ctrl)
            elements.append(element)

        if element_json:
            write_element_info_as_json(
                elements, clean_filename(f"locator_{self.windowtitle}_all_elements")
            )

        return controls, elements

    def _get_all_window_controls(self):
        if self.dlg is None:
            raise ValueError("No dialog open")

        ctrls = [self.dlg]
        try:
            if hasattr(self.dlg, "descendants"):
                ctrls += self.dlg.descendants()
        except COMError as ce:
            self.logger.info("Got COM error: %s", str(ce))
        return ctrls

    def _get_element_coordinates(self, element: Any) -> Any:
        """Get element coordinates from pywinauto object.

        :param rectangle: item containing rectangle information
        :return: coordinates: left, top, right, bottom
        """
        left = 0
        top = 0
        right = 0
        bottom = 0
        if isinstance(element, pywinauto.win32structures.RECT):
            left = element.left
            top = element.top
            right = element.right
            bottom = element.bottom
        elif isinstance(element, dict) and "rectangle" not in element.keys():
            left = element.left
            top = element.top
            right = element.right
            bottom = element.bottom
        else:
            if isinstance(element, dict) and "rectangle" in element.keys():
                rectangle = element["rectangle"]
            else:
                rectangle = element
            left, top, right, bottom = map(
                int,
                re.match(
                    r"\(L([-]?\d+).*T([-]?\d+).*R([-]?\d+).*B([-]?\d+)\)",
                    str(rectangle),
                ).groups(),
            )
        return left, top, right, bottom

    def screenshot(
        self,
        filename: str,
        element: dict = None,
        ctrl: Any = None,
        desktop: bool = False,
        overwrite: bool = False,
    ) -> None:
        """Save screenshot into filename.

        :param filename: name of the file
        :param element: take element screenshot, defaults to None
        :param ctrl: take control screenshot, defaults to None
        :param desktop: take desktop screenshot if True, defaults to False
        :param overwrite: file is overwritten if True, defaults to False

        Example:

        .. code-block:: robotframework

            @{element}   Find Element  CalculatorResults
            Screenshot   element.png   ${elements[0][0]}
            Screenshot   desktop.png   desktop=True
            Screenshot   desktop.png   desktop=True  overwrite=True

        """
        if desktop:
            region = None
        elif element:
            region = self._get_element_coordinates(element["rectangle"])
        elif ctrl:
            region = self.get_dialog_rectangle(ctrl)
        else:
            region = self.get_dialog_rectangle()

        if region:
            left, top, right, bottom = region
            if right - left == 0 or bottom - top == 0:
                self.logger.info(
                    "Unable to take screenshot, because regions was: %s", region
                )
                return
        try:
            output_dir = BuiltIn().get_variable_value("${OUTPUT_DIR}")
        except (ModuleNotFoundError, RobotNotRunningError):
            output_dir = Path.cwd()

        filename = Path(output_dir, "images", clean_filename(filename))
        os.makedirs(filename.parent, exist_ok=overwrite)
        Images().take_screenshot(filename=filename, region=region)

        self.logger.info("Saved screenshot as '%s'", filename)

    def _parse_element_attributes(self, element: dict) -> dict:
        """Return filtered element dictionary for an element.

        :param element: should contain `element_info` attribute
        :return: dictionary containing element attributes
        """
        if element is None and "element_info" not in element:
            self.logger.warning(
                "%s is none or does not have element_info attribute", element
            )
            return None

        attributes_to_remove = [
            # "automation_id",
            "children",
            # "class_name",
            # "control_id",
            # "control_type",
            "descendants",
            "dump_window",
            "element",
            # "enabled",
            "filter_with_depth",
            "framework_id",
            "from_point",
            # "handle",
            "has_depth",
            "iter_children",
            "iter_descendants",
            # "name",
            "parent",
            # "process_id",
            # "rectangle",
            # "rich_text",
            # "runtime_id",
            "set_cache_strategy",
            "top_from_point",
            # "visible",
        ]

        element_dict = {}
        element_info = element.element_info
        element_attributes = [a for a in dir(element_info) if not a.startswith("_")]

        for attr in element_attributes:
            try:
                attr_value = getattr(element_info, attr)
                element_dict[attr] = (
                    attr_value() if callable(attr_value) else str(attr_value)
                )
            except TypeError:
                pass
            except COMError as ce:
                self.logger.info("Got COM error: %s", str(ce))

        for attr in attributes_to_remove:
            element_dict.pop(attr, None)

        element_dict["legacy"] = (
            element.legacy_properties()
            if hasattr(element, "legacy_properties")
            else None
        )
        element_dict["object"] = element
        return element_dict

    def put_system_to_sleep(self) -> None:
        """Put Windows into sleep mode

        Example:

        .. code-block:: robotframework

            Put System To Sleep

        """
        access = win32security.TOKEN_ADJUST_PRIVILEGES | win32security.TOKEN_QUERY
        htoken = win32security.OpenProcessToken(win32api.GetCurrentProcess(), access)
        if htoken:
            priv_id = win32security.LookupPrivilegeValue(
                None, win32security.SE_SHUTDOWN_NAME
            )
            win32security.AdjustTokenPrivileges(
                htoken, 0, [(priv_id, win32security.SE_PRIVILEGE_ENABLED)]
            )
            ctypes.windll.powrprof.SetSuspendState(False, True, True)
            win32api.CloseHandle(htoken)

    def lock_screen(self) -> None:
        """Put windows into lock mode

        Example:

        .. code-block:: robotframework

            Lock Screen
        """
        ctypes.windll.User32.LockWorkStation()

    def log_in(self, username: str, password: str, domain: str = ".") -> str:
        """Log into Windows `domain` with `username` and `password`.

        :param username: name of the user
        :param password: password of the user
        :param domain: windows domain for the user, defaults to "."
        :return: handle

        Example:

        .. code-block:: robotframework

            Log In  username=myname  password=mypassword  domain=company
        """
        return win32security.LogonUser(
            username,
            domain,
            password,
            win32con.LOGON32_LOGON_INTERACTIVE,
            win32con.LOGON32_PROVIDER_DEFAULT,
        )

    def _validate_target(self, target: dict, target_locator: str) -> Any:
        target_x = target_y = 0
        if target_locator is not None:
            self.switch_to_application(target["id"])
            target_elements, _ = self.find_element(target_locator)
            if len(target_elements) == 0:
                raise ValueError(
                    ("Target element was not found by locator '%s'", target_locator)
                )
            elif len(target_elements) > 1:
                raise ValueError(
                    (
                        "Target element matched more than 1 element (%d) "
                        "by locator '%s'",
                        len(target_elements),
                        target_locator,
                    )
                )
            target_x, target_y = self.calculate_rectangle_center(
                target_elements[0]["rectangle"]
            )
        else:
            target_x, target_y = self.calculate_rectangle_center(
                target["dlg"].rectangle()
            )
        return target_x, target_y

    def _select_elements_for_drag(self, src: dict, src_locator: str) -> Any:
        self.switch_to_application(src["id"])
        source_elements, _ = self.find_element(src_locator)
        if len(source_elements) == 0:
            raise ValueError(
                ("Source elements where not found by locator '%s'", src_locator)
            )
        selections = []
        source_min_left = 99999
        source_max_right = -1
        source_min_top = 99999
        source_max_bottom = -1
        for elem in source_elements:
            left, top, right, bottom = self._get_element_coordinates(elem["rectangle"])
            if left < source_min_left:
                source_min_left = left
            if right > source_max_right:
                source_max_right = right
            if top < source_min_top:
                source_min_top = top
            if bottom > source_max_bottom:
                source_max_bottom = bottom
            mid_x = int((right - left) / 2) + left
            mid_y = int((bottom - top) / 2) + top
            selections.append((mid_x, mid_y))
        source_x = int((source_max_right - source_min_left) / 2) + source_min_left
        source_y = int((source_max_bottom - source_min_top) / 2) + source_min_top
        return selections, source_x, source_y

    def drag_and_drop(
        self,
        src: Any,
        target: Any,
        src_locator: str,
        target_locator: str = None,
        handle_ctrl_key: bool = False,
        drop_delay: float = 2.0,
    ) -> None:
        # pylint: disable=C0301
        """Drag elements from source and drop them on target.

        Please note that if CTRL is not pressed down during drag and drop then
        operation is MOVE operation, on CTRL down the operation is COPY operation.

        There will be also overwrite notification if dropping over existing files.

        :param src: application object or instance id
        :param target: application object or instance id
        :param src_locator: elements to move
        :param handle_ctrl_key: True if keyword should press CTRL down dragging
        :param drop_delay: how many seconds to wait until releasing mouse drop,
         default 2.0
        :raises ValueError: on validation errors

        Example:

        .. code-block:: robotframework

            ${app1}=        Open Using Run Dialog    explorer.exe{VK_SPACE}C:\\workfiles\\movethese   movethese
            ${app2}=        Open Using Run Dialog    wordpad.exe   Document - WordPad
            Drag And Drop   ${app1}   ${app2}   regexp:testfile_\\d.txt  name:Rich Text Window   handle_ctrl_key=${True}
            Drag And Drop   ${app1}   ${app1}   regexp:testfile_\\d.txt  name:subdir  handle_ctrl_key=${True}

        """  # noqa : E501
        if isinstance(src, int):
            src = self.get_app(src)
        if isinstance(target, int):
            target = self.get_app(target)

        single_application = src["app"] == target["app"]
        selections, source_x, source_y = self._select_elements_for_drag(
            src, src_locator
        )
        target_x, target_y = self._validate_target(target, target_locator)

        self.logger.info(
            "Dragging %d elements from (%d,%d) to (%d,%d)",
            len(selections),
            source_x,
            source_y,
            target_x,
            target_y,
        )

        try:
            if handle_ctrl_key:
                self.send_keys("{VK_LCONTROL down}")
                delay(0.2)

            # Select elements by mouse clicking
            if not single_application:
                self.restore_dialog(src["windowtitle"])
            for idx, selection in enumerate(selections):
                self.logger.debug("Selecting item %d by mouse_click", idx)
                # pywinauto.mouse.click(coords=(selection[0]+5, selection[1]+5))
                self.mouse_click_coords(selection[0] + 5, selection[1] + 5)

            # Start drag from the last item
            pywinauto.mouse.press(coords=(source_x, source_y))
            delay(0.5)
            if not single_application:
                self.restore_dialog(target["windowtitle"])
            pywinauto.mouse.move(coords=(target_x, target_y))

            self.logger.debug("Cursor position: %s", win32api.GetCursorPos())
            delay(drop_delay)
            self.mouse_click_coords(target_x, target_y)
            pywinauto.mouse.click(coords=(target_x, target_y))

            # if action_required:
            self.send_keys("{ENTER}")
            if handle_ctrl_key:
                self.send_keys("{VK_LCONTROL up}")
                delay(0.5)
            # Deselect elements by mouse clicking
            for selection in selections:
                self.logger.debug("Deselecting item by mouse_click")
                self.mouse_click_coords(selection[0] + 5, selection[1] + 5)
        finally:
            self.send_keys("{VK_LCONTROL up}")

    def calculate_rectangle_center(self, rectangle: Any) -> Any:
        """Calculate x and y center coordinates from rectangle.

        :param rectangle: element rectangle coordinates
        :return: x and y coordinates of rectangle center

        Example:

        .. code-block:: robotframework

            Open Using Run Dialog   calc  Calculator
            &{rect}=        Get Element Rectangle    CalculatorResults
            ${x}  ${y}=     Calculate Rectangle Center   ${rect}
        """
        left, top, right, bottom = self._get_element_coordinates(rectangle)
        x = int((right - left) / 2) + left
        y = int((bottom - top) / 2) + top
        return x, y

    def get_window_list(self):
        """Get list of open windows

        Window dictionaries contain:

        - automation_id
        - control_id
        - title
        - pid
        - handle
        - is_active
        - keyboard_focus
        - rectangle

        :return: list of window dictionaries

        Example:

        .. code-block:: robotframework

            @{windows}    Get Window List
            FOR  ${window}  IN  @{windows}
                Log Many  ${window}
            END
        """
        windows = pywinauto.Desktop(backend=self._backend).windows()
        window_list = []
        for w in windows:
            try:
                left, top, right, bottom = self._get_element_coordinates(w.rectangle())
                window_list.append(
                    {
                        "automation_id": w.automation_id(),
                        "control_id": w.control_id(),
                        "title": w.window_text(),
                        "pid": w.process_id(),
                        "handle": w.handle,
                        "is_active": w.is_active(),
                        "keyboard_focus": w.has_keyboard_focus(),
                        "rectangle": [left, top, right, bottom],
                    }
                )
            except Exception as e:  # pylint: disable=broad-except
                self.logger.debug(str(e))
        return window_list

    def refresh_window(self):
        """Get controls and elements for current windows.

        Should be called always when window content changes on
        Windows desktop.

        :return: controls (list) and elements (list)
        """
        self.logger.debug("Refresh window")
        controls, elements = self.get_window_elements()
        self.elements = elements
        self.controls = controls
        return controls, elements

    def _parse_locator(self, locator: str, search_criteria: str):
        regex = rf"({':|'.join(WINDOWS_LOCATOR_STRATEGIES.keys())}:|or|and)('{{1}}(.+)'{{1}}|(\S+))?"  # noqa: E501
        parts = re.finditer(regex, locator, re.IGNORECASE)

        locators = []
        match_type = "all"

        for part in parts:
            groups = part.groups()
            if groups[0].lower() == "or":
                match_type = "any"
            elif groups[0].lower() == "and":
                pass
            else:
                strategy, _ = groups[0].split(":")
                value = groups[2] if groups[2] else groups[3]
                locators.append([WINDOWS_LOCATOR_STRATEGIES[strategy], value])

        # Add some strategies if there aren't other valid strategies
        if not locators:
            match_type = "any"
            locators.append(["name", locator])
            locators.append(["automation_id", locator])
            locators.append([search_criteria, locator])
        return match_type, locators
