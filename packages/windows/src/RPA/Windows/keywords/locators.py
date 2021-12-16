from dataclasses import dataclass, field
import re
from typing import List, Union
from RPA.Windows.keywords import (
    ElementNotFound,
    keyword,
    LibraryContext,
    WindowControlError,
)
from RPA.Windows import utils

if utils.is_windows():
    import uiautomation as auto
    from uiautomation.uiautomation import Control

DEFAULT_SEARCH_TIMEOUT = auto.uiautomation.TIME_OUT_SECOND

WINDOWS_LOCATOR_STRATEGIES = {
    "automationid": "AutomationId",
    "id": "AutomationId",
    "class": "ClassName",
    "control": "ControlType",
    "depth": "searchDepth",
    "name": "Name",
    "regex": "RegexName",
    "subname": "SubName",
    "type": "ControlType",
    "index": "foundIndex",
    "offset": "offset",
    "desktop": "desktop",
    "process": "process",
    "handle": "handle",
    "executable": "executable",
}


@dataclass
class WindowsElement:
    """Represent Control as dataclass"""

    item: Control
    locator: str = None
    name: str = ""
    automation_id: str = ""
    control_type: str = ""
    class_name: str = ""
    left: int = -1
    right: int = -1
    top: int = -1
    bottom: int = -1
    width: int = -1
    height: int = -1
    xcenter: int = -1
    ycenter: int = -1

    def __init__(self, item, locator):
        self.item = item
        self.locator = locator
        self.name = item.Name
        self.automation_id = item.AutomationId
        self.control_type = item.ControlTypeName
        self.class_name = item.ClassName
        rect = item.BoundingRectangle
        self.left = rect.left if rect else -1
        self.right = rect.right if rect else -1
        self.top = rect.top if rect else -1
        self.bottom = rect.bottom if rect else -1
        self.width = rect.width() if rect else -1
        self.height = rect.height() if rect else -1
        self.xcenter = rect.xcenter() if rect else -1
        self.ycenter = rect.ycenter() if rect else -1


@dataclass
class MatchObject:
    """Represents all locator parts as object properties"""

    match_type: str = field(default="all")
    match_index: int = None
    locators: List = field(default_factory=list)
    _classes: List = field(default_factory=list)
    regex: str = None
    regex_field: str = None
    max_level: int = 0

    def parse_locator(self, locator: str):
        locator_tree = [loc.strip() for loc in locator.split(">")]
        # self.logger.warning(locator_tree)
        regex = rf"({':|'.join(WINDOWS_LOCATOR_STRATEGIES.keys())}:|or|and|desktop)('{{1}}(.+)'{{1}})|(\S+)?"  # noqa: E501
        match_object = MatchObject()
        for level, branch in enumerate(locator_tree):
            parts = re.finditer(regex, branch, re.IGNORECASE)

            default_value = []
            strategy = None

            for part in parts:
                self.handle_locator_part(
                    level, part, match_object, default_value, strategy
                )
            if not strategy and len(default_value) > 0:
                match_object.add_locator("Name", " ".join(default_value), level)
        if len(match_object.locators) == 0:
            match_object.add_locator("Name", locator)
        return match_object

    def handle_locator_part(self, level, part, match_object, default_value, strategy):
        part_text = part.group(0)
        if len(part_text.strip()) == 0:
            return
        if part_text == "or":
            match_object.match_type = "any"
        elif part_text == "and":
            pass
        elif part_text == "desktop":
            match_object.add_locator("desktop", "desktop", level)
        else:
            try:
                strategy, value = part_text.split(":", 1)
            except ValueError:
                strategy = None
                default_value.append(part_text)
            # self.logger.info("STRATEGY: %s VALUE: %s" % (strategy, value))
            if strategy and strategy in WINDOWS_LOCATOR_STRATEGIES:
                if len(default_value) > 0:
                    match_object.add_locator("Name", " ".join(default_value))
                    default_value = []
                windows_locator_strategy = WINDOWS_LOCATOR_STRATEGIES[strategy]
                match_object.add_locator(windows_locator_strategy, value, level)

    def add_locator(self, strategy, value, level=0) -> None:
        if not value:
            return
        self.max_level = max(self.max_level, level)
        value = value.replace("'", "").strip()
        if strategy == "regex":
            self.regex = value
        elif strategy == "regex_field":
            self.regex_field = value
        elif strategy in ["foundIndex", "searchDepth", "handle"]:
            value = int(value.strip())
            self.locators.append([strategy, value, level])  # pylint: disable=no-member
        elif strategy == "ControlType":
            value = value if value.endswith("Control") else f"{value}Control"
            self.locators.append([strategy, value, level])  # pylint: disable=no-member
        else:
            self.locators.append([strategy, value, level])  # pylint: disable=no-member
        if (
            strategy
            in [
                "class",
                "class_name",
                "friendly",
                "friendly_class_name",
            ]  # pylint: disable=unsupported-membership-test
            and value.lower() not in self._classes
        ):
            self._classes.append(value.lower())  # pylint: disable=no-member

    @property
    def classes(self) -> List:
        uniques = []
        for c in self._classes:  # pylint: disable=not-an-iterable
            if c not in uniques:
                uniques.append(c)
        return uniques


