from datetime import datetime

# pylint: disable=C0415
from pynput_robocorp import mouse, keyboard

from RPA.Windows.keywords import keyword, LibraryContext
from RPA.Windows import utils


if utils.is_windows():
    import uiautomation as auto


class RecorderKeywords(LibraryContext):
    """Keywords for inspecting and recording"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.record = False
        self.recording = []
        self.record_time = None

    @keyword(tags=["recording"])
    def inspect_control(self, action: str = "Click", control_window: bool = True):
        """Inspect Windows Control under mouse pointer

        :param action: which action is attached to locator
        :param control_window: set False to not include ``Control Window`` keyword
        """
        # TODO. Add Python syntax
        with auto.UIAutomationInitializerInThread(debug=True):
            control = auto.ControlFromCursor()
            self.ctx.logger.warning(control)
            parent_control = control.GetParentControl()
            top_level_control = control.GetTopLevelControl()
            # self.logger.warning("Top: %s" % top_level_control)
            # self.logger.warning("Parent: %s" % parent_control)
            # self.logger.warning(dir(control))
            parent_locator = self._get_control_key_properties(parent_control)
            child_locator = self._get_control_key_properties(control)
            locator_path = f"{parent_locator} > {child_locator}"
            if "id:" in child_locator:
                locator_path = child_locator
            output = []
            if control_window:
                output.append(f"Control Window  {top_level_control.Name}")
            if action:
                output.append(f"{action}  {locator_path}")
            else:
                output.append(locator_path)
            if self.record:
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
                self.recording.append(
                    {
                        "type": "locator",
                        "top": top_level_control.Name,
                        "top_handle": top_level_control.NativeWindowHandle,
                        "x": top_level_control,
                        "locator": locator_path,
                    }
                )
            return output

    def _get_control_key_properties(self, control, regex_limit=300):
        automation_id = control.AutomationId
        snippet = ""
        if automation_id and not utils.is_integer(automation_id):
            snippet = f"id:{automation_id}"
        else:
            control_type = control.ControlTypeName.strip()
            class_name = control.ClassName.strip()
            name = control.Name.strip()
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
                self.ctx.logger.warning(
                    "Was unable to construct locator for the control"
                )
                return None
            else:
                snippet = " and ".join(locators)
        return snippet

    @keyword(tags=["recording"])
    def stop_listeners(self):
        mouse.Listener.stop()
        keyboard.Listener.stop()

    @keyword(tags=["recording"])
    def stop_recording(self):
        self.record = False

    @keyword(tags=["recording"])
    def start_recording(self):
        """Start recording mouse clicks.

        Can be stopped by pressing keyboard ``ESC``.
        """
        self.record = True
        self.recording = []
        self.record_time = None

        def on_click(x, y, button, pressed):  # pylint: disable=W0613
            if pressed:
                inspect_time = datetime.now()
                if self.record_time:
                    timediff = inspect_time - self.record_time
                    seconds = max(
                        round(float(timediff.microseconds / 1000000.0), 1), 0.1
                    )
                    self.recording.append({"type": "sleep", "value": seconds})
                self.record_time = inspect_time
                self.inspect_control()

        def on_release(key):
            if key == keyboard.Key.esc:
                return False
            return True

        mouse_listener = mouse.Listener(on_click=on_click)
        self.ctx.logger.warning("starting mouse listener")
        mouse_listener.start()
        self.ctx.logger.warning("starting key listener")
        with keyboard.Listener(on_release=on_release) as key_listener:
            key_listener.join()
        mouse_listener.stop()
        self.ctx.logger.warning("LEN = %s" % len(self.recording))

    @keyword(tags=["recording"])
    def get_recording(self, sleeps=True):
        """Get list of recorded steps.

        :param sleeps: set False to exclude recording sleeps
        """
        # TODO. atm will always use CLICK
        output = []
        top = None
        for item in self.recording:
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
                output.append(f"Click   {item['locator']}")

        result = "\n".join(output)
        header = (
            f"\n{'-'*80}"
            "\nCOPY & PASTE BELOW CODE INTO *** Tasks *** or *** Keywords ***"
            f"\n{'-'*80}\n\n"
        )
        footer = f"\n\n{'-'*80}"
        return f"{header}{result}{footer}"
