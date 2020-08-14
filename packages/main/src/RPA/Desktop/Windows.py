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


def write_element_info_as_json(
    elements: Any, filename: str, path: str = "output/json"
) -> None:
    """Write list of elements into json file

    :param elements: list of elements to write
    :param filename: output file name
    :param path: output directory, defaults to "output/json"
    """
    elements = elements if isinstance(elements, list) else [elements]
    with open(Path(f"{path}/{filename}.json"), "w") as outfile:
        json.dump(elements, outfile, indent=4, sort_keys=True)


class Windows(OperatingSystem):
    """Windows methods extending OperatingSystem class.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self, backend: str = "uia") -> None:
        OperatingSystem.__init__(self)
        self._apps = {}
        self._app_instance_id = 0
        self._active_app_instance = -1
        # uia or win32
        self._backend = backend
        self.app = None
        self.dlg = None
        self.windowtitle = None
        self.logger = logging.getLogger(__name__)
        self.clipboard = Clipboard()

    def __del__(self):
        try:
            # TODO: Do this as RF listener instead of __del__?
            self.clipboard.clear_clipboard()
        except RuntimeError as err:
            self.logger.debug("Failed to clear clipboard: %s", err)

    # TODO. add possibility to define alias for application
    def _add_app_instance(
        self, app: Any = None, dialog: bool = True, params: dict = None,
    ) -> int:
        params = params or {}
        self._app_instance_id += 1

        if app:
            self.app = app

        default_params = {
            "app": app,
            "id": self._app_instance_id,
            "dispatched": False,
        }

        self._apps[self._app_instance_id] = {**default_params, **params}
        self._active_app_instance = self._app_instance_id

        if dialog:
            self.open_dialog(self._apps[self._app_instance_id].get("windowtitle", None))

        self.logger.debug(self._apps)
        return self._active_app_instance

    def switch_to_application(self, app_id: int) -> None:
        """Switch to application by id.

        :param app_id: application's id
        :raises ValueError: if application is not found by given id
        """
        if app_id and app_id in self._apps.keys():
            app = self.get_app(app_id)
            self._active_app_instance = app_id
            self.app = app["app"]
            self.open_dialog(app["windowtitle"])
            delay(0.5)
            self.restore_dialog(app["windowtitle"])
        else:
            raise ValueError(f"No open application with id '{app_id}'")

    def get_app(self, app_id: int = None) -> Any:
        """Get application object by id

        By default returns active_application application object.

        :param app_id: id of the application to get, defaults to None
        :return: application object
        """
        if app_id is None and self._active_app_instance != -1:
            return self._apps[self._active_app_instance]
        else:
            return self._apps[app_id]

    def open_application(self, application: str) -> int:
        """Open application by dispatch method

        :param application: name of the application as `str`
        :return: application instance id
        """
        self.logger.info("Open application: %s", application)
        app = win32com.client.gencache.EnsureDispatch(f"{application}.Application")
        app.Visible = True
        # show eg. file overwrite warning or not
        if hasattr(self.app, "DisplayAlerts"):
            app.DisplayAlerts = False
        return self._add_app_instance(app, dialog=False, params={"dispatched": True})

    # TODO. How to manage app launched by open_file
    def open_file(self, filename: str) -> bool:
        """Open associated application when opening file

        :param filename: path to file
        :return: True if application is opened, False if not
        """
        self.logger.info("Open file: %s", filename)
        if platform.system() == "Windows":
            # pylint: disable=no-member
            os.startfile(filename)
            return True
        elif platform.system() == "Darwin":
            subprocess.call(["open", filename])
            return True
        else:
            subprocess.call(["xdg-open", filename])
            return True

        return False

    def open_executable(
        self,
        executable: str,
        windowtitle: str,
        backend: str = "uia",
        work_dir: str = None,
    ) -> int:
        """Open Windows executable. Window title name is required
        to get handle on the application.

        :param executable: name of the executable
        :param windowtitle: name of the window
        :param work_dir: path to working directory, default None
        :return: application instance id
        """
        self.logger.info("Opening executable: %s - window: %s", executable, windowtitle)
        params = {"executable": executable, "windowtitle": windowtitle}
        self.windowtitle = windowtitle
        app = pywinauto.Application(backend=backend).start(
            cmd_line=executable, work_dir=work_dir
        )
        return self._add_app_instance(app, dialog=True, params=params)

    def open_using_run_dialog(self, executable: str, windowtitle: str) -> int:
        """Open application using Windows run dialog.
        Window title name is required to get handle on the application.

        :param executable: name of the executable
        :param windowtitle: name of the window
        :return: application instance id
        """
        self.send_keys("{VK_LWIN down}r{VK_LWIN up}")
        delay(1)

        self.send_keys_to_input(executable)

        params = {"windowtitle": windowtitle, "executable": executable}
        return self._add_app_instance(params=params, dialog=True)

    def open_from_search(self, executable: str, windowtitle: str) -> int:
        """Open application using Windows search dialog.
        Window title name is required to get handle on the application.

        :param executable: name of the executable
        :param windowtitle: name of the window
        :return: application instance id
        """
        self.logger.info("Run from start menu: %s", executable)
        self.send_keys("{LWIN}")
        delay(1)

        self.send_keys_to_input(executable)

        params = {"windowtitle": windowtitle, "executable": executable}
        return self._add_app_instance(params=params, dialog=True)

    def send_keys_to_input(
        self,
        keys_to_type: str,
        with_enter: bool = True,
        send_delay: float = 0.5,
        enter_delay: float = 1.5,
    ) -> None:
        """Send keys to windows and add ENTER if `with_enter` is True

        At the end of send_keys there is by default 1.0 second delay.
        At the end of ENTER there is by default 3.5 second delay.

        :param keys_to_type: keys to type into Windows
        :param with_enter: send ENTER if `with_enter` is True
        :param send_delay: delay after send_keys
        :param enter_delay: delay after ENTER
        """
        # Set keyboard layout for Windows platform
        if platform.system() == "Windows":
            win32api.LoadKeyboardLayout("00000409", 1)

        self.send_keys(keys_to_type)
        delay(send_delay)
        if with_enter:
            self.send_keys("{ENTER}")
            delay(enter_delay)

    def minimize_dialog(self, windowtitle: str) -> None:
        """Minimize window by its title

        :param windowtitle: name of the window
        """
        self.logger.info("Minimize dialog: %s", windowtitle)
        self.dlg = pywinauto.Desktop(backend="uia")[windowtitle]
        self.dlg.minimize()

    def restore_dialog(self, windowtitle: str) -> None:
        """Restore window by its title

        :param windowtitle: name of the window
        """
        self.logger.info("Restore dialog: %s", windowtitle)
        self.dlg = pywinauto.Desktop(backend="uia")[windowtitle]
        self.dlg.restore()

    def open_dialog(
        self, windowtitle: str = None, highlight: bool = False, timeout: int = 10
    ) -> Any:
        """Open window by its title.

        :param windowtitle: name of the window, defaults to active window if None
        :param highlight: draw outline for window if True, defaults to False
        :param timeout: time to wait for dialog to appear
        """
        self.logger.info("Open dialog: '%s', '%s'", windowtitle, highlight)

        if windowtitle:
            self.windowtitle = windowtitle

        app_instance = None
        end_time = time.time() + float(timeout)
        while time.time() < end_time and app_instance is None:
            for window in self.get_window_list():
                if window["title"] == self.windowtitle:
                    app_instance = self.connect_by_handle(window["handle"])
            time.sleep(0.1)

        if self.dlg is None:
            raise ValueError("No window with title '{}'".format(self.windowtitle))

        if highlight:
            self.dlg.draw_outline()

        return app_instance

    def connect_by_pid(self, app_pid: str, windowtitle: str = None) -> Any:
        """Connect to application by its pid

        :param app_pid: process id of the application
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

    def connect_by_handle(self, handle: str, windowtitle: str = None) -> Any:
        """Connect to application by its handle

        :param handle: handle of the application
        """
        self.logger.info("Connect to application handle: %s", handle)
        app = pywinauto.Application(backend="uia").connect(
            handle=handle, visible_only=False
        )
        self.dlg = app.window(handle=handle)
        self.dlg.restore()
        params = None
        if windowtitle is not None:
            params = {}
            params["windowtitle"] = windowtitle
        app_instance = self._add_app_instance(app=app, params=params, dialog=False)
        return app_instance

    def close_all_applications(self) -> None:
        """Close all applications
        """
        self.logger.info("Closing all applications")
        application_ids = self._apps.keys()
        self.logger.debug("Applications in memory: %d", len(self._apps))
        for aid in application_ids:
            self.logger.debug("Closing application ID: %s", aid)
            self.quit_application(aid)

    def quit_application(self, app_id: str = None, send_keys: bool = False) -> None:
        """Quit an application by application id or
        active application if `app_id` is None.

        :param app_id: application_id, defaults to None
        """
        app = self.get_app(app_id)
        app_id_to_quit = app["id"]
        self.logger.info("Quit application: %s", app_id_to_quit)
        if send_keys:
            self.switch_to_application(app_id)
            self.send_keys("%{F4}")
        else:
            if app["dispatched"]:
                app["app"].Quit()
            else:
                app["app"].kill()
        self._apps[app_id_to_quit]["app"] = None
        self._active_app_instance = -1

    def type_keys(self, keys: str) -> None:
        """Type keys into active window element.

        :param keys: list of keys to type
        """
        self.logger.info("Type keys: %s", keys)
        if self.dlg is None:
            raise ValueError("No dialog open")
        self.dlg.type_keys(keys)

    def type_into(self, locator: str, keys: str) -> None:
        """Type keys into element matched by given locator.

        :param locator: element locator
        :param keys:    list of keys to type
        """
        elements, _ = self.find_element(locator)
        if elements and len(elements) == 1:
            ctrl = elements[0]["control"]
            ctrl.type_keys(keys)
        else:
            raise ValueError(f"Could not find unique element for '{locator}'")

    def send_keys(self, keys: str) -> None:
        """Send keys into active windows.

        :param keys: list of keys to send
        """
        self.logger.info("Send keys: %s", keys)
        pywinauto.keyboard.send_keys(keys)

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
    ) -> None:
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
        """
        self.logger.info("Mouse click: %s", locator)

        if method == "locator":
            element, _ = self.find_element(locator)
            if element and len(element) == 1:
                x, y = self.get_element_center(element[0])
                self.click_type(x + off_x, y + off_y, ctype)
            else:
                raise ValueError(f"Could not find unique element for '{locator}'")
        elif method == "coordinates":
            self.mouse_click_coords(x, y, ctype)
        elif method == "image":
            self.mouse_click_image(image, off_x, off_y, ctype)

    def mouse_click_image(
        self, template: str, off_x: int = 0, off_y: int = 0, ctype: str = "click"
    ) -> None:
        """Click at template image on desktop

        :param image: [description]
        :param off_x: [description], defaults to 0
        :param off_y: [description], defaults to 0
        :param ctype: [description], defaults to "click"
        """
        matches = Images().find_template_on_screen(template, limit=1)

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
        """
        self.click_type(x, y, ctype)
        if delay_time:
            delay(delay_time)

    def get_element(self, locator: str, screenshot: bool = False) -> Any:
        """Get element by locator.

        :param locator: name of the locator
        :param screenshot: takes element screenshot if True, defaults to False
        :return: element if element was identified, else False
        """
        self.logger.info("Get element: %s", locator)
        # self.connect_by_handle(self.dlg.handle)
        # TODO. move dlg wait into "open_dialog" ?
        self.open_dialog(self.windowtitle)
        self.dlg.wait("exists enabled visible ready")

        search_criteria, locator = self._determine_search_criteria(locator)
        matching_elements, locators = self.find_element(locator, search_criteria)

        locators = sorted(set(locators))
        if locator in locators:
            locators.remove(locator)
        locators_string = "\n\t- ".join(locators)

        if len(matching_elements) == 0:
            self.logger.info(
                "Locator '%s' using search criteria '%s' not found in '%s'.\n"
                "Maybe one of these would be better?\n%s\n",
                locator,
                search_criteria,
                self.windowtitle,
                locators_string,
            )
        elif len(matching_elements) == 1:
            element = matching_elements[0]
            if screenshot:
                self.screenshot(f"locator_{locator}", element=element)
            for key in element.keys():
                self.logger.debug("%s=%s", key, element[key])
            return element
        else:
            # TODO. return more valuable information about what should
            # be matching element ?
            self.logger.info(
                "Locator '%s' matched multiple elements in '%s'. "
                "Maybe one of these would be better?\n%s\n",
                locator,
                self.windowtitle,
                locators_string,
            )
        return False

    def get_element_rich_text(self, locator: str) -> Any:
        """Get value of element `rich text` attribute.

        :param locator: element locator
        :return: `rich_text` value if found, else False
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

    def get_element_rectangle(self, locator: str) -> Any:
        """Get value of element `rectangle` attribute.

        :param locator: element locator
        :return: (left, top, right, bottom) values if found, else False
        """
        rectangle = self._get_element_attribute(locator, "rectangle")
        return self._get_element_coordinates(rectangle)

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
        """
        visible = self._get_element_attribute(locator, "visible")
        return bool(visible)

    def is_element_enabled(self, locator: str) -> bool:
        """Is element enabled.

        :param locator: element locator
        :return: True if enabled, else False
        """
        enabled = self._get_element_attribute(locator, "enabled")
        return bool(enabled)

    def menu_select(self, menuitem: str) -> None:
        """Select item from menu

        :param menuitem: name of the menu item
        """
        self.logger.info("Menu select: %s", menuitem)
        app = self.get_app()
        app["dlg"].menu_select(menuitem)
        # self.logger.warning(f"Window '{app['windowtitle']}'
        # does not have menu_select")

    def find_element(self, locator: str, search_criteria: str = None) -> Any:
        """Find element from window by locator and criteria.

        :param locator: name of locator
        :param search_criteria: criteria by which element is matched
        :return: list of matching elements and locators that were found on the window
        """
        search_locator = locator
        if search_criteria is None:
            search_criteria, search_locator = self._determine_search_criteria(locator)

        controls, elements = self.get_window_elements()
        self.logger.info(
            "Find element: (locator: %s, criteria: %s)", locator, search_criteria,
        )

        matching_elements, locators = [], []
        for ctrl, element in zip(controls, elements):
            if self.is_element_matching(element, search_locator, search_criteria):
                element["control"] = ctrl
                matching_elements.append(element)
            if search_criteria == "any" and "name" in element:
                locators.append(element["name"])
            elif search_criteria and search_criteria in element:
                locators.append(element[search_criteria])

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

    # TODO. supporting multiple search criterias at same time to identify ONE element
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

    def get_dialog_rectangle(self, ctrl: Any = None) -> Any:
        """Get element rectangle coordinates

        If `ctrl` is None then get coordinates from `dialog`
        :param ctrl: name of the window control object, defaults to None
        :return: coordinates: left, top, right, bottom
        """
        if ctrl:
            rect = ctrl.element_info.rectangle
        elif self.dlg:
            rect = self.dlg.element_info.rectangle
        else:
            raise ValueError("No dialog open")

        return rect.left, rect.top, rect.right, rect.bottom

    def get_element_center(self, element: dict) -> Any:
        """Get element center coordinates

        :param element: dictionary of element items
        :return: coordinates, x and y
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
        """Get element information about all window dialog controls
        and their descendants.

        :param screenshot: save element screenshot if True, defaults to False
        :param element_json: save element json if True, defaults to False
        :param outline: highlight elements if True, defaults to False
        :return: all controls and all elements
        """
        if self.dlg is None:
            raise ValueError("No dialog open")

        ctrls = [self.dlg]
        if hasattr(self.dlg, "descendants"):
            ctrls += self.dlg.descendants()

        elements, controls = [], []
        for _, ctrl in enumerate(ctrls):
            if not hasattr(ctrl, "element_info"):
                continue

            filename = clean_filename(
                f"locator_{self.windowtitle}_ctrl_{ctrl.element_info.name}"
            )

            if screenshot and len(ctrl.element_info.name) > 0:
                self.screenshot(filename, ctrl=ctrl)
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

    def _get_element_coordinates(self, rectangle: Any) -> Any:
        """Get element coordinates from pywinauto object.

        :param rectangle: item containing rectangle information
        :return: coordinates: left, top, right, bottom
        """
        self.logger.debug(
            "Get element coordinates from rectangle: %s of type %s",
            rectangle,
            type(rectangle),
        )
        left = 0
        top = 0
        right = 0
        bottom = 0
        if isinstance(rectangle, pywinauto.win32structures.RECT):
            left = rectangle.left
            top = rectangle.top
            right = rectangle.right
            bottom = rectangle.bottom
        else:
            left, top, right, bottom = map(
                int,
                re.match(
                    r"\(L(\d+).*T(\d+).*R(\d+).*B(\d+)\)", str(rectangle)
                ).groups(),
            )
        return left, top, right, bottom

    def screenshot(
        self,
        filename: str,
        element: dict = None,
        ctrl: Any = None,
        desktop: bool = False,
    ) -> None:
        """Save screenshot into filename.

        :param filename: name of the file
        :param element: take element screenshot if True, defaults to None
        :param ctrl: take control screenshot if True, defaults to None
        :param desktop: take desktop screenshot if True, defaults to False
        """
        if desktop:
            region = None
        elif element:
            region = self._get_element_coordinates(element["rectangle"])
        elif ctrl:
            region = self.get_dialog_rectangle(ctrl)
        else:
            region = self.get_dialog_rectangle()

        try:
            output_dir = BuiltIn().get_variable_value("${OUTPUT_DIR}")
        except (ModuleNotFoundError, RobotNotRunningError):
            output_dir = Path.cwd()

        filename = Path(output_dir, "images", clean_filename(filename))
        os.makedirs(filename.parent)
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

        attributes = [
            "automation_id",
            # "children",
            "class_name",
            "control_id",
            "control_type",
            # "descendants",
            # "dump_window",
            # "element"
            "enabled",
            # "filter_with_depth",
            # "framework_id",
            # "from_point",
            "handle",
            # "has_depth",
            # "iter_children",
            # "iter_descendants",
            "name",
            # "parent",
            "process_id",
            "rectangle",
            "rich_text",
            "runtime_id",
            # "set_cache_strategy",
            # "top_from_point",
            "visible",
        ]

        element_dict = {}
        # self.element_info = backend.registry.backends[_backend].element_info_class()
        element_info = element.element_info
        # self.logger.debug(element_info)
        for attr in attributes:
            if hasattr(element_info, attr):
                attr_value = getattr(element_info, attr)
                try:
                    element_dict[attr] = (
                        attr_value() if callable(attr_value) else str(attr_value)
                    )
                except TypeError:
                    pass
            else:
                self.logger.warning("did not have attr %s", attr)
        return element_dict

    def put_system_to_sleep(self) -> None:
        """Put Windows into sleep mode
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
        """
        ctypes.windll.User32.LockWorkStation()

    def log_in(self, username: str, password: str, domain: str = ".") -> str:
        """Log into Windows `domain` with `username` and `password`.

        :param username: name of the user
        :param password: password of the user
        :param domain: windows domain for the user, defaults to "."
        :return: handle
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
        """Drag elements from source and drop them on target.

        Please note that if CTRL is not pressed down during drag and drop then
        operation is MOVE operation, on CTRL down the operation is COPY operation.

        There will be also overwrite notification if dropping over existing files.

        :param src: application object or instance id
        :param target: application object or instance id
        :param ssrc_locator: elements to move
        :param target_locator: target element to drop source elements into
        :param handle_ctrl_key: True if keyword should press CTRL down dragging
        :param drop_delay: how many seconds to wait until releasing mouse drop,
            default 2.0
        :raises ValueError: on validation errors
        """
        if isinstance(src, int):
            src = self.get_app(src)
        if isinstance(target, int):
            target = self.get_app(target)

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

        if handle_ctrl_key:
            self.send_keys("{VK_LCONTROL down}")
            delay(0.5)
        # Select elements by mouse clicking

        for idx, selection in enumerate(selections):
            self.logger.debug("Selecting item %d by mouse_click", idx)
            pywinauto.mouse.click(coords=(selection[0], selection[1]))

        # Start drag from the last item
        pywinauto.mouse.press(coords=(source_x, source_y))
        delay(1)
        pywinauto.mouse.move(coords=(target_x, target_y))

        self.logger.debug("Cursor position: %s", win32api.GetCursorPos())
        delay(drop_delay)
        pywinauto.mouse.click(coords=(target_x, target_y))
        pywinauto.mouse.release(coords=(target_x, target_y))

        if handle_ctrl_key:
            self.send_keys("{VK_LCONTROL up}")
            delay(0.5)
        # Deselect elements by mouse clicking
        for selection in selections:
            self.logger.debug("Deselecting item by mouse_click")
            self.mouse_click_coords(selection[0], selection[1])

    def calculate_rectangle_center(self, rectangle: Any) -> Any:
        """Calculate x and y center coordinates from rectangle.

        :param rectangle: element rectangle coordinates
        :return: x and y coordinates of rectangle center
        """
        left, top, right, bottom = self._get_element_coordinates(rectangle)
        x = int((right - left) / 2) + left
        y = int((bottom - top) / 2) + top
        return x, y

    def get_window_list(self):
        """Get list of open windows

        Window dictionaries contain:

        - title
        - pid
        - handle

        :return: list of window dictionaries
        """
        windows = pywinauto.Desktop(backend="uia").windows()
        window_list = []
        for w in windows:
            window_list.append(
                {"title": w.window_text(), "pid": w.process_id(), "handle": w.handle}
            )
        return window_list
