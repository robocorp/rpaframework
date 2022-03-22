from typing import Dict, List, Optional, Union

from RPA.core.windows.helpers import IS_WINDOWS, is_numeric

if IS_WINDOWS:
    import uiautomation as auto

    RecordElement = Dict[str, Optional[Union[float, str, auto.Control]]]


class ElementInspector:
    """Element locator inspector"""

    @classmethod
    def inspect_element(
        cls,
        action: str = "Click",
        control_window: bool = True,
        recording: Optional[List["RecordElement"]] = None,
        verbose: bool = False,
    ):
        """Inspect Windows element under mouse pointer.

        :param action: Action attached to the locator.
        :param control_window: Include relevant ``Control Window  ...`` statement or
            not.
        :param recording: Where to store records.
        :param verbose: Show exhaustive locators if `True`, otherwise just simple ones.
        """
        # TODO: Python syntax support too instead of just RF.
        output = []
        with auto.UIAutomationInitializerInThread(debug=False):
            control = auto.ControlFromCursor()
            parent_control = control.GetParentControl()
            try:
                top_level_control = control.GetTopLevelControl()
            except AttributeError:
                top_level_control = None
                top_level_name = top_level_handle = "N/A"
            else:
                top_level_name = top_level_control.Name
                top_level_handle = top_level_control.NativeWindowHandle

            parent_locator = (
                cls._get_element_key_properties(parent_control, verbose=verbose)
                or "N/A"
            )
            child_locator = (
                cls._get_element_key_properties(control, verbose=verbose) or "N/A"
            )
            locator_path = f"{parent_locator} > {child_locator}"
            if "name:" in child_locator or "id:" in child_locator:
                locator_path = child_locator
            if control_window:
                output.append(f"Control Window  {top_level_name}")
            if action:
                output.append(f"{action}  {locator_path}")
            else:
                output.append(locator_path)

            if recording is not None:
                recording.append(
                    {
                        "type": "locator",
                        "top": top_level_name,
                        "top_handle": top_level_handle,
                        "x": top_level_control,
                        "locator": locator_path,
                        "name": parent_control.Name if parent_control else None,
                        "control": parent_control,
                    }
                )

        return output

    @staticmethod
    def _get_element_key_properties(element, *, verbose: bool, regex_limit: int = 300):
        if not element:
            print("Got null element!")
            return None

        name = element.Name.strip()
        automation_id = element.AutomationId
        control_type = element.ControlTypeName.strip()
        class_name = element.ClassName.strip()
        locators = []
        if len(name) > 0:
            name_property = "name:"
            if len(name) > regex_limit:
                name_property = "regex:"
                name = name[:regex_limit].strip()
            if " " in name:
                name = f"'{name}'"
            locators.append(f"{name_property}{name}")
        if automation_id and not is_numeric(automation_id):
            locators.append(f"id:{automation_id}")
        if len(control_type) > 0:
            locators.append(f"type:{control_type}")
        if len(class_name) > 0:
            locators.append(f"class:{class_name}")
        if locators:
            if not verbose:
                locators = locators[:1]
            return " and ".join(locators)

        print("Was unable to construct locator for the control!")
        return None
