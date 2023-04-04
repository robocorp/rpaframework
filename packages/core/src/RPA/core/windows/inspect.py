import itertools
from pathlib import Path
from typing import Dict, List, Optional, Union

from RPA.core.windows import WindowsElements
from RPA.core.windows.elements import StructureType
from RPA.core.windows.helpers import IS_WINDOWS
from RPA.core.windows.locators import MatchObject, WindowsElement
from RPA.core.windows.window import WindowMethods

if IS_WINDOWS:
    import uiautomation as auto
    from uiautomation import Control

    RecordElement = Dict[str, Optional[Union[float, str, Control, List[str]]]]


class ElementInspector:
    """Element locator inspector"""

    def __int__(self):
        # Lazily loaded with verbose mode on for printing the tree and returning the
        #  structure.
        self._windows_elements: Optional[WindowsElements] = None

    @property
    def windows_elements(self) -> WindowsElements:
        if not self._windows_elements:
            self._windows_elements = WindowsElements()
        return self._windows_elements

    def inspect_element(
        self,
        recording: List["RecordElement"],
        verbose: bool = False,
    ) -> None:
        """Inspect Windows element under mouse pointer.

        :param recording: Store the dict records under this list.
        :param verbose: Show exhaustive locators if `True`, otherwise just simple ones.
            Switching this on will make recording slower as it is refreshing the
            element tree with each click in order to provide their path strategy as
            well.
        """
        # TODO(cmin764): Support Python syntax as well. (currently just RF keywords)
        with auto.UIAutomationInitializerInThread(debug=False):
            control = auto.ControlFromCursor()
            parent_control = control.GetParentControl()
            exec_path = ""
            try:
                top_level_control = control.GetTopLevelControl()
            except AttributeError:
                top_level_control = None
                top_level_handle = "N/A"
            else:
                top_level_handle = top_level_control.NativeWindowHandle
                try:
                    exec_path = WindowMethods.get_fullpath(top_level_control.ProcessId)
                except Exception:  # pylint: disable=broad-except
                    pass

            top_properties = self._get_element_key_properties(
                top_level_control, verbose=verbose
            )
            parent_properties = self._get_element_key_properties(
                parent_control, verbose=verbose
            )
            child_properties = self._get_element_key_properties(
                control, top_level_control=top_level_control, verbose=verbose
            )

            top_locator = " and ".join(top_properties) or "N/A"
            parent_locator = " and ".join(parent_properties) or "N/A"
            child_locator = " and ".join(child_properties) or "N/A"
            locator_path = f"{parent_locator} > {child_locator}"
            if "name:" in child_locator or "id:" in child_locator:
                locator_path = child_locator

            recording.append(
                {
                    "type": "locator",
                    "exec_path": exec_path,
                    "exec": Path(exec_path).name,
                    "top": top_locator,
                    "top_handle": top_level_handle,
                    "x": top_level_control,
                    "locator": locator_path,
                    "top_props": top_properties,
                    "parent_props": parent_properties,
                    "props": child_properties,
                    "name": parent_control.Name if parent_control else None,
                    "control": parent_control,
                }
            )

    def _filter_structure(
        self,
        structure: StructureType,
        *,
        control_type: str,
        class_name: str,
        automation_id: str,
        name: str,
    ) -> Dict[str, List[WindowsElement]]:
        elements: Dict[str, List[WindowsElement]] = {}

        for element in itertools.chain(*structure.values()):
            good = (
                control_type
                and control_type == element.control_type
                or class_name
                and class_name == element.class_name
            )
            if not good:
                continue

            priority = {
                "automation_id": automation_id,
                "name": name,
            }
            for attr, value in priority.items():
                if value and value == getattr(element, attr):
                    elements.setdefault(attr, []).append(element)

        return elements

    def _get_element_key_properties(
        self,
        control: Optional["Control"],
        *,
        top_level_control: Optional["Control"],
        verbose: bool,
        regex_limit: int = 300,
    ) -> List[str]:
        if not control:
            print("Got null control!")
            return []

        name = control.Name.strip()
        automation_id = control.AutomationId
        control_type = control.ControlTypeName.strip()
        class_name = control.ClassName.strip()
        locators = []
        if len(name) > 0:
            name_property = "name:"
            if len(name) > regex_limit:
                name_property = "regex:"
                name = name[:regex_limit].strip()
            if " " in name:
                q = MatchObject.QUOTE
                name = f"{q}{name}{q}"
            locators.append(f"{name_property}{name}")
        if automation_id and not str(automation_id).isnumeric():
            locators.append(f"id:{automation_id}")
        if len(control_type) > 0:
            locators.append(f"type:{control_type}")
        if len(class_name) > 0:
            locators.append(f"class:{class_name}")

        # Add the `path:` strategy as well with verbose recordings. (useful when you
        #  can't rely on Automation IDs nor names)
        if verbose and top_level_control:
            path: Optional[str] = None
            structure = self.windows_elements.print_tree(
                top_level_control, return_structure=True
            )
            elems_dict = self._filter_structure(
                structure,
                control_type=control_type,
                class_name=class_name,
                automation_id=automation_id,
                name=name,
            )
            priority = ["automation_id", "name"]
            for prio in priority:
                elems = elems_dict.get(prio)
                if elems:
                    match = elems[0]
                    path = match.locator.rsplit(MatchObject.TREE_SEP, 1)[-1]
                    break
            if path:
                locators.append(path)

        if locators:
            if not verbose:
                locators = locators[:1]
            return locators

        print("Was unable to construct locator for the control!")
        return []
