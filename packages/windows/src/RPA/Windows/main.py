from datetime import datetime
from typing import List

import fire
from pynput_robocorp import mouse, keyboard  # pylint: disable=C0415
from RPA.core.windows.inspect import ElementInspector, RecordElement


recording_time = None
recording: List[RecordElement] = []


def stop_listeners():
    mouse.Listener.stop()
    keyboard.Listener.stop()


def start_recording(verbose: bool = False):
    """Start recording mouse clicks.

    Can be stopped by pressing keyboard ``ESC``.
    """
    global recording  # pylint: disable=W0603
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
            ElementInspector.inspect_element(recording=recording, verbose=verbose)

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