class LocatorKeywords(LibraryContext):
    """Keywords for handling Windows locators"""

    def _get_element_with_locator_part(
        self, locator, search_depth, root_element=None
    ) -> Control:
        # TODO. refactor code
        element = None

        match_object = MatchObject()
        mo = match_object.parse_locator(locator)
        self.ctx.logger.info("locator '%s' to match element: %s" % (locator, mo))
        search_params = {}
        for loc in mo.locators:  # pylint: disable=not-an-iterable
            search_params[loc[0]] = loc[1]
        offset = search_params.pop("offset", None)
        if "searchDepth" not in search_params.keys():
            search_params["searchDepth"] = search_depth
        if "executable" in search_params.keys():
            root_element = auto.GetRootControl()
            search_params.pop("ControlType")
            executable = search_params.pop("executable")
            window_list = self.ctx.list_windows()
            matches = [w for w in window_list if w["name"] == executable]
            if not matches:
                raise WindowControlError(
                    "Could not locate window with executable '%s'" % executable
                )
            elif len(matches) > 1:
                raise WindowControlError(
                    "Found more than one window with executable '%s'" % executable
                )
            self.logger.info(
                "Found process with window title: '%s'" % matches[0]["title"]
            )
            search_params["Name"] = matches[0]["title"]
            element = Control(**search_params)
            new_element = Control.CreateControlFromControl(element)
            new_element.robocorp_click_offset = offset
            return new_element
        elif "handle" in search_params.keys():
            root_element = auto.GetRootControl()
            search_params.pop("ControlType")
            handle = search_params.pop("handle")
            window_list = self.ctx.list_windows()
            matches = [w for w in window_list if w["handle"] == handle]
            if not matches:
                raise WindowControlError(
                    "Could not locate window with handle '%s'" % handle
                )
            elif len(matches) > 1:
                raise WindowControlError(
                    "Found more than one window with handle '%s'" % handle
                )
            self.logger.info(
                "Found process with window title: '%s'" % matches[0]["title"]
            )
            search_params["Name"] = matches[0]["title"]
            element = Control(**search_params)
            new_element = Control.CreateControlFromControl(element)
            new_element.robocorp_click_offset = offset
            return new_element

        if "desktop" in search_params.keys():
            root_element = auto.GetRootControl()
            search_params.pop("desktop")
            return Control.CreateControlFromControl(root_element)

        control_type = search_params.pop("ControlType", "Control")
        element = getattr(root_element, control_type)
        new_element = element(**search_params)
        new_element = Control.CreateControlFromControl(new_element)
        new_element.robocorp_click_offset = offset
        return new_element

    @keyword
    def get_element(
        self,
        locator: Union[str, WindowsElement] = None,
        search_depth: int = 8,
        root_element: WindowsElement = None,
        timeout: float = None,
    ) -> WindowsElement:
        """Get Control element defined by the locator.

        Returned element can be used instead of a locator string for
        keywords accepting `locator`.

        Keyword ``Get Attribute`` can be used to read element attribute values.

        If `locator` is *None* then returned `element` will be in order of preference:

            1. anchor element if that has been set with `Set Anchor`
            2. current active window if that has been set with `Control Window`
            3. final option is the `Desktop`

        :param locator: locator as a string or as a element
        :param search_depth: how deep the element search will traverse (default 8)
        :param root_element: can be used to set search root element
        :param timeout: float value in seconds, see keyword
         ``Set Global Timeout``
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            ${element}=    Get Element    name:'Text Editor*
            Set Value   ${element}  note to myself
        """
        # TODO. Add examples
        self.logger.info("Locator '%s' into element", locator)
        if timeout:
            auto.SetGlobalSearchTimeout(timeout)
        self.logger.info(
            "Locator timeout set to: %s" % auto.uiautomation.TIME_OUT_SECOND
        )
        if not locator:
            element = (
                self.ctx.anchor_element
                or self.ctx.window
                or WindowsElement(auto.GetRootControl(), None)
            )
        elif isinstance(locator, str):
            try:
                element = self.get_element_by_locator_string(
                    locator, search_depth, root_element
                )
            finally:
                auto.SetGlobalSearchTimeout(self.ctx.global_timeout)
        else:
            element = locator
        if hasattr(element.item, "Exists"):
            element.item.Exists(maxSearchSeconds=timeout)
        if not element:
            raise ElementNotFound("Unable to get element with '%s'" % locator)
        self.logger.info("Returning element: '%s'", element)
        return element

    def get_element_by_locator_string(self, locator, search_depth, root_element):
        locators = locator.split(" > ")
        anchor = self.ctx.anchor_element.item if self.ctx.anchor_element else None
        root = root_element.item if root_element else None
        window = self.ctx.window.item if self.ctx.window else None
        root_element = root or anchor or window or auto.GetRootControl()
        self.logger.debug("argument root_element = %s" % root)
        self.logger.debug("active anchor_element = %s" % anchor)
        self.logger.debug("active window = %s" % window)
        self.logger.debug("resulting root_element = %s" % root_element)
        element = None
        try:
            for loc in locators:
                self.logger.info("Root element: '%s'" % root_element)
                element = self._get_element_with_locator_part(
                    loc, search_depth, root_element
                )
                root_element = element
        except LookupError as err:
            raise ElementNotFound(
                "Element not found with locator %s" % locator
            ) from err
        return WindowsElement(element, locator)

    @keyword
    def get_elements(
        self,
        locator: Union[str, WindowsElement],
        search_depth: int = 8,
        root_element: WindowsElement = None,
        timeout: float = None,
    ) -> List:
        """Get list of elements matching locator.

        :param locator: locator as a string or as a element
        :param search_depth: how deep the element search will traverse (default 8)
        :param root_element: can be used to set search root element
        :param timeout: float value in seconds, see keyword
         ``Set Global Timeout``
        :return: list of WindowsElement objects

        Example:

        .. code-block:: robotframework

            Set Anchor    id:DataGrid
            ${elements}=    Get Elements    type:HeaderItem
            FOR    ${el}    IN    @{elements}
                Log To Console    ${el.Name}
            END
        """
        if timeout:
            auto.SetGlobalSearchTimeout(timeout)
        elements = []
        window_element = self.get_element(locator, search_depth, root_element, timeout)
        elements.append(window_element)
        try:
            while True:
                # TODO. the sibling needs to match the original locator
                next_element = window_element.item.GetNextSiblingControl()
                if next_element:
                    window_element = WindowsElement(next_element, locator)
                    elements.append(window_element)
                else:
                    break
        finally:
            auto.SetGlobalSearchTimeout(self.ctx.global_timeout)
        return elements
