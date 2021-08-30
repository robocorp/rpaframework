import atexit
import logging
import os
import platform
import queue
import threading
import time
from typing import Union
import warnings

from robot.api.deco import library, keyword
from robot.libraries.BuiltIn import BuiltIn

from RPA.Desktop import Desktop

if platform.system() == "Windows":
    import ctypes
    from ctypes import wintypes, byref

    # Configure comtypes to not generate DLL bindings into
    # current environment, instead keeping them in memory.
    # Slower, but prevents dirtying environments.
    import comtypes.client

    from JABWrapper.context_tree import ContextTree, ContextNode, SearchElement
    from JABWrapper.jab_wrapper import JavaAccessBridgeWrapper

    comtypes.client.gen_dir = None

    # Ignore warning about threading mode,
    # which comtypes initializes to STA instead of MTA on import.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        import win32con
        import win32gui

    PeekMessage = ctypes.windll.user32.PeekMessageW
    GetMessage = ctypes.windll.user32.GetMessageW
    TranslateMessage = ctypes.windll.user32.TranslateMessage
    DispatchMessage = ctypes.windll.user32.DispatchMessageW
    ScalingFactor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
    LocatorType = Union[ContextNode, str]
else:
    ScalingFactor = 1.0
    LocatorType = str
    ContextNode = object


class ElementNotFound(ValueError):
    """No matching elements were found."""


