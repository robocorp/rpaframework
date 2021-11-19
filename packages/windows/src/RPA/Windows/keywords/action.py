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

    @keyword(tags=["action", "mouse"])
    def click(self, locator: Union[str, Control]):
        """Mouse click on element matching given locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            Click  id:button1
            Click  id:button2 offset:10,10
            Click  name:SendButton
        """
        return self._mouse_click(locator, "Click")

    @keyword(tags=["action", "mouse"])
    def double_click(self, locator: Union[str, Control]):
        """Double mouse click on element matching given locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            Double Click  name:ResetButton
        """
        return self._mouse_click(locator, "DoubleClick")

    @keyword(tags=["action", "mouse"])
    def right_click(self, locator: Union[str, Control]):
        """Right mouse click on element matching given locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            Right Click  name:MenuButton
        """
        return self._mouse_click(locator, "RightClick")

    @keyword(tags=["action", "mouse"])
    def middle_click(self, locator: Union[str, Control]):
        """Right mouse click on element matching given locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            Middle Click  name:button2
        """
        return self._mouse_click(locator, "MiddleClick")

    def _mouse_click(self, element, click_type):
        element = self._get_element_for_click(element)
        if element.robocorp_click_offset:
            self._click_element_coordinates(element, click_type)
        else:
            self._click_element(element, click_type)
        return element

    def _click_element_coordinates(self, element, click_type):
        callable_attribute = getattr(auto, click_type, None)
        if callable_attribute:
            rect = element.BoundingRectangle
            offset_x, offset_y = [
                int(v) for v in element.robocorp_click_offset.split(",")
            ]
            callable_attribute(
                rect.xcenter() + offset_x,
                rect.ycenter() + offset_y,
                waitTime=self.ctx.timeout,
            )
        else:
            raise ActionNotPossible(
                "Element '%s' does not have '%s' attribute" % (element, click_type)
            )

    def _click_element(self, element, click_type):
        attr = getattr(element, click_type, None)
        if attr and callable(attr):
            attr(waitTime=self.ctx.timeout, simulateMove=self.ctx.simulate_move)
        else:
            raise ActionNotPossible(
                "Element '%s' does not have '%s' attribute" % (element, click_type)
            )

    def _get_element_for_click(self, locator):
        element = self.ctx.get_element(locator)
        if hasattr(element, "SetActive"):
            element.SetActive()
        element.MoveCursorToMyCenter(simulateMove=self.ctx.simulate_move)
        return element

    @keyword(tags=["action"])
    def select(self, locator: Union[str, Control], value: str):
        """Select value on Control element if action is supported.

        Will print warning if it is not possible to select on element.

        :param locator: string locator or Control element
        :param value: string value to select on Control element

        Example:

        .. code-block:: robotframework

            Select  type:SelectControl   option2
        """
        element = self.ctx.get_element(locator)
        if hasattr(element, "Select"):
            element.Select(value)
        else:
            raise ActionNotPossible(
                "Element '%s' does not have 'Select' attribute" % locator
            )

    @keyword(tags=["action"])
    def send_keys(
        self,
        locator: Optional[Union[str, Control]] = None,
        keys: str = None,
        interval: float = 0.01,
        wait_time: float = None,
        send_enter: bool = False,
    ):
        """Send keys to desktop, current window or to Control element
        defined by given locator.

        If ``locator`` is `None` then keys are sent to desktop.

        :param locator: string locator or Control element (default None means desktop)
        :param keys: the keys to send
        :param interval: time between sending keys, default 0.01 seconds
        :param wait_time: time to wait after sending keys, default is a
         library timeout
        :param send_enter: if True then {Enter} is sent at the end of the keys

        Example:

        .. code-block:: robotframework

            Send Keys  desktop   {Ctrl}{F4}
            Send Keys  None   {Ctrl}{F4}
            Send Keys  id:input5  username   send_enter=True
            ${control}=   Get Control   id:pass
            Send Keys  ${control}  password   send_enter=True
        """
        element = self.ctx.get_element(locator)
        keys_wait_time = wait_time or self.ctx.timeout
        if send_enter:
            keys += "{Enter}"
        if hasattr(element, "SendKeys"):
            element.SendKeys(keys, interval=interval, waitTime=keys_wait_time)
        else:
            raise ActionNotPossible(
                "Element '%s' does not have 'SendKeys' attribute" % locator
            )

    @keyword
    def get_text(self, locator: Union[str, Control]) -> str:
        """Get text from Control element defined by the locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            ${date}=  Get Text   type:Edit name:'Date of birth'
        """
        element = self.ctx.get_element(locator)
        if hasattr(element, "GetWindowText"):
            return element.GetWindowText()
        raise ActionNotPossible(
            "Element '%s' does not have 'GetWindowText' attribute" % locator
        )

    @keyword
    def get_value(self, locator: Union[str, Control]) -> str:
        """Get value of the element defined by the locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            ${value}=   Get Value   type:DataItem name:column1
        """
        element = self.ctx.get_element(locator)
        if hasattr(element, "GetValuePattern"):
            value_pattern = element.GetValuePattern()
            return value_pattern.Value
        raise ActionNotPossible(
            "Element '%s' does not have 'GetValuePattern' attribute" % locator,
        )

    @keyword(tags=["action"])
    def set_value(self, locator: Union[str, Control], value: str) -> None:
        """Set value of the element defined by the locator.

        :param locator: string locator or Control element
        :param value: string value to set

        Example:

        .. code-block:: robotframework

            Set Value   type:DataItem name:column1   ab c  # Set value to "ab c"
        """
        element = self.ctx.get_element(locator)
        if hasattr(element, "GetValuePattern"):
            value_pattern = element.GetValuePattern()
            value_pattern.SetValue(value)
        else:
            raise ActionNotPossible(
                "Element '%s' does not have 'ValuePattern' attribute to set" % locator,
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
        old_value = self.ctx.timeout
        self.ctx.timeout = timeout
        return old_value
