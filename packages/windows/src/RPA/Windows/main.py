from datetime import datetime
from typing import List, Optional

import fire
from comtypes import COMError
from pynput_robocorp import keyboard, mouse  # pylint: disable=C0415
from RPA.core.windows.inspect import ElementInspector, RecordElement


recording: List[RecordElement] = []


def get_recording(show_sleeps: bool = False) -> str:
    """Get a list of the recorded steps after stopping clicking elements.

    :param show_sleeps: Exclude recording sleeps when `False`.
    :returns: The string report of the recorded elements.
    """
    output = []
    top_window = None
    # NOTE(cmin764): Works with "Click" actions only for now.
    action_name = "Click"

    for item in recording:
        if show_sleeps and item["type"] == "sleep":
            output.append(f"Sleep   {item['value']}s")

        if item["type"] == "locator":
            new_top = item["top"]
            if not top_window or new_top != top_window:
                output.append(
                    f"\nControl Window    {new_top}  # handle:{item['top_handle']}"
                )
                top_window = new_top

            output.append(f"{action_name}    {item['locator']}")

    sep = "-" * 80
    header = (
        f"\n{sep}"
        "\nCopy-paste the code below into your `*** Tasks ***` or `*** Keywords ***`"
        f"\n{sep}\n"
    )
    result = "\n".join(output)
    footer = f"\n\n{sep}"
    return f"{header}{result}{footer}"


def start_recording(verbose: bool = False):
    """Start recording elements with mouse clicks.

    Can be stopped by pressing the *ESC* key.
    """
    recording_time: Optional[datetime] = None
    recording.clear()
    inspector = ElementInspector()

    def on_click(x, y, button, pressed):  # pylint: disable=W0613
        nonlocal recording_time  # pylint: disable=W0602
        if not pressed:
            return

        inspect_time = datetime.now()
        if recording_time:
            timediff = inspect_time - recording_time
            seconds = max(round(float(timediff.microseconds / 1000000.0), 1), 0.1)
            recording.append({"type": "sleep", "value": seconds})
        recording_time = inspect_time

        try:
            inspector.inspect_element(recording, verbose=verbose)
        except (NotImplementedError, COMError) as err:
            # At least in cases where Windows desktop is clicked as first event
            # to capture, the recorder goes into some broken state where future
            # clicks also fail to capture.
            print(f"Could not capture element, got exception: {err}", flush=True)
            key_listener.stop()
            mouse_listener.stop()

    def on_release(key):
        if key == keyboard.Key.esc:
            return False
        return True

    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()
    with keyboard.Listener(on_release=on_release) as key_listener:
        print(
            "Mouse recording started. Use ESC to stop recording.",
            flush=True,
        )
        key_listener.join()
    mouse_listener.stop()
    the_recording = get_recording()
    print(the_recording)


def main():
    fire.Fire(start_recording)
