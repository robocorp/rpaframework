from typing import Union, Optional

from RPA.Windows.keywords import (
    ActionNotPossible,
    keyword,
    LibraryContext,
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

        Example:

        .. code-block:: robotframework

            Click  id:button1
            Click  id:button2 offset:10,10
            Click  name:SendButton  True
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

        Example:

        .. code-block:: robotframework

            Double Click  name:ResetButton
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

        Example:

        .. code-block:: robotframework

            Right Click  name:MenuButton
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

        Example:

        .. code-block:: robotframework

            Middle Click  name:button2
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
        callable_attribute = getattr(auto, click_type, None)
        if callable_attribute:
            rect = control.BoundingRectangle
            offset_x, offset_y = [
                int(v) for v in control.robocorp_click_offset.split(",")
            ]
            callable_attribute(
                rect.xcenter() + offset_x,
                rect.ycenter() + offset_y,
                waitTime=self.ctx.timeout,
            )
        else:
            raise ActionNotPossible(
                "Control '%s' does not have '%s' attribute" % (control, click_type)
            )

    def _click_control(self, control, click_type):
        callable_attribute = getattr(control, click_type, None)
        if callable_attribute:
            callable_attribute(
                waitTime=self.ctx.timeout, simulateMove=self.ctx.simulate_move
            )
        else:
            raise ActionNotPossible(
                "Control '%s' does not have '%s' attribute" % (control, click_type)
            )

    def _get_control_for_click(self, locator, set_focus):
        control = self.ctx.get_control(locator)
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

        Example:

        .. code-block:: robotframework

            Select  type:SelectControl   option2
        """
        control = self.ctx.get_control(locator)
        if hasattr(control, "Select"):
            control.Select(value)
        else:
            raise ActionNotPossible(
                "Control '%s' does not have 'Select' attribute" % locator
            )

    @keyword(tags=["action"])
    def input_text(
        self,
        locator: Union[str, Control],
        text: str,
        interval: float = 0.01,
        wait_time: float = None,
    ):
        """Input text into desktop, current window or to Control object
        defined by given locator.

        Alias of keyword ``Send Keys``.

        :param locator: string locator or Control object (default None)
        :param keys: the keys to send
        :param interval: time between sending keys, default 0.01 seconds
        :param wait_time: time to wait after sending keys, default is a
         library timeout

        Example:

        .. code-block:: robotframework

            Send Keys  desktop   {Ctrl}{F4}
            Send Keys  id:input5  username
            ${control}=   Get Control   id:pass
            Send Keys  ${control}  password
        """
        self.send_keys(locator, text, interval, wait_time)

    @keyword(tags=["action"])
    def send_keys(
        self,
        locator: Optional[Union[str, Control]] = None,
        keys: str = None,
        interval: float = 0.01,
        wait_time: float = None,
    ):
        """Send keys to desktop, current window or to Control object
        defined by given locator.

        :param locator: string locator or Control object (default None)
        :param keys: the keys to send
        :param interval: time between sending keys, default 0.01 seconds
        :param wait_time: time to wait after sending keys, default is a
         library timeout

        Example:

        .. code-block:: robotframework

            Send Keys  desktop   {Ctrl}{F4}
            Send Keys  id:input5  username
            ${control}=   Get Control   id:pass
            Send Keys  ${control}  password
        """
        control = self.ctx.get_control(locator)
        keys_wait_time = wait_time or self.ctx.timeout
        if hasattr(control, "SendKeys"):
            control.SendKeys(keys, interval=interval, waitTime=keys_wait_time)
        else:
            raise ActionNotPossible(
                "Control '%s' does not have 'SendKeys' attribute" % locator
            )

    @keyword
    def get_text(self, locator: Union[str, Control]) -> str:
        """Get text from Control object defined by the locator.

        :param locator: string locator or Control object

        Example:

        .. code-block:: robotframework

            ${date}=  Get Text   type:Edit name:'Date of birth'
        """
        control = self.ctx.get_control(locator)
        if hasattr(control, "GetWindowText"):
            return control.GetWindowText()
        raise ActionNotPossible(
            "Control '%s' does not have 'GetWindowText' attribute" % locator
        )

    @keyword
    def get_item_value(self, locator: Union[str, Control]) -> str:
        """Get Control object item value.

        :param locator: string locator or Control object

        Example:

        .. code-block:: robotframework

            ${value}=   Get Item Value   type:DataItem name:column1
        """
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

        Example:

        .. code-block:: robotframework

            Set Item Value   type:DataItem name:column1   abc
        """
        control = self.ctx.get_control(locator)
        if hasattr(control, "GetValuePattern"):
            value_pattern = control.GetValuePattern()
            value_pattern.SetValue(value)
        else:
            raise ActionNotPossible(
                "Control '%s' does not have 'ValuePattern' attribute to set" % locator,
            )

    @keyword
    def set_timeout(self, timeout: float) -> float:
        """Set library timeout for action keywords.

        This timeout is used as delay after each keyword performing mouse
        or keyboard action.

        Returns value of the previous timeout value.

        :param timeout: float value (in seconds), e.g. `0.1`

        Example:

        .. code-block:: robotframework

            ${old_timeout}=  Set Timeout  0.2
        """
        self.ctx.timeout = timeout
