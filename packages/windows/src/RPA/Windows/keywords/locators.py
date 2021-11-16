from dataclasses import dataclass, field
import re
from typing import List
from RPA.Windows.keywords import keyword, LibraryContext, WindowControlError
from RPA.Windows import utils

if utils.is_windows():
    import uiautomation as auto
    from uiautomation.uiautomation import Control


WINDOWS_LOCATOR_STRATEGIES = {
    "automationid": "AutomationId",
    "id": "AutomationId",
    "class": "ClassName",
    "control": "ControlType",
    "depth": "depth",
    "name": "Name",
    "regex": "RegexName",
    "subname": "SubName",
    "type": "ControlType",
    "index": "foundIndex",
    "offset": "offset",
    "desktop": "desktop",
    "process": "process",
    "executable": "executable",
}


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
        regex = rf"({':|'.join(WINDOWS_LOCATOR_STRATEGIES.keys())}:|or|and)('{{1}}(.+)'{{1}})|(\S+)?"  # noqa: E501
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
        else:
            try:
                strategy, value = part_text.split(":", 1)
            except ValueError:
                strategy = None
                default_value.append(part_text)
            # self.logger.info("STRATEGY: %s VALUE: %s" % (strategy, value))
            if strategy:
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
        elif strategy == "foundIndex":
            self.match_index = int(value.strip())
            value = int(value.strip())
            self.locators.append([strategy, value, level])
        elif strategy == "ControlType":
            value = value if value.endswith("Control") else f"{value}Control"
            self.locators.append([strategy, value, level])
        else:
            self.locators.append([strategy, value, level])
        if (
            strategy in ["class", "class_name", "friendly", "friendly_class_name"]
            and value.lower() not in self._classes
        ):
            self._classes.append(value.lower())

    @property
    def classes(self) -> List:
        uniques = []
        for c in self._classes:
            if c not in uniques:
                uniques.append(c)
        return uniques


class LocatorKeywords(LibraryContext):
    """Keywords for handling Windows locators"""

    def _get_control_with_locator_part(
        self, locator, search_depth, root_control=None
    ) -> Control:
        control = None

        match_object = MatchObject()
        mo = match_object.parse_locator(locator)
        self.ctx.logger.info("locator '%s' to match object: %s" % (locator, mo))
        search_params = {}
        for loc in mo.locators:
            search_params[loc[0]] = loc[1]
        offset = search_params.pop("offset", None)
        if "executable" in search_params.keys():
            root_control = auto.GetRootControl()
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
            control = Control(**search_params, searchDepth=search_depth)
            new_control = Control.CreateControlFromControl(control)
            new_control.robocorp_click_offset = offset
            return new_control
        if "desktop" in search_params.keys():
            root_control = auto
            search_params.pop("desktop")
        if "ControlType" in search_params.keys():
            control_type = search_params.pop("ControlType")
            control = getattr(root_control, control_type)
            new_control = control(**search_params, searchDepth=search_depth)
            new_control.robocorp_click_offset = offset
            return new_control

        control = getattr(root_control, "Control")

        new_control = control(**search_params, searchDepth=search_depth)
        new_control.robocorp_click_offset = offset
        return new_control

    @keyword
    def get_control(
        self, locator: str, search_depth: int = 8, root_control: Control = None
    ) -> Control:
        """Get Control object defined by the locator.

        :param locator: locator as a string
        :param search_depth: how deep the Control search will traverse (default 8)
        :param root_control: can be used to restrict Control search into
         a specific Control object
        """
        self.logger.info("Locator '%s' into control", locator)
        locators = locator.split(" > ")
        root_control = root_control or self.ctx.window or auto
        control = None
        for loc in locators:
            self.logger.info("Root control: '%s'" % root_control)
            control = self._get_control_with_locator_part(
                loc, search_depth, root_control
            )
            root_control = control
        self.logger.info("Returning control: '%s'", control)
        return control
