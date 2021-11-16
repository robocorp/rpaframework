from typing import Union, Optional

from RPA.Windows.keywords import (
    ActionNotPossible,
    keyword,
    LibraryContext,
    WindowControlError,
)
from RPA.Windows import utils

if utils.is_windows():
    import uiautomation as auto
    from uiautomation.uiautomation import Control


class ActionKeywords(LibraryContext):
    """Keywords for performing desktop actions"""

    @keyword(tags=["action"])
    def click(
        self,
        locator: Union[str, Control],
        set_focus: bool = False,
    ):
        """Mouse click on control matching given locator.

        :param locator: string locator or Control object
        :param set_focus: set True to focus on Control object
        """
        click_type = "Click"
        control = self._mouse_click(locator, set_focus, click_type)
        return control

    @keyword(tags=["action"])
    def double_click(
        self,
        locator: Union[str, Control],
        set_focus: bool = False,
    ):
        """Double mouse click on control matching given locator.

        :param locator: string locator or Control object
        :param set_focus: set True to focus on Control object
        """
        click_type = "DoubleClick"
        control = self._mouse_click(locator, set_focus, click_type)
        return control

    @keyword(tags=["action"])
    def right_click(
        self,
        locator: Union[str, Control],
        set_focus: bool = False,
    ):
        """Right mouse click on control matching given locator.

        :param locator: string locator or Control object
        :param set_focus: set True to focus on Control object
        """
        click_type = "RightClick"
        control = self._mouse_click(locator, set_focus, click_type)
        return control

    @keyword(tags=["action"])
    def middle_click(
        self,
        locator: Union[str, Control],
        set_focus: bool = False,
    ):
        """Right mouse click on control matching given locator.

        :param locator: string locator or Control object
        :param set_focus: set True to focus on Control object
        """
        click_type = "MiddleClick"
        control = self._mouse_click(locator, set_focus, click_type)
        return control

    def _mouse_click(self, locator, set_focus, click_type):
        control = self._get_control_for_click(locator, set_focus)
        if control.robocorp_click_offset:
            self._click_control_coordinates(control, click_type)
        else:
            self._click_control(control, click_type)
        return control

    def _click_control_coordinates(self, control, click_type):
        callable = getattr(auto, click_type)
        rect = control.BoundingRectangle
        offset_x, offset_y = [int(v) for v in control.robocorp_click_offset.split(",")]
        callable(
            rect.xcenter() + offset_x,
            rect.ycenter() + offset_y,
            waitTime=self.ctx.timeout,
        )

    def _click_control(self, control, click_type):
        callable = getattr(control, click_type)
        callable(waitTime=self.ctx.timeout, simulateMove=self.ctx.simulate_move)

    def _get_control_for_click(self, locator, set_focus):
        control = locator
        if isinstance(locator, str):
            try:
                control = self.ctx.get_control(locator)
            except Exception as err:
                raise WindowControlError(str(err)) from err
        if set_focus:
            control.SetFocus()
            if hasattr(control, "SetActive"):
                control.SetActive()
        control.MoveCursorToMyCenter(simulateMove=self.ctx.simulate_move)
        return control

    @keyword(tags=["action"])
    def select(self, locator: Union[str, Control], value: str):
        """Select value on Control object if action is supported.

        Will print warning if it is not possible to select on object.

        :param locator: string locator or Control object
        :param value: string value to select on Control object
        """
        control = locator
        if isinstance(locator, str):
            try:
                control = self.ctx.get_control(locator)
            except Exception as err:
                raise WindowControlError(str(err)) from err
        if hasattr(control, "Select"):
            control.Select(value)
        else:
            raise ActionNotPossible(
                "Control '%s' does not have 'Select' attribute" % locator
            )

    @keyword(tags=["action"])
    def input_text(self, text: str, locator: Union[str, Control]):
        """Input text into Control object defined by the locator.

        :param text: the text to input
        :param locator: string locator or Control object
        """
        control = locator
        if isinstance(locator, str):
            control = self.ctx.get_control(locator)
        self.send_keys(text, control)

    @keyword(tags=["action"])
    def send_keys(self, keys: str, locator: Optional[Union[str, Control]] = None):
        """Send keys to desktop, current window or to Control object
        defined by given locator.

        :param keys: the keys to send
        :param locator: string locator or Control object (default None)
        """
        if not locator:
            control = self.ctx.window or auto
        elif isinstance(locator, str):
            control = self.ctx.get_control(locator)
        else:
            control = locator
        control.SendKeys(keys, waitTime=self.ctx.timeout)

    @keyword
    def get_text(self, locator: Union[str, Control]) -> str:
        """Get text from Control object defined by the locator.

        :param locator: string locator or Control object
        """
        control = locator
        if isinstance(locator, str):
            control = self.ctx.get_control(locator)
        if hasattr(control, "GetWindowText"):
            return control.GetWindowText()
        raise ActionNotPossible(
            "Control '%s' does not have 'GetWindowText' attribute" % locator
        )

    @keyword
    def get_item_value(self, locator: Union[str, Control]) -> str:
        """Get Control object item value

        :param locator: string locator or Control object
        """
        control = locator
        if isinstance(locator, str):
            control = self.ctx.get_control(locator)
        if hasattr(control, "GetValuePattern"):
            value_pattern = control.GetValuePattern()
            return value_pattern.Value
        raise ActionNotPossible(
            "Control '%s' does not have 'GetValuePattern' attribute" % locator,
        )

    @keyword(tags=["action"])
    def set_item_value(self, locator: Union[str, Control], value: str) -> None:
        """Set Control object item value

        :param locator: string locator or Control object
        :param value: string value to set
        """
        control = locator
        if isinstance(locator, str):
            control = self.ctx.get_control(locator)
        if hasattr(control, "GetValuePattern"):
            value_pattern = control.GetValuePattern()
            value_pattern.SetValue(value)
        else:
            raise ActionNotPossible(
                "Control '%s' does not have 'GetValuePattern' attribute" % locator,
            )

    @keyword
    def set_timeout(self, timeout: float) -> None:
        """Set library timeout for action keywords

        :param timeout: float value (in seconds), e.g. `0.1`
        """
        self.ctx.timeout = timeout
