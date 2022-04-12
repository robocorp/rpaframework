import functools
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple, Union

from RPA.core.locators import LocatorsDatabase, WindowsLocator
from RPA.core.vendor.deco import keyword as method
from RPA.core.windows.context import (
    ElementNotFound,
    WindowsContext,
    WindowControlError,
    with_timeout,
)
from RPA.core.windows.helpers import IS_WINDOWS

if IS_WINDOWS:
    import uiautomation as auto
    from uiautomation.uiautomation import Control


Locator = Union["WindowsElement", str]


@dataclass
class WindowsElement:
    """Represent Control as dataclass"""

    _WINDOW_SIBLING_COMPARE = {
        # <locator_strategy>: <element_attribute>
        "name": "name",  # this works for "subname" as well
        "class": "class_name",
        "control": "control_type",
        "id": "automation_id",
    }

    item: "Control"
    locator: Optional[Locator] = None
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

    def __init__(self, item: "Control", locator: Optional[Locator]):
        self.item: "Control" = item
        self.locator: Optional[Locator] = locator
        self.name = item.Name
        self.automation_id = item.AutomationId
        self.control_type = item.ControlTypeName
        self.class_name = item.ClassName
        # If there's no rectangle, then all coords are defaulting to -1.
        rect = item.BoundingRectangle
        if rect:
            self.left = rect.left
            self.right = rect.right
            self.top = rect.top
            self.bottom = rect.bottom
            self.width = rect.width()
            self.height = rect.height()
            self.xcenter = rect.xcenter()
            self.ycenter = rect.ycenter()

    def is_sibling(self, win_elem: "WindowsElement") -> bool:
        """Returns `True` if the provided window element is a sibling."""
        locator: Optional[Locator] = win_elem.locator
        while locator:
            if isinstance(locator, WindowsElement):
                locator = locator.locator
            else:  # reached a string
                break
        else:
            return True  # nothing to check here, can be considered sibling

        # FIXME(cmin764): Implement missing strategies like "regex".
        cmp_attrs = []
        for strategy, attr in self._WINDOW_SIBLING_COMPARE.items():
            if f"{strategy}:" in locator:
                cmp_attrs.append(attr)
        checks = (getattr(self, attr) == getattr(win_elem, attr) for attr in cmp_attrs)
        return all(checks)


