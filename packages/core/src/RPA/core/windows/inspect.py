from typing import List

from .helpers import IS_WINDOWS, is_numeric

if IS_WINDOWS:
    import uiautomation as auto


class ElementInspector:
    """Element locator inspector"""

    @classmethod
    def inspect_element(
        cls,
        action: str = "Click",
        control_window: bool = True,
        recording: List = None,
    ):
        """Inspect Windows element under mouse pointer

        :param action: which action is attached to locator
        :param control_window: set False to not include ``Control Window`` keyword
        """
        # TODO. Add Python syntax
        # TODO. Add examples
        output = []
        with auto.UIAutomationInitializerInThread(debug=False):
            control = auto.ControlFromCursor()
            parent_control = control.GetParentControl()
            top_level_control = control.GetTopLevelControl()

            parent_locator = cls._get_element_key_properties(parent_control)
            child_locator = cls._get_element_key_properties(control)
            locator_path = f"{parent_locator} > {child_locator}"
            if "name:" in child_locator:
                locator_path = child_locator
            elif "id:" in child_locator:
                locator_path = child_locator
            if control_window:
                output.append(f"Control Window  {top_level_control.Name}")
            if action:
                output.append(f"{action}  {locator_path}")
            else:
                output.append(locator_path)
            if recording is not None:
                recording.append(
                    {
                        "type": "locator",
                        "top": top_level_control.Name,
                        "top_handle": top_level_control.NativeWindowHandle,
                        "x": top_level_control,
                        "locator": locator_path,
                        "name": parent_control.Name,
                        "control": parent_control,
                    }
                )
        return output

    @classmethod
    def _get_element_key_properties(cls, element, regex_limit=300):
        automation_id = element.AutomationId
        element_name = element.Name
        snippet = ""
        if element_name and len(element_name) > 0:
            snippet = f"name:'{element_name.strip()}'"
        elif automation_id and not is_numeric(automation_id):
            snippet = f"id:{automation_id}"
        else:
            control_type = element.ControlTypeName.strip()
            class_name = element.ClassName.strip()
            name = element.Name.strip()
            name_property = "name:"
            if len(name) > regex_limit:
                name_property = "regex:"
                name = name[:regex_limit].strip()
            locators = []
            if len(control_type) > 0:
                locators.append(f"type:{control_type}")
            if len(class_name) > 0:
                locators.append(f"class:{class_name}")
            if len(name) > 0 and " " in name:
                locators.append(f"{name_property}'{name}'")
            elif len(name) > 0:
                locators.append(f"{name_property}{name}")
            if not locators:
                print("Was unable to construct locator for the control")
                return None
            else:
                snippet = " and ".join(locators)
        return snippet