@library(scope="GLOBAL", doc_format="REST", auto_keywords=False)
class JavaAccessBridge:
    # pylint: disable=W1401
    """Java application UI automation library using `Java Access Bridge technology`_.

    Library is at the beta level at the moment so feedback is highly appreciated.

    The library utilizes `java-access-bridge-wrapper`_ package to interact with
    Java UI. Currently only the 64-bit Windows OS is supported.

    **Steps to enable**

        1. Enable the Java Access Bridge in Windows
        2. Set environment variable `RC_JAVA_ACCESS_BRIDGE_DLL` as an absolute path to `WindowsAccessBridge-64.dll`.
           It is also possible to give DLL location as library initialization parameter `access_bridge_path`.

        .. code-block:: console

            C:\\path\\to\\java\\bin\\jabswitch -enable
            set RC_JAVA_ACCESS_BRIDGE_DLL=C:\\path\\to\\Java\\bin\\WindowsAccessBridge-64.dll

        .. code:: robotframework

            *** Settings ***
            Library   RPA.JavaAccessBridge   access_bridge_path=C:\\path\\to\\Java\\bin\\WindowsAccessBridge-64.dll

    .. _Java Access Bridge technology: https://www.oracle.com/java/technologies/javase/javase-tech-access-bridge.html
    .. _java-access-bridge-wrapper: https://github.com/robocorp/java-access-bridge-wrapper

    **About Java wrapper callbacks and actions**

    There might be a compability issue with callbacks and actions on target Java application. Possible reasons:

    - target application is executed with 32-bit Java
    - target application does not support callbacks and/or actions

    Workaround for this situation is to initialize `JavaAccessBridge` library with parameter `ignore_callbacks=True`.
    Then application's element information is still accessible and any actions on those elements can be performed
    with `RPA.Desktop` library.

    *Note.* There are still keywords, for example. `Call Element Action`, which will cause error if used in this situation.
    To be fixed in future release.

    .. code:: robotframework

        *** Settings ***
        Library   RPA.JavaAccessBridge   ignore_callbacks=True

    **Locating elements**

    To automate actions on the Java application, the robot needs locations to various elements
    using a feature called `locators`. Locator describes properties of an element.

    At the moment library contains basic level support for locators.

    The common locator types are `name` and `role`.

    To identify element with more than one property `and` can be used, for example:

        .. code-block:: console

            role:push button and name:Clear

    To address element within parent element `>` can be used, for example:

        .. code-block:: console

            name:Find Purchase Orders > name:NumberField

    Some keywords accept element as an parameter in place of locator.

    **Interacting with elements**

    By default application elements are interacted with Actions supported by the element.
    Most common example is `click` action supported by an button element.

    But because application and technology support for the actions might be limited, it is also
    possible to opt for interaction elements by their coordinates by giving keyword parameter
    ``action=False`` if parameter is available.

    **Inspecting elements**

    Inspecting Java application elements depends on what kind of Java UI framework the application
    has been built with.

    The `Accessibility Insights for Windows`_ can show element properties if application framework
    supports Windows UI Automation (UIA), see more at `using Accessibility Insights`_.

    The Google's `Access Bridge Explorer`_ can also be used for inspecting Java application elements.

    .. _Accessibility Insights for Windows: https://accessibilityinsights.io/en/downloads/
    .. _Access Bridge Explorer: https://github.com/google/access-bridge-explorer
    .. _using Accessibility Insights: https://accessibilityinsights.io/docs/en/windows/reference/faq/#can-i-use-accessibility-insights-for-windows-on-a-windows-app-written-with-java

    **Examples**

    *robotframework*

    .. code:: robotframework

        *** Settings ***
        Library   RPA.JavaAccessBridge
        Library   Process

        *** Tasks ***
        Write text into Swing application
            Start Process    java -jar BasicSwing.jar
            ...              shell=${TRUE}
            ...              cwd=${CURDIR}
            Select Window    Chat Frame
            Type Text    role:text
            ...          text for the textarea
            Type Text    role:text
            ...          text for the input field
            ...          index=1
            ...          clear=${TRUE}
            Click Element    role:push button and name:Send

    *Python*

    .. code:: python

        from RPA.JavaAccessBridge import JavaAccessBridge
        import subprocess

        jab = JavaAccessBridge()

        subprocess.Popen(
            ["java", "-jar", "BasicSwing.jar"],
            shell=True,
            cwd=".",
            close_fds=True
        )
        jab.select_window("Chat Frame")
        jab.type_text(
            "role:text",
            "text for the textarea",
            enter=True
        )
        jab.type_text(
            "role:text",
            "text for the input field",
            index=1,
            clear=True
        )
        jab.click_element("role:push button and name:Send")

    """  # noqa: E501, W605

    # TODO: add keyword for taking screenshots of elements and window
    # TODO. implement proper XPath syntax support

    def __init__(self, ignore_callbacks: bool = False, access_bridge_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.desktop = Desktop()
        if platform.system() != "Windows":
            self.logger.warning(
                "JavaAccessBridge library requires Windows dependencies to work"
            )
        if access_bridge_path:
            os.environ["RC_JAVA_ACCESS_BRIDGE_DLL"] = access_bridge_path
        if "RC_JAVA_ACCESS_BRIDGE_DLL" not in os.environ.keys():
            self.logger.warning(
                "Environment variable `RC_JAVA_ACCESS_BRIDGE_DLL` needs to be set to "
                "absolute path of `WindowsAccessBridge-64.dll`"
            )
        self.version_printed = False
        self.jab_wrapper = None
        self.context_info_tree = None
        self.pumper_thread = None
        self.refresh_counter = 1
        self.display_scale_factor = ScalingFactor
        self.ignore_callbacks = ignore_callbacks

    def _initialize(self):
        pipe = queue.Queue()
        self.pumper_thread = threading.Thread(
            target=self._pump_background, daemon=True, args=[pipe]
        )
        self.pumper_thread.start()
        self.jab_wrapper = pipe.get(timeout=10)
        if not self.jab_wrapper:
            raise Exception("Failed to initialize Java Access Bridge Wrapper")
        time.sleep(1)
        atexit.register(self._handle_shutdown)
        self.logger.info("Java Access Bridge Wrapper initialized")

    def _handle_shutdown(self):
        if self.jab_wrapper:
            self.jab_wrapper.shutdown()

    def _pump_background(self, pipe: queue.Queue):
        try:
            jab_wrapper = JavaAccessBridgeWrapper(
                ignore_callbacks=self.ignore_callbacks
            )
            pipe.put(jab_wrapper)
            message = byref(wintypes.MSG())
            while GetMessage(message, 0, 0, 0) > 0:
                TranslateMessage(message)
                self.logger.debug("Dispatching msg=%s", repr(message))
                DispatchMessage(message)
        # pylint: disable=broad-except
        except Exception as err:
            self.logger.error(err)
            pipe.put(None)
        finally:
            self.logger.info("Stopped processing events")

    @keyword
    def select_window(
        self, title: str, bring_foreground: bool = True, timeout: int = 30
    ):
        """Selects Java application window as target for the automation

        :param title: application window title
        :param bring_foreground: if application is brought to foreground or not
        :param timeout: selection timeout
        """
        if self.jab_wrapper is None:
            self._initialize()
        window_found = False
        interval = float(0.5)
        end_time = time.time() + float(timeout)
        while time.time() <= end_time:
            start = time.time()
            try:
                self.jab_wrapper.switch_window_by_title(title)
                window_found = True
                break
            except Exception:  # pylint: disable=broad-except
                pass
            finally:
                duration = time.time() - start
                if duration < interval:
                    time.sleep(interval - duration)

        if not window_found:
            raise ValueError("Did not find window '%s'" % title)

        if not self.version_printed:
            self.get_version_info()
            self.version_printed = True

        if bring_foreground:
            handle = self.jab_wrapper.get_current_windows_handle()
            # pylint: disable=c-extension-no-member
            win32gui.ShowWindow(handle, win32con.SW_SHOW)
            # pylint: disable=c-extension-no-member
            win32gui.SetForegroundWindow(handle)

        self.application_refresh()

    def _parse_locator(self, locator):
        levels = locator.split(">")
        levels = [lvl.strip() for lvl in levels]
        searches = []
        for lvl in levels:
            conditions = lvl.split(" and ")
            lvl_search = []
            for cond in conditions:
                parts = cond.split(":", 1)
                if len(parts) == 1:
                    parts = ["name", parts[0]]
                lvl_search.append(parts)
            searches.append(lvl_search)
        return searches

    def _find_elements(self, locator: str, index: int = None):
        if not self.context_info_tree:
            raise ValueError("ContextTree has not been initialized")
        searches = self._parse_locator(locator)
        self.logger.info("Searches: %s", searches)
        elements = []
        for lvl, search in enumerate(searches):
            search_elements = []
            for s in search:
                search_elements.append(SearchElement(s[0], s[1]))
            if lvl == 0:
                elements = self.context_info_tree.get_by_attrs(search_elements)
            else:
                sub_matches = []
                for elem in elements:
                    matches = elem.get_by_attrs(search_elements)
                    sub_matches.extend(matches)
                elements = sub_matches
        self.logger.info('Search "%s" returned %s element(s)', locator, len(elements))
        if index and len(elements) > (index + 1):
            raise AttributeError(
                "Locator '%s' returned only %s elements (can't index element at %s)"
                % (locator, len(elements), index)
            )
        return elements if index is None else [elements[index]]

    @keyword
    def set_mouse_position(self, element: ContextNode):
        """Set mouse position to element center

        :param element: target element
        """
        left, top, right, bottom = self._get_scaled_coordinates(element)
        middle_x = int((left + right) / 2)
        middle_y = int((top + bottom) / 2)
        point = f"point:{middle_x},{middle_y}"
        self.desktop.move_mouse(point)

    @keyword
    def type_text(
        self,
        locator: str,
        text: str,
        index: int = 0,
        clear: bool = False,
        enter: bool = False,
    ):
        """Type text into coordinates defined by locator

        :param locator: target element
        :param text: text to write
        :param index: target element if multiple are returned
        :param clear: should element be cleared before typing
        :param enter: should enter key be pressed after typing
        """
        element = self._find_elements(locator, index)
        self._click_element_middle(element[0], "double click")
        if not self.ignore_callbacks:
            element[0].request_focus()
        if clear:
            self.desktop.press_keys("ctrl", "a")
            self.desktop.press_keys("delete")
        self.desktop.type_text(text, enter=enter)

    def _clear_element(self, element):
        self.wait_until_element_is_focused(element)
        element_cleared = False
        for _ in range(10):
            self.desktop.press_keys("ctrl", "a")
            self.desktop.press_keys("delete")
            try:
                self.wait_until_element_text_equals(element, "")
                element_cleared = True
            except ValueError:
                pass
        if not element_cleared:
            raise ValueError(f"Element={element} not cleared")

    @keyword
    def get_elements(self, locator: str):
        """Get matching elements

        :param locator: elements to get
        """
        return self._find_elements(locator)

    @keyword
    def wait_until_element_text_contains(
        self, locator: LocatorType, text: str, index: int = 0, timeout: float = 0.5
    ):
        """Wait until element text contains expected text

        :param locator: target element
        :param text: element text should contain this
        :param index: target element index if multiple are returned
        :param timeout: timeout in seconds to wait, default 0.5 seconds
        """
        matching = self._get_matching_element(locator, index)
        end_time = time.time() + float(timeout)
        while time.time() <= end_time:
            # pylint: disable=protected-access
            if text in matching.text._items.sentence:
                return
            time.sleep(0.05)

        raise ValueError(f"Text={text} not found in element={matching}")

    @keyword
    def wait_until_element_text_equals(
        self, locator: LocatorType, text: str, index: int = 0, timeout: float = 0.5
    ):
        """Wait until element text equals expected text

        :param locator: target element
        :param text: element text should match this
        :param index: target element index if multiple are returned
        :param timeout: timeout in seconds to wait, default 0.5 seconds
        """
        matching = self._get_matching_element(locator, index)
        end_time = time.time() + float(timeout)
        while time.time() <= end_time:
            # pylint: disable=protected-access
            if text == matching.text._items.sentence:
                return
            time.sleep(0.05)

        raise ValueError(f"Text={text} not found in element={matching}")

    @keyword
    def wait_until_element_is_focused(
        self, locator: LocatorType, index: int = 0, timeout: float = 0.5
    ):
        """Wait until element is focused

        :param locator: target element
        :param index: target element index if multiple are returned
        :param timeout: timeout in seconds to wait, default 0.5 seconds
        """
        matching = self._get_matching_element(locator, index)
        end_time = time.time() + float(timeout)
        while time.time() <= end_time:
            if matching.state == "focused":
                return
            time.sleep(0.05)

        raise ValueError(f"Element={matching} not focused")

    @keyword
    def get_element_text(self, locator: LocatorType, index: int = 0):
        """Get element text

        :param locator: target element
        :param index: target element index if multiple are returned
        """
        matching = self._get_matching_element(locator, index)
        # pylint: disable=protected-access
        return matching.text._items.sentence

    def _get_matching_element(self, locator: LocatorType, index: int = 0):
        matching = None
        if isinstance(locator, str):
            elements = self._find_elements(locator)
            if len(elements) < (index + 1):
                raise ElementNotFound(
                    "Locator '%s' matched only %s elements" % (locator, len(elements))
                )
            matching = elements[index]
        else:
            matching = locator
        return matching

    @keyword
    def get_element_actions(self, locator: str):
        """Get list of possible element actions

        :param locator: target element
        """
        elements = self._find_elements(locator)
        return elements[0].get_actions().keys()

    def _elements_to_console(self, elements, function=""):
        BuiltIn().log_to_console(f"\nElements to Console: {function}")
        for elem in elements:
            BuiltIn().log_to_console(str(elem).strip())

    @keyword
    def highlight_element(self, locator: LocatorType, index: int = 0):
        """Highlight an element

        :param locator: element to highlight
        :param index: target element index if multiple are returned
        """
        matching = self._get_matching_element(locator, index)
        self.logger.info("Highlighting element: %s", repr(matching))
        region_locator = self._get_region_locator(matching)
        self.desktop.highlight_elements(region_locator)

    def _get_scaled_coordinates(self, element):
        left = int(element.context_info.x / self.display_scale_factor)
        top = int(element.context_info.y / self.display_scale_factor)
        width = int(element.context_info.width / self.display_scale_factor)
        height = int(element.context_info.height / self.display_scale_factor)
        right = left + width
        bottom = top + height
        return left, top, right, bottom

    def _get_region_locator(self, element):
        left, top, right, bottom = self._get_scaled_coordinates(element)
        return self.desktop.define_region(left, top, right, bottom)

    @keyword
    def click_element(
        self,
        locator: LocatorType,
        index: int = 0,
        action: bool = True,
        timeout: int = 10,
    ):
        """Click element

        :param target: element to click
        :param index: target element index if multiple are returned
        :param action: call click action on element (default), or use coordinates
        :param timeout: timeout in seconds to find element
        """
        if isinstance(locator, str):
            interval = float(0.2)
            end_time = time.time() + float(timeout)
            while time.time() <= end_time:
                start = time.time()
                elements = self._find_elements(locator)
                if len(elements) > 0:
                    break
                duration = time.time() - start
                if duration < interval:
                    time.sleep(interval - duration)

            if len(elements) < (index + 1):
                raise ElementNotFound(
                    "Locator '%s' matched only %s elements" % (locator, len(elements))
                )
            matching = elements[index]
        else:
            matching = locator
        try:
            if action:
                self.logger.info("Element click action type:%s", type(matching))
                matching.do_action("click")
            else:
                self._click_element_middle(matching)
        except NotImplementedError:
            self._click_element_middle(matching)

    @keyword
    def call_element_action(self, locator: str, action: str):
        """Call element action

        :param locator: target element
        :param action: name of the element action to call
        """
        elements = self._find_elements(locator)
        if len(elements) != 1:
            raise ElementNotFound("Locator %s did not match a unique element" % locator)
        matching = elements[0]
        self.logger.info("Element '%s' action", action)
        matching.do_action(action)

    def _click_element_middle(self, element, click_type="click"):
        # TODO. change to use RPA.core.geometry Region/Point
        # region = Region.from_size(
        # element.left,
        # element.top,
        # element.width,
        # element.height
        # )
        # region.scale(self.scale_factor)
        # Desktop().click(region.center)
        self.logger.info("Element click coordinates")
        middle_x = element.context_info.x + int(element.context_info.width / 2)
        middle_y = element.context_info.y + int(element.context_info.height / 2)
        locator = f"coordinates:{middle_x},{middle_y}"
        self.desktop.click(locator, action=click_type)
        time.sleep(0.5)

    @keyword
    def toggle_drop_down(self, locator: str, index: int = 0):
        """Toggle dropdown action on element

        :param locator: element locator
        :param index: target element index if multiple are returned
        """
        elements = self._find_elements(locator)
        matching = elements[index]
        matching.toggle_drop_down()

    @keyword
    def application_refresh(self):
        """Refresh application element tree

        Might be required action after application element
        structure changes after window refresh.
        """
        self.context_info_tree = ContextTree(self.jab_wrapper)

    @keyword
    def press_keys(self, *keys):
        """Press multiple keys down simultaneously

        See `Desktop`_ library documentation for supported keys

        .. _Desktop: https://rpaframework.org/libraries/desktop/index.html

        :param keys: keys to press
        """
        self.desktop.press_keys(*keys)

    @keyword
    def print_element_tree(self, filename: str = None):
        """Print current element into log and possibly into a file

        :param filename: filepath to save element tree
        """
        tree = repr(self.context_info_tree)
        self.logger.info(tree)
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(tree)
            self.logger.info("Context tree written to file '%s'", filename)
        return tree

    @keyword
    def select_menu(self, menu: str, menuitem: str):
        """Select menu by clicking menu elements

        :param menu: name of the menu
        :param menuitem: name of the menu item
        """
        self.click_element(f"role:menu and name:{menu}")
        self.click_element(f"role:menu item and name:{menuitem}")

    @keyword
    def click_push_button(self, button_name: str):
        """Click element of role `push button`

        :param button_name: name of the button to click
        """
        locator = f"role:push button and name:{button_name}"
        self.click_element(locator)

    @keyword
    def shutdown_jab(self):
        """Call Java Access Bridge process shutdown"""
        self.jab_wrapper.shutdown()

    @keyword
    def get_version_info(self):
        """Get Java Access Bridge version information"""
        version_info = self.jab_wrapper.get_version_info()
        self.logger.info(
            "VMversion=%s; BridgeJavaClassVersion=%s; BridgeJavaDLLVersion=%s; BridgeWinDLLVersion=%s",  # noqa: E501
            version_info.VMversion,
            version_info.bridgeJavaClassVersion,
            version_info.bridgeJavaDLLVersion,
            version_info.bridgeWinDLLVersion,
        )
        return version_info