@dataclass
class MatchObject:
    """Represents all locator parts as object properties"""

    _WINDOWS_LOCATOR_STRATEGIES = {
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
    _LOCATOR_REGEX = re.compile(
        rf"({':|'.join(_WINDOWS_LOCATOR_STRATEGIES)}:|or|and|desktop)"
        r"('{{1}}(.+)'{{1}})|(\S+)?",
        re.IGNORECASE
    )

    match_type: str = field(default="all")
    match_index: int = None
    locators: List[Tuple] = field(default_factory=list)
    _classes: Set[str] = field(default_factory=set)
    regex: str = None
    regex_field: str = None
    max_level: int = 0

    @classmethod
    def parse_locator(cls, locator: str) -> "MatchObject":
        match_object = MatchObject()
        locator_tree = [loc.strip() for loc in locator.split(">")]
        for level, branch in enumerate(locator_tree):
            default_values = []
            for part in cls._LOCATOR_REGEX.finditer(branch):
                match_object.handle_locator_part(level, part, default_values)
            if len(default_values) > 0:
                match_object.add_locator("Name", " ".join(default_values), level=level)
        if not match_object.locators:
            match_object.add_locator("Name", locator)
        return match_object

    def handle_locator_part(self, level, part, default_values) -> None:
        part_text = part.group(0).strip()
        if not part_text:
            return

        add_locator = functools.partial(self.add_locator, level=level)

        if part_text in ("and", "or", "desktop"):
            # NOTE(cmin764): Only "and" is supported at the moment. (`match_type` is
            #  ignored and spaces are treated as "and"s)
            if part_text == "and":
                self.match_type = "all"
            elif part_text == "or":
                self.match_type = "any"
            elif part_text == "desktop":
                add_locator("desktop", "desktop")
            return

        try:
            strategy, value = part_text.split(":", 1)
        except ValueError:
            strategy = value = None
            default_values.append(part_text)
        if strategy and strategy in self._WINDOWS_LOCATOR_STRATEGIES:
            if len(default_values) > 0:
                add_locator("Name", " ".join(default_values))
                default_values.clear()
            windows_locator_strategy = self._WINDOWS_LOCATOR_STRATEGIES[strategy]
            add_locator(windows_locator_strategy, value)

    def add_locator(self, strategy, value, level=0) -> None:
        value = value.replace("'", "").strip()
        if not value:
            return

        self.max_level = max(self.max_level, level)

        add_locator = True
        if strategy == "regex":
            self.regex = value
            add_locator = False
        elif strategy == "regex_field":
            self.regex_field = value
            add_locator = False
        elif strategy in ("foundIndex", "searchDepth", "handle"):
            value = int(value)
        elif strategy == "ControlType":
            value = value if value.endswith("Control") else f"{value}Control"
        elif strategy in ("class", "class_name", "friendly", "friendly_class_name"):
            self._classes.add(value.lower())  # pylint: disable=no-member
        if add_locator:
            self.locators.append((strategy, value, level))  # pylint: disable=no-member

    @property
    def classes(self) -> List[str]:
        return list(self._classes)


class LocatorMethods(WindowsContext):
    """Keywords for finding Windows GUI elements"""

    def __init__(self, ctx, locators_path: Optional[str] = None):
        self._locators_path = locators_path
        super().__init__(ctx)

    def _get_element_with_locator_part(
        self, locator, search_depth, root_element
    ) -> "Control":
        match_object = MatchObject()
        mo = match_object.parse_locator(locator)
        self.logger.info("locator '%s' to match element: %s", locator, mo)
        search_params = {}
        for loc in mo.locators:  # pylint: disable=not-an-iterable
            search_params[loc[0]] = loc[1]
        offset = search_params.pop("offset", None)
        if "searchDepth" not in search_params:
            search_params["searchDepth"] = search_depth

        if "executable" in search_params:
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
                "Found process with window title: '%s'", matches[0]["title"]
            )
            search_params["Name"] = matches[0]["title"]
            element = Control(**search_params)
            new_element = Control.CreateControlFromControl(element)
            new_element.robocorp_click_offset = offset
            return new_element

        if "handle" in search_params:
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
                "Found process with window title: '%s'", matches[0]["title"]
            )
            search_params["Name"] = matches[0]["title"]
            element = Control(**search_params)
            new_element = Control.CreateControlFromControl(element)
            new_element.robocorp_click_offset = offset
            return new_element

        if "desktop" in search_params:
            root_element = auto.GetRootControl()
            search_params.pop("desktop")
            return Control.CreateControlFromControl(root_element)

        control_type = search_params.pop("ControlType", "Control")
        element = getattr(root_element, control_type)
        new_element = element(**search_params)
        new_element = Control.CreateControlFromControl(new_element)
        new_element.robocorp_click_offset = offset
        return new_element

    def _load_by_alias(self, criteria: str) -> str:
        try:
            locator = LocatorsDatabase.load_by_name(criteria, self._locators_path)
            if isinstance(locator, WindowsLocator):
                return locator.value
        except ValueError:
            # How to check if locator check should be done as inspector
            # locators are just strings?
            pass
        return criteria

    @method
    @with_timeout
    def get_element(
        self,
        locator: Optional[Locator] = None,
        search_depth: int = 8,
        root_element: Optional[WindowsElement] = None,
        timeout: Optional[float] = None,  # pylint: disable=unused-argument
    ) -> WindowsElement:
        if isinstance(locator, str):
            locator = self._load_by_alias(locator)
        self.logger.info("Getting element with locator: %s", locator)
        if not locator:
            element = (
                self.ctx.anchor_element
                or self.ctx.window_element
                or WindowsElement(auto.GetRootControl(), None)
            )
        elif isinstance(locator, str):
            element = self._get_element_by_locator_string(
                locator, search_depth, root_element
            )
        else:
            element = locator
        if self._window_or_none(element) is None:
            raise ElementNotFound(f"Unable to get element with '{locator}'")
        self.logger.info("Returning element: %s", element)
        return element

    def _get_element_by_locator_string(self, locator, search_depth, root_element):
        root = root_element.item if self._window_or_none(root_element) else None
        anchor = self.anchor.item if self.anchor else None
        window = self.window.item if self.window else None
        self.logger.debug("argument root = %s", root)
        self.logger.debug("active anchor = %s", anchor)
        self.logger.debug("active window = %s", window)
        root_result = root or anchor or window or auto.GetRootControl()
        self.logger.debug("resulting root = %s", root_result)
        element = None

        locators = locator.split(" > ")
        try:
            for loc in locators:
                self.logger.info("Root element: '%s'", root_result)
                element = self._get_element_with_locator_part(
                    loc, search_depth, root_result
                )
                root_result = element
        except LookupError as err:
            raise ElementNotFound(f"Element not found with locator {locator}") from err

        return WindowsElement(element, locator)
