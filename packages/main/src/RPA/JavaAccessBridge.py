import atexit
from dataclasses import dataclass
import logging
import os
import platform
import queue
import threading
import time
from typing import List, Optional, Union
import warnings

from robot.api.deco import library, keyword
from robot.libraries.BuiltIn import BuiltIn

from RPA.Desktop import Desktop
from RPA.core.logger import deprecation


DESKTOP = Desktop()


def get_scaled_coordinate(coordinate, scaling_factor):
    return int(coordinate * scaling_factor)


if platform.system() == "Windows":  # noqa: C901
    import ctypes
    from ctypes import wintypes, byref
    from JABWrapper.context_tree import ContextTree, ContextNode, SearchElement
    from JABWrapper.jab_wrapper import JavaAccessBridgeWrapper

    # Configure comtypes to not generate DLL bindings into
    # current environment, instead keeping them in memory.
    # Slower, but prevents dirtying environments.
    import comtypes.client

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
    ScalingFactor: float = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100

    @dataclass
    class JavaElement:
        """Abstraction for Java object properties"""

        name: str
        role: str
        description: str
        states: list
        ancestry: int
        checked: bool
        selected: bool
        visible: bool
        enabled: bool
        showing: bool
        focusable: bool
        states_string: str
        x: int
        y: int
        width: int
        height: int
        node: ContextNode
        row: int
        col: int
        text: str
        column_count: int
        visible_children: list
        visible_children_count: int
        index_in_parent: int

        def __init__(
            self,
            node,
            scaling_factor: Optional[float] = None,
            index: int = 0,
            column_count: Optional[int] = None,
        ):
            scaling_factor = scaling_factor or ScalingFactor
            self.name = node.context_info.name
            self.role = node.context_info.role
            self.description = node.context_info.description
            self.states = node.context_info.states.split(",")
            self.ancestry = node.ancestry
            self.checked = "checked" in self.states
            self.selected = "selected" in self.states
            self.visible = "visible" in self.states
            self.enabled = "enabled" in self.states
            self.showing = "showing" in self.states
            self.focusable = "focusable" in self.states
            self.node = node
            self.states_string = node.context_info.states
            self.x = get_scaled_coordinate(node.context_info.x, scaling_factor)
            self.y = get_scaled_coordinate(node.context_info.y, scaling_factor)
            self.width = get_scaled_coordinate(node.context_info.width, scaling_factor)
            self.height = get_scaled_coordinate(
                node.context_info.height, scaling_factor
            )
            self.center_x = self.x + int(self.width / 2)
            self.center_y = self.y + int(self.height / 2)
            self.text = node.text._items.sentence
            self.visible_children = node.get_visible_children()
            self.visible_children_count = node.visible_children_count
            self.index_in_parent = node.context_info.indexInParent
            self.column_count = column_count
            self.set_rows_columns(self.visible_children, index=index)

        def set_rows_columns(self, children: List[ContextNode], index: int = 0):
            if not self.column_count:
                self.column_count = 0
                if children:
                    self.column_count = 1
                    java_child = JavaElement(children[0])
                    x_pos, y_pos = java_child.x, java_child.y
                    for child in children[1:]:
                        java_child = JavaElement(child)
                        if java_child.x == x_pos or java_child.y != y_pos:
                            break
                        self.column_count += 1

            if self.column_count > 0:
                self.row = (
                    0 if index < self.column_count else int(index / self.column_count)
                )
                self.col = (
                    index
                    if index < self.column_count
                    else int(index - (self.row * self.column_count))
                )
            else:
                self.row = -1
                self.col = -1

        def click(self, click_type: str = "click"):
            if self.x != -1 and self.y != -1:
                locator = f"coordinates:{self.center_x},{self.center_y}"
                DESKTOP.click(locator, action=click_type)

        def type_text(self, text: str, clear: bool = False) -> None:
            self.click()
            if clear:
                DESKTOP.press_keys("ctrl", "a")
                time.sleep(0.2)
                DESKTOP.press_keys("delete")
                time.sleep(0.2)
            for c in text:
                DESKTOP.press_keys(c)

        def __str__(self):
            string = (
                f"name={self.name}; "
                f"role={self.role}; "
                f"enabled={self.enabled}; "
                f"visible={self.visible}; "
                f"selected={self.selected}; "
                f"checked={self.checked}; "
                f"showing={self.checked}; "
                f"focusable={self.checked}; "
                f"description={self.description}; "
                f"ancestry={self.ancestry}; "
                f"states={self.states}; "
                f"x={self.x}; "
                f"y={self.y}; "
                f"width={self.width}; "
                f"height={self.height}; "
                f"center_x={self.center_x}; "
                f"center_y={self.center_y}; "
                f"indexInParent={self.index_in_parent}; "
                f"childrentCount={self.visible_children_count};"
            )
            return string

    LocatorType = Union[ContextNode, JavaElement, str]
