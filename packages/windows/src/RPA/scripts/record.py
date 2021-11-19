from datetime import datetime

# pylint: disable=C0415
from pynput_robocorp import mouse, keyboard

from RPA.Windows import utils


if utils.is_windows():
    import uiautomation as auto


record = False
recording_time = None
recording = []


def inspect_element(action: str = "Click", control_window: bool = True):
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

        parent_locator = _get_element_key_properties(parent_control)
        child_locator = _get_element_key_properties(control)
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
        if record:
            # skip similar locators
            # unique = True
            # for item in self.recording:
            #     if (
            #         item["top"] == top_level_control.Name
            #         and item["locator"] == locator_path
            #     ):
            #         unique = False
            #         break
            # if unique:
            recording.append(
                {
                    "type": "locator",
                    "top": top_level_control.Name,
                    "top_handle": top_level_control.NativeWindowHandle,
                    "x": top_level_control,
                    "locator": locator_path,
                }
            )
    return output


def _get_element_key_properties(element, regex_limit=300):
    automation_id = element.AutomationId
    element_name = element.Name
    snippet = ""
    if element_name and len(element_name) > 0:
        snippet = f"name:'{element_name.strip()}'"
    elif automation_id and not utils.is_integer(automation_id):
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


def stop_listeners():
    mouse.Listener.stop()
    keyboard.Listener.stop()


def start_recording():
    """Start recording mouse clicks.

    Can be stopped by pressing keyboard ``ESC``.
    """
    # TODO. Add examples
    global record, recording  # pylint: disable=W0603
    record = True
    recording = []

    def on_click(x, y, button, pressed):  # pylint: disable=W0613
        global recording, recording_time  # pylint: disable=W0602
        if pressed:
            inspect_time = datetime.now()
            if recording_time:
                timediff = inspect_time - recording_time
                seconds = max(round(float(timediff.microseconds / 1000000.0), 1), 0.1)
                recording.append({"type": "sleep", "value": seconds})
            recording_time = inspect_time
            inspect_element()

    def on_release(key):
        if key == keyboard.Key.esc:
            return False
        return True

    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()
    with keyboard.Listener(on_release=on_release) as key_listener:
        print("keyboard and mouse listeners started")
        key_listener.join()
    mouse_listener.stop()
    the_recording = get_recording()
    print(the_recording)


def get_recording(sleeps=False):
    """Get list of recorded steps.

    :param sleeps: set False to exclude recording sleeps
    """
    # TODO. atm will always use CLICK
    # TODO. Add examples
    global recording  # pylint: disable=W0602
    output = []
    top = None
    action_name = "Click"
    for item in recording:
        if sleeps and item["type"] == "sleep":
            output.append(f"Sleep   {item['value']}s")
        if (
            item["type"] == "locator"
            and not top
            or "top" in item.keys()
            and item["top"] != top
        ):
            output.append(
                f"Control Window    {item['top']}  # Handle: {item['top_handle']}"
            )
            top = item["top"]
        if item["type"] == "locator":
            output.append(f"{action_name}   {item['locator']}")

    result = "\n".join(output)
    header = (
        f"\n{'-'*80}"
        "\nCOPY & PASTE BELOW CODE INTO *** Tasks *** or *** Keywords ***"
        f"\n{'-'*80}\n\n"
    )
    footer = f"\n\n{'-'*80}"
    return f"{header}{result}{footer}"


if __name__ == "__main__":
    start_recording()
