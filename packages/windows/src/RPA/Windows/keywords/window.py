import time
from typing import List, Dict

from RPA.Windows.keywords import (
    keyword,
    LibraryContext,
    WindowControlError,
)
from RPA.Windows import utils


if utils.is_windows():
    import uiautomation as auto


class WindowKeywords(LibraryContext):
    """Keywords for handling Window controls"""

    @keyword
    def control_window(self, title: str = None, process_name: str = None) -> int:
        """[summary]

        Return process id of the window

        :param title: [description], defaults to None
        :param process_name: [description], defaults to None
        """
        subname = None
        if title:
            subname = title
        elif process_name:
            window_list = self.list_windows()
            matches = [w for w in window_list if w["name"] == process_name]
            if not matches:
                raise WindowControlError(
                    "Could not locate window with process name '%s'" % process_name
                )
            elif len(matches) > 1:
                raise WindowControlError(
                    "Found more than one window with process_name '%s'" % process_name
                )
            subname = matches[0]["title"]

        self.ctx.window = auto.WindowControl(
            searchDepth=8, SubName=subname
        )  # RegexName=f'{title}')
        if not self.window.Exists():
            self.ctx.window = auto.PaneControl(
                searchDepth=8, SubName=subname
            )  # RegexName=f'{title}')
        if not self.ctx.window.Exists():
            raise WindowControlError("Could not locate window title '%s'" % title)
        # or PaneControl ?
        self.ctx.logger.info(dir(self.ctx.window))
        self.ctx.window.Restore()
        self.ctx.window.SetFocus()
        self.ctx.window.MoveCursorToMyCenter(simulateMove=self.ctx.simulate_move)
        time.sleep(1.0)
        return self.ctx.window.ProcessId

    @keyword
    def minimize_window(self, title: str = None, process_name: str = None) -> None:
        if title or process_name:
            self.control_window(title, process_name)
        if not self.ctx.window:
            raise WindowControlError("There is no active window")
        if not hasattr(self.ctx.window, "Minimize"):
            raise WindowControlError("Window does not have attribute Minimize")
        self.ctx.window.Minimize()

    @keyword
    def maximize_window(self, title: str = None, process_name: str = None) -> None:
        if title or process_name:
            self.control_window(title, process_name)
        if not self.ctx.window:
            raise WindowControlError("There is no active window")
        if not hasattr(self.ctx.window, "Maximize"):
            raise WindowControlError("Window does not have attribute Maximize")
        self.ctx.window.Maximize()

    @keyword
    def list_windows(self) -> List[Dict]:
        windows = auto.GetRootControl().GetChildren()
        process_list = utils.get_process_list()
        win_list = []
        for win in windows:
            pid = win.ProcessId
            info = {
                "title": win.Name,
                "pid": win.ProcessId,
                "name": process_list[pid] if pid in process_list.keys() else None,
            }
            win_list.append(info)
        return win_list

    @keyword
    def windows_run(self, name: str, wait_time: float = 3.0) -> None:
        self.send_keys("{Win}r")
        self.send_keys(name)
        self.send_keys("{Enter}")
        time.sleep(wait_time)

    @keyword
    def windows_search(self, name: str, wait_time: float = 3.0) -> None:
        self.send_keys("{Win}s")
        self.send_keys(name)
        self.send_keys("{Enter}")
        time.sleep(wait_time)

    @keyword
    def close_current_window(self) -> None:
        if not self.ctx.window:
            raise WindowControlError("There is no active window")
        self.ctx.logger.warning(
            "Current window process id = %s" % self.window.ProcessId
        )
        self.ctx.window.SetActive()
        self.ctx.window.SendKeys("{Alt}{F4}")

    @keyword
    def click(
        self,
        locator,
        set_focus: bool = False,
    ):
        control = locator
        if isinstance(locator, str):
            try:
                control = self.ctx.locator_to_control(locator)
            except Exception as err:
                raise WindowControlError from err
        # rect = control.BoundingRectangle
        # self.logger.info(type(rect))
        # self.logger.info(dir(rect))
        # self.logger.info(rect.xcenter())
        # self.logger.info(rect.ycenter())
        # offset_x = offset_x or 0
        # offset_y = offset_y or 0
        # auto.Click(rect.xcenter()+offset_x, rect.ycenter()+offset_y)
        if set_focus:
            control.SetFocus()
            if hasattr(control, "SetActive"):
                control.SetActive()
            control.MoveCursorToMyCenter(simulateMove=self.ctx.simulate_move)
            time.sleep(0.5)
        control.Click(waitTime=self.ctx.timeout, simulateMove=self.ctx.simulate_move)
        return control
        # time.sleep(self.timeout)

    @keyword
    def select(self, locator, value):
        control = locator
        if isinstance(locator, str):
            try:
                control = self.ctx.locator_to_control(locator)
            except Exception as err:
                raise WindowControlError from err
        control.Select(value)

    @keyword
    def input_text(self, locator, text):
        control = self.ctx.locator_to_control(locator)
        self.send_keys(text, control)

    @keyword
    def send_keys(self, keys=None, control=None):
        control = control or self.ctx.window or auto
        control.SendKeys(keys, waitTime=self.ctx.timeout)

    @keyword
    def get_item_value(self, item):
        value_pattern = item.GetValuePattern()
        return value_pattern.Value

    @keyword
    def set_item_value(self, item, value):
        value_pattern = item.GetValuePattern()
        value_pattern.SetValue(value)

    @keyword
    def get_text(self, locator):
        control = self.ctx.locator_to_control(locator)
        return control.GetWindowText()
        # return control.GetValuePattern().Value

    @keyword
    def set_timeout(self, timeout: float):
        self.ctx.timeout = timeout