else:
    ScalingFactor = 1.0
    LocatorType = str
    ContextNode = object
    JavaElement = object


class ElementNotFound(ValueError):
    """No matching elements were found."""


class JavaWindowNotFound(ValueError):
    """No active Java window were found."""


class InvalidLocatorError(AttributeError):
    """Invalid locator string."""


IntegerLocatorTypes = [
    "x",
    "y",
    "width",
    "height",
    "indexInParent",
    "ancestry",
    "childrentCount",
]


@library(scope="GLOBAL", doc_format="REST", auto_keywords=False)
class JavaAccessBridge:
    # pylint: disable=W1401
    """Java application UI automation library using `Java Access Bridge technology`_.

    The library utilizes `java-access-bridge-wrapper`_ package to interact with
    Java UI. Currently only the 64-bit Windows OS is supported.

    **Inspecting elements**

    We have built an `Assistant`_ for working with Java application's element structure and `Java locators`_.
    The Assistant provides copy-paste-able locators for each element and also allows testing locators against
    selected application.

    If our tools fail to pick the locator from your target application, there is always the
    `Access Bridge Explorer`_ from Google that enables you to see the raw view. Please note that
    Access Bridge Explorer repository has been archived on July 27, 2022 and is no longer actively
    maintained.

    The `Accessibility Insights for Windows`_ can show element properties if application framework
    supports Windows UI Automation (UIA), see more at `using Accessibility Insights`_. Then the recommended
    library would be `RPA.Windows`_ library.

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
    .. _Assistant: https://github.com/robocorp/working-with-java

    **About Java wrapper callbacks and actions**

    There might be a compatibility issue with callbacks and actions on target Java application. Possible reasons:

    - target application is executed with 32-bit Java
    - target application does not support callbacks and/or actions

    Workaround for this situation is to initialize `JavaAccessBridge` library with parameter `ignore_callbacks=True`.
    Then application's element information is still accessible and any actions on those elements can be performed
    with `RPA.Desktop` library. Keep in mind that you can still manuall refresh an element with ``Refresh Element``.

    *Note.* There are still keywords, for example. ``Call Element Action``, which will cause error if used in this
    situation.

    .. code:: robotframework

        *** Settings ***
        Library   RPA.JavaAccessBridge   ignore_callbacks=True

    **Controlling the Java window**

    Keyword for this purpose is ``Select Window``. Window selection is based on the ``title`` parameter, which can be
    given as a regular expressions to match the correct window. The keyword brings the window into focus and initially
    reads window's element structure.

    **Locating elements**

    To automate actions on the Java application, the robot needs locations to various elements
    using a feature called `Java locators`_. Locator describes properties of an element.

    At the moment library contains basic level support for locators.

    The common locator types are ``name`` and ``role``.

    To identify element with more than one property `and` can be used, for example:

        .. code-block:: console

            role:push button and name:Clear

    To address element within parent element `>` can be used, for example:

        .. code-block:: console

            name:Find Purchase Orders > name:NumberField

    Some keywords accept element as an parameter in place of locator.

    New locator type `strict` has been added in rpaframework==12.5.0. Currently
    property values of string type have been evaluated with `startsWith` which
    can match several property values. With `strict` set in the locator string,
    all locator on the right side of this definition will be matched using
    strict (equal matching), example:

        .. code-block:: robotframework

            # without strict, name can be 'Type', 'Type1', 'Type of'...
            Get Elements   role:push button and name:Type
            # name must be equal to 'Type'
            Get Elements  role:push button and strict:True and name:Type

    Keyword ``Get Elements`` has extra parameter ``strict``, which when set to
    ``True`` forces all locator value matches to be strict, example:

        .. code-block:: robotframework

            # without strict, name can be 'Type', 'Type1', 'Type of'...
            Get Elements  role:push button and name:Type
            # name must be equal to 'Type' and role must be equal to 'text'
            Get Elements  role:text and name:Type  strict=True

    **About JavaElement object**

    The ``JavaElement`` was added in rpaframework==12.3.0 for easy access into
    ``ContextNode`` objects which have been returned by ``Get Elements`` keyword.

    Keyword ``Get Elements`` still returns ``ContextNode`` objects, but with parameter
    ``java_elements=True`` the keyword returns ``JavaElement`` objects instead (they
    still contain reference to ``ContextNode`` object via ``node`` property, e.g.
    JavaObject.node).

    Properties and methods included in the JavaElement:

    - name: str
    - role: str
    - description: str
    - states: list            # list presentation of states (string)
    - ancestry: int           # you can set the maximum depth based on this
    - checked: bool
    - selected: bool
    - visible: bool
    - enabled: bool
    - showing: bool
    - focusable: bool
    - states_string: str
    - x: int                  # left coordinate of the element
    - y: int                  # top coordinate of the element
    - width: int
    - height: int
    - node: ContextNode       # original ContextNode
    - row: int                # table row, -1 if element is not member of table
    - col: int                # table column, -1 if element is not member of table
    - text: str               # text content of the element
    - column_count: int       # table column count
    - visible_children: list  # visible children elements of this element
    - visible_children_count: int
    - index_in_parent: int    # position in the parent
    - click()                 # method for clicking element center
    - type_text()             # method for typing text into element (if possible)

    **Interacting with elements**

    By default application elements are interacted with Actions supported by the element.
    Most common example is `click` action supported by an button element.

    But because application and technology support for the actions might be limited, it is also
    possible to opt for interaction elements by their coordinates by giving keyword parameter
    ``action=False`` if parameter is available.

    .. _Accessibility Insights for Windows: https://accessibilityinsights.io/en/downloads/
    .. _Access Bridge Explorer: https://github.com/google/access-bridge-explorer
    .. _using Accessibility Insights: https://accessibilityinsights.io/docs/en/windows/reference/faq/#can-i-use-accessibility-insights-for-windows-on-a-windows-app-written-with-java
    .. _RPA.Windows: https://robocorp.com/docs/libraries/rpa-framework/rpa-windows
    .. _Java locators: https://robocorp.com/docs/development-guide/locators#java-locators

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

    def __init__(
        self,
        ignore_callbacks: bool = False,
        access_bridge_path: Optional[str] = None,
        max_depth: Optional[int] = None,
        disable_refresh: bool = False,
    ):
        """If library is not given ``access_bridge_path`` then path needs to be given
        by the environment variable ``RC_JAVA_ACCESS_BRIDGE_DLL``.

        The ``ignore_callbacks`` can be set to ``True`` if the target application
        does not support Java callback feature (property value change listeners).

        :param ignore_callbacks: set to `True` if application does not support
            Java callback feature, defaults to False
        :param access_bridge_path: absolute filepath to the DLL, defaults to None
        :param max_depth: limit the height of the element tree (how deep the search
            goes); by default every element is taken into account and the tree of
            elements is built until reaching the last leaf (which might be
            time-consuming)
        :param disable_refresh: disables automatic app/element refresh when this is
            `True` (saves time); by default, automatic app/element refreshes are
            triggered with keywords like ``Read Table``, ``Wait Until Element Exists``
        """
        self.logger = logging.getLogger(__name__)
        desktoplogger = logging.getLogger("RPA.Desktop")
        desktoplogger.setLevel(logging.WARNING)
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
        self.display_scale_factor = ScalingFactor
        self.ignore_callbacks = ignore_callbacks
        self.max_depth = max_depth
        self.disable_refresh = disable_refresh
        self.pid = None

    def _initialize(self):
        pipe = queue.Queue()
        self.pumper_thread = threading.Thread(
            target=self._pump_background, daemon=True, args=[pipe]
        )
        self.pumper_thread.start()
        obj = pipe.get(timeout=10)
        if isinstance(obj, Exception):
            raise obj
        if isinstance(obj, JavaAccessBridgeWrapper):
            self.jab_wrapper = obj
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
            pipe.put(err)
        finally:
            self.logger.info("Stopped processing events")

    @keyword
    def set_display_scale_factor(self, factor: float) -> float:
        """Override library display scale factor.

        Keyword returns previous value.

        :param factor: value for the new display scale factor
        :return: previous display scale factor value
        """
        previous_factor = self.display_scale_factor
        self.display_scale_factor = factor
        return previous_factor

    @keyword
    def select_window(
        self, title: str, bring_foreground: bool = True, timeout: int = 30
    ):
        """Selects Java application window as target for the automation using
        Java window title.

        :param title: application window title
        :param bring_foreground: if application is brought to foreground or not
        :param timeout: selection timeout
        """
        deprecation(
            "Keyword `Select Window` is deprecated and will be removed in the "
            "next major update to the `RPA.JavaAccessBridge` library. "
            "Please use `Select Window By Title` or `Select Window By PID` keywords "
            "instead."
        )
        self._select_window(
            title=title, bring_foreground=bring_foreground, timeout=timeout
        )

    def _parse_locator(self, locator, strict_default=False):
        levels = locator.split(">")
        levels = [lvl.strip() for lvl in levels]
        searches = []
        for lvl in levels:
            conditions = lvl.split(" and ")
            lvl_search = []
            strict_mode = strict_default
            for cond in conditions:
                parts = cond.split(":", 1)
                if len(parts) == 1:
                    parts = ["name", parts[0]]
                elif parts[0].lower() == "strict":
                    strict_mode = bool(parts[1])
                    continue
                elif parts[0] in IntegerLocatorTypes:
                    try:
                        parts[1] = int(parts[1])
                    except ValueError as err:
                        raise InvalidLocatorError(
                            "Locator '%s' needs to be of 'integer' type" % parts[0]
                        ) from err
                lvl_search.append(SearchElement(parts[0], parts[1], strict=strict_mode))
            searches.append(lvl_search)
        return searches

    def _find_elements(
        self, locator: str, index: Optional[int] = None, strict: bool = False
    ) -> Union[ContextNode, List[ContextNode]]:
        if not self.context_info_tree:
            raise ValueError("ContextTree has not been initialized")
        searches = self._parse_locator(locator, strict)
        self.logger.info("Searches: %s", searches)
        elements = []
        for lvl, search_elements in enumerate(searches):
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
        return elements[index] if index else elements

    @keyword
    def set_mouse_position(self, element: ContextNode):
        """Set mouse position to element center

        :param element: target element
        """
        left, top, right, bottom = self._get_scaled_coordinates(element)
        middle_x = int((left + right) / 2)
        middle_y = int((top + bottom) / 2)
        point = f"point:{middle_x},{middle_y}"
        DESKTOP.move_mouse(point)

    @keyword
    def type_text(
        self,
        locator: LocatorType,
        text: str,
        index: int = 0,
        clear: bool = False,
        enter: bool = False,
        typing: bool = True,
    ):
        """Type text into coordinates defined by locator

        :param locator: target element
        :param text: text to write
        :param index: target element if multiple are returned
        :param clear: should element be cleared before typing
        :param enter: should enter key be pressed after typing
        :param typing: if True (default) will use Desktop().type_text()
         if False will use Desktop().press_keys()
        """
        target = self._get_matching_element(locator, index)
        self.click_element(target, click_type="double click")

        if not self.ignore_callbacks:
            target.request_focus()
            time.sleep(1)  # this takes time and interferes with the keys sending below
        if clear:
            DESKTOP.press_keys("ctrl", "a")
            time.sleep(0.2)
            DESKTOP.press_keys("delete")
            time.sleep(0.2)
        self.logger.info("type text: %s", text)
        if typing:
            DESKTOP.type_text(text, enter=enter)
        else:
            for c in text:
                DESKTOP.press_keys(c)
            if enter:
                DESKTOP.press_keys("enter")

    @keyword
    def get_elements(
        self, locator: str, java_elements: bool = False, strict: bool = False
    ) -> List[Union[ContextNode, JavaElement]]:
        """Get matching elements

        :param locator: elements to get
        :param java_elements: if True will return elements as ``JavaElement``
         on False will return Java ContextNodes
        :param strict: on True all locator matches need to match exactly, on
         False will be using startsWith matching on non-integer properties
        :return: list of ContextNodes or JavaElements

        Python example.

        .. code:: python

            elements = java.get_elements("name:common", java_elements=True)
            for e in elements:
                print(e.name if e.name else "EMPTY", e.visible, e.x, e.y)
                if e.role == "check box":
                    e.click()
                else:
                    java.type_text(e, "new content", clear=True, typing=False)

            # following does NOT return anything because search is strict
            # and there are no 'push butto' role
            elements = java.get_elements("role:push butto", strict=True)

        Robotframework  example.

        .. code:: robotframework

            ${elements}=    Get Elements
            ...    role:push button and name:Send
            ...    java_elements=True
            Evaluate   $elements[0].click()
            Click Element    ${elements}[0]    action=False
            Type Text
            ...    ${elements}[0]
            ...    moretext
            ...    clear=True
            ...    typing=False
        """
        elements = self._find_elements(locator, strict=strict)
        return (
            [JavaElement(e, self.display_scale_factor) for e in elements]
            if java_elements
            else elements
        )

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
        java_element = self._get_matching_element(locator, index, as_java_element=True)
        end_time = time.time() + float(timeout)
        self.logger.info("Focusing on element: %s", java_element)

        while time.time() <= end_time:
            if "focused" in java_element.states:
                return
            time.sleep(0.05)

        raise ValueError(f"Element={java_element} not focused")

    @keyword
    def get_element_text(self, locator: LocatorType, index: int = 0):
        """Get element text

        :param locator: target element
        :param index: target element index if multiple are returned
        """
        matching = self._get_matching_element(locator, index)
        # pylint: disable=protected-access
        return matching.text._items.sentence

    def _get_matching_element(
        self,
        locator: LocatorType,
        index: int = 0,
        as_java_element: bool = False,
        refresh: bool = False,
    ) -> Union[ContextNode, JavaElement]:
        matching = None
        if isinstance(locator, str):
            elements = self._find_elements(locator)
            if len(elements) < (index + 1):
                raise ElementNotFound(
                    "Locator '%s' matched  %s elements" % (locator, len(elements))
                )
            matching = elements[index]
        elif isinstance(locator, ContextNode):
            matching = locator
        elif isinstance(locator, JavaElement):
            matching = locator.node

        if refresh and not self.disable_refresh:
            matching.refresh()
        return (
            JavaElement(matching, self.display_scale_factor)
            if as_java_element
            else matching
        )

    @keyword
    def get_element_actions(self, locator: LocatorType) -> List[str]:
        """Get list of possible element actions

        :param locator: target element
        """
        if isinstance(locator, str):
            target = self._find_elements(locator, index=0)
        elif isinstance(locator, ContextNode):
            target = locator
        else:
            target = locator.node
        return target.get_actions()

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
        DESKTOP.highlight_elements(region_locator)

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
        return DESKTOP.define_region(left, top, right, bottom)

    @keyword
    def click_element(
        self,
        locator: LocatorType,
        index: int = 0,
        action: bool = True,
        timeout: int = 10,
        click_type: str = "click",
    ):
        """Click element

        :param locator: element to click
        :param index: target element index if multiple are returned
        :param action: call click action on element (default), or use coordinates
        :param timeout: timeout in seconds to find element
        :param click_type: default `click`, see `RPA.Desktop` for different
         click options
        """
        if isinstance(locator, str):
            elements = self.wait_until_element_exists(locator, timeout)
            if len(elements) < (index + 1):
                # print element tree when result is not expected
                self.print_element_tree()
                raise ElementNotFound(
                    "Locator '%s' matched only %s elements" % (locator, len(elements))
                )
            element = elements[index]
        else:
            element = locator
        try:
            if action:
                self.logger.info("Element click action type: %s", type(element))
                element.click()  # works for both `ContextNode` & `JavaElement`
            else:
                self._click_element_middle(element, click_type)
        except NotImplementedError:
            self._click_element_middle(element, click_type)

    @keyword
    def call_element_action(self, locator: str, action: str):
        """Call element action

        :param locator: target element
        :param action: name of the element action to call
        """
        if isinstance(locator, str):
            elements = self._find_elements(locator)
            if len(elements) != 1:
                raise ElementNotFound(
                    "Locator %s did not match a unique element" % locator
                )

            matching = elements[0]
        else:
            matching = locator
        self.logger.info("Element '%s' action", action)
        matching.do_action(action)

    def _click_element_middle(self, element, click_type="click"):
        self.logger.info("Element click coordinates")
        if not isinstance(element, JavaElement):
            java_element = JavaElement(element, self.display_scale_factor)
        else:
            java_element = element
        self.click_coordinates(java_element.center_x, java_element.center_y, click_type)

    @keyword
    def click_coordinates(
        self, x: int, y: int, click_type: str = "click", delay: float = 0.5
    ):
        """Keyword to mouse click at specific coordinates.

        :param x: horizontal coordinate
        :param y: vertical coordinates
        :param click_type: default `click`, see `RPA.Desktop` for different
         click options
        :param delay: how much in seconds to delay after click, defaults to 0.5
        """
        locator = f"coordinates:{x},{y}"
        DESKTOP.click(locator, action=click_type)
        time.sleep(delay)

    @keyword
    def toggle_drop_down(self, locator: LocatorType, index: int = 0):
        """Toggle dropdown action on element

        :param locator: element locator
        :param index: target element index if multiple are returned
        """
        matching = self._get_matching_element(locator, index)
        matching.toggle_drop_down()

    def _application_refresh(self, force: bool = False):
        if self.disable_refresh and not force:
            self.logger.debug("Refresh triggered, but disabled globally by user.")
            return

        self.logger.info(
            "%s refreshing the entire app to a maximum depth of %d.",
            "Forcibly" if force else "Automatically",
            self.max_depth if self.max_depth is not None else -1,
        )
        self.context_info_tree = ContextTree(self.jab_wrapper, max_depth=self.max_depth)

    @keyword
    def application_refresh(self):
        """Refresh application element tree

        Might be required action after application element
        structure changes after window refresh.
        """
        self._application_refresh(force=True)

    @keyword
    def press_keys(self, *keys):
        """Press multiple keys down simultaneously

        See `Desktop`_ library documentation for supported keys

        .. _Desktop: https://rpaframework.org/libraries/desktop/index.html

        :param keys: keys to press
        """
        DESKTOP.press_keys(*keys)

    @keyword
    def print_element_tree(self, filename: Optional[str] = None):
        """Print current element into log and possibly into a file

        :param filename: filepath to save element tree
        :return: element tree
        """
        tree = repr(self.context_info_tree)
        self.logger.info(tree)
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(tree)
            self.logger.info("Context tree written to file '%s'", filename)
        return tree

    @keyword
    def get_locator_tree(self):
        """Return Java locator tree as list of objects.

        Mostly relevant object properties are:

            - ancestry
            - role
            - name
            - description
            - indexInParent

        :return: list of objects
        """
        return self.context_info_tree.get_search_element_tree()

    @keyword
    def print_locator_tree(self, filename: Optional[str] = None):
        """Print current Java window locator list into log and possibly
        into a file.

        :param filename: filepath to save locator tree
        :return: locator tree
        """
        search_tree = self.get_locator_tree()
        tree = "\n".join(
            [
                f"{'| ' * item.ancestry}role:{item.role} and name:{item.name} and "
                f"description:{item.description} "
                f"and indexInParent:{item.indexInParent}"
                for item in search_tree
            ]
        )
        self.logger.info(tree)
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(tree)
            self.logger.info("Locator tree written to file '%s'", filename)
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

    @keyword
    def read_table(self, locator: LocatorType, visible_only: bool = True):
        """Return Java table as list of lists (rows containing columns).

        Each cell element is represented by ``JavaElement`` class.

        :param locator: locator to match element with type of table
        :param visible_only: return all the children when this is `False`
        :return: list of lists

        Example.

        .. code:: python

            table = java.read_table(locator_table)
            for row in table:
                for cell in row:
                    if cell.role == "check box":
                        print(cell.row, cell.col, str(cell.checked))
                    else:
                        print(cell.row, cell.col, cell.name)
        """
        # Refresh the table before encapsulating it in a `JavaElement` object.
        table = self._get_matching_element(
            locator, as_java_element=True, refresh=self.ignore_callbacks
        )
        if visible_only:
            active_children = table.visible_children
        else:
            active_children = table.node.children
            # Reset the column counter when dealing with all the children this time.
            # NOTE(cmin764; 4 Oct 23): Normally, we would set `table.column_count` to
            #  `None` first, but node's all children are not having any visible
            #  coordinates (-1), thus not reliable when computing the number of columns
            #  again if we don't keep the previously set counter.
            table.set_rows_columns(active_children)
        self.logger.info("Read table: %s", table)

        column_count = table.column_count
        if not column_count:
            raise InvalidLocatorError(
                f"Locator {locator!r} does not match the 'table' element"
            )

        table_elements = []
        for index, active_child in enumerate(active_children):
            java_elem = JavaElement(
                active_child,
                scaling_factor=self.display_scale_factor,
                index=index,
                column_count=column_count,
            )
            table_elements.append(java_elem)
        table_rows = [
            table_elements[idx : idx + column_count]
            for idx in range(0, len(table_elements), column_count)
        ]
        return table_rows

    @keyword
    def close_java_window(self):
        """Close active Java window which has been accessed
        via ```Select Window`` keyword.
        """
        if not self.pid:
            raise JavaWindowNotFound()
        os.system(f"taskkill /F /T /PID {self.pid}")

    @keyword
    def list_java_windows(self):
        """List all available Java windows.

        `JavaWindow` object contains following properties:

            - Java process id (pid)
            - Java window title
            - Java window handle (hwnd)

        The pid and title can be used to get control of the
        Java process by.

        :return: list of `JavaWindow` objects

        **Python example.**

        .. code:: python

            window_list = java.list_java_windows()
            # By looping window list
            for window in window_list:
                if window.title == "my java window title":
                    logging.info("Java window found")
                    java.select_window_by_pid(window.pid)
            # Directly accessing
            if len(window_list) == 1:
                java.select_window_by_pid(window_list[0].pid)

        **Robot Framework example.**

        .. code:: robotframework

            @{window_list}=    List Java Windows
            FOR    ${window}    IN    @{window_list}
                IF    "${window.title}" == "my java window title"
                    Select Window By PID    ${window.pid}
                END
            END
            IF    len($window_list)==1
                Select Window By PID    ${window_list[0].pid}
            END
        """
        if self.jab_wrapper is None:
            self._initialize()
        window_list = self.jab_wrapper.get_windows()
        return window_list

    @keyword
    def select_window_by_title(
        self, title: str, bring_foreground: bool = True, timeout: int = 30
    ):
        """Selects Java application window as target for the automation using
        Java window title.

        :param title: application window title
        :param bring_foreground: if application is brought to foreground or not
        :param timeout: selection timeout
        """
        self._select_window(
            title=title, pid=None, bring_foreground=bring_foreground, timeout=timeout
        )

    @keyword
    def select_window_by_pid(
        self, pid: int, bring_foreground: bool = True, timeout: int = 30
    ):
        """Selects Java application window as target for the automation using
        Java process ID (pid).

        :param pid: application process id
        :param bring_foreground: if application is brought to foreground or not
        :param timeout: selection timeout
        """
        self._select_window(pid=pid, bring_foreground=bring_foreground, timeout=timeout)

    def _find_window(self, title: Optional[str] = None, pid: Optional[int] = None):
        window_found = False
        try:
            if title:
                self.pid = self.jab_wrapper.switch_window_by_title(title)
            elif pid:
                self.pid = self.jab_wrapper.switch_window_by_pid(pid)
            window_found = True
        except Exception:  # pylint: disable=broad-except
            pass
        return window_found

    def _select_window(
        self,
        title: Optional[str] = None,
        pid: Optional[int] = None,
        bring_foreground: bool = True,
        timeout: int = 30,
    ):
        if self.jab_wrapper is None:
            self._initialize()

        window_found = False
        interval = float(0.5)
        end_time = time.time() + float(timeout)
        while time.time() <= end_time:
            start = time.time()
            window_found = self._find_window(title, pid)
            if window_found:
                break
            duration = time.time() - start
            if duration < interval:
                time.sleep(interval - duration)

        if not window_found:
            if title:
                raise ValueError("Did not find window with title '%s'" % title)
            elif pid:
                raise ValueError("Did not find window with pid '%s'" % pid)
            else:
                raise ValueError(
                    "Window selection was called without 'title' or 'pid'."
                    " Can't select window."
                )

        if not self.version_printed:
            self.get_version_info()
            self.version_printed = True

        if bring_foreground:
            self._bring_window_to_foreground()

        self._application_refresh(force=True)

        return self.pid

    def _bring_window_to_foreground(self):
        # correct window identifiable by the PID
        if self.pid:
            handle = self.jab_wrapper.get_current_windows_handle()
            # pylint: disable=c-extension-no-member
            win32gui.ShowWindow(handle, win32con.SW_SHOW)
            # pylint: disable=c-extension-no-member
            win32gui.SetForegroundWindow(handle)
        else:
            self.logger.warning(
                "Window pid is unknown, can't bring to window to foreground."
            )

    @keyword
    def wait_until_element_exists(self, locator: str, timeout: int = 10):
        """Wait until element(s) matching the locator are found within
        given timeout or raises ``ElementNotFound`` exception.

        :param locator: locator to match element
        :param timeout: timeout in seconds to find element
        :return: element(s) if found
        """
        elements = None
        end_time = time.time() + float(timeout)
        while time.time() <= end_time:
            start_time = time.time()
            elements = self._find_elements(locator)
            if len(elements) > 0:
                break
            self._application_refresh()
            # sleep at least a second per iteration
            duration = time.time() - start_time
            if duration < 1.0:
                time.sleep(1.0 - duration)
        if elements is None or len(elements) == 0:
            # print element tree when result is not expected
            self.print_element_tree()
            raise ElementNotFound("Locator '%s' did not match any elements" % locator)
        return elements

    @keyword
    def refresh_element(self, locator: LocatorType, index: int = 0) -> JavaElement:
        """Refresh an element alone.

        This will ensure the latest data is available in the targeted element, thus
        gaining speed when dealing with big apps that won't require an entire global
        refresh. The obtained Java element is returned.

        :param locator: element to refresh
        :param index: target element index if multiple are returned
        :returns: the Java element found by the passed locator
        """
        elem = self._get_matching_element(locator, index, as_java_element=True)
        self.logger.info("Refreshing element: %r", elem)
        elem.node.refresh()
        return elem
