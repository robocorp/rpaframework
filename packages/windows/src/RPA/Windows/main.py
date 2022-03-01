from datetime import datetime

import fire
from pynput_robocorp import mouse, keyboard  # pylint: disable=C0415

from RPA.Windows import utils


if utils.IS_WINDOWS:
    import uiautomation as auto


record = False
recording_time = None
recording = []


def inspect_element(verbose: bool, action: str = "Click", control_window: bool = True):
    """Inspect Windows element under mouse pointer.

    :param verbose: Show exhaustive locators if `True`, otherwise just simple ones.
    :param action: Action attached to the locator.
    :param control_window: Include relevant ``Control Window  ...`` statement or not.
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
            _get_element_key_properties(parent_control, verbose=verbose) or "N/A"
        )
        child_locator = _get_element_key_properties(control, verbose=verbose) or "N/A"
        locator_path = f"{parent_locator} > {child_locator}"
        if "name:" in child_locator or "id:" in child_locator:
            locator_path = child_locator
        if control_window:
            output.append(f"Control Window  {top_level_name}")
        if action:
            output.append(f"{action}  {locator_path}")
        else:
            output.append(locator_path)

        if record:
            recording.append(
                {
                    "type": "locator",
                    "top": top_level_name,
                    "top_handle": top_level_handle,
                    "x": top_level_control,
                    "locator": locator_path,
                }
            )

    return output


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
    if automation_id and not utils.is_numeric(automation_id):
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


def stop_listeners():
    mouse.Listener.stop()
    keyboard.Listener.stop()


def start_recording(verbose: bool = False):
    """Start recording mouse clicks.

    Can be stopped by pressing keyboard ``ESC``.
    """
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
            inspect_element(verbose)

    def on_release(key):
        if key == keyboard.Key.esc:
            return False
        return True

    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()
    with keyboard.Listener(on_release=on_release) as key_listener:
        print("keyboard and mouse listeners started", flush=True)
        key_listener.join()
    mouse_listener.stop()
    the_recording = get_recording()
    print(the_recording)


def get_recording(sleeps: bool = False):
    """Get list of recorded steps.

    :param sleeps: Exclude recording sleeps when `False`.
    """
    # NOTE: Works with "Click" only for now.
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
            or "top" in item
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


def main():
    fire.Fire(start_recording)
