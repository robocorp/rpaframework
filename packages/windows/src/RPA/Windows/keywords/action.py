from pathlib import Path
from typing import Union, Optional

from RPA.Windows.keywords import ActionNotPossible, keyword, LibraryContext
from RPA.Windows import utils
from .locators import WindowsElement

if utils.is_windows():
    import uiautomation as auto


class ActionKeywords(LibraryContext):
    """Keywords for performing desktop actions"""

    @keyword(tags=["action", "mouse"])
    def click(self, locator: Union[WindowsElement, str]):
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
    def double_click(self, locator: Union[WindowsElement, str]):
        """Double mouse click on element matching given locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            Double Click  name:ResetButton
        """
        return self._mouse_click(locator, "DoubleClick")

    @keyword(tags=["action", "mouse"])
    def right_click(self, locator: Union[WindowsElement, str]):
        """Right mouse click on element matching given locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            Right Click  name:MenuButton
        """
        return self._mouse_click(locator, "RightClick")

    @keyword(tags=["action", "mouse"])
    def middle_click(self, locator: Union[WindowsElement, str]):
        """Right mouse click on element matching given locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            Middle Click  name:button2
        """
        return self._mouse_click(locator, "MiddleClick")

    def _mouse_click(self, element, click_type):
        element = self._get_element_for_click(element)
        if element.item.robocorp_click_offset:
            self._click_element_coordinates(element, click_type)
        else:
            self._click_element(element, click_type)
        return element

    def _click_element_coordinates(self, element, click_type):
        callable_attribute = getattr(auto, click_type, None)
        if callable_attribute:
            rect = element.item.BoundingRectangle
            offset_x, offset_y = [
                int(v) for v in element.item.robocorp_click_offset.split(",")
            ]
            callable_attribute(
                rect.xcenter() + offset_x,
                rect.ycenter() + offset_y,
                waitTime=self.ctx.wait_time,
            )
        else:
            raise ActionNotPossible(
                "Element '%s' does not have '%s' attribute" % (element, click_type)
            )

    def _click_element(self, element, click_type):
        attr = getattr(element.item, click_type, None)
        if attr and callable(attr):
            attr(waitTime=self.ctx.wait_time, simulateMove=self.ctx.simulate_move)
        else:
            raise ActionNotPossible(
                "Element '%s' does not have '%s' attribute" % (element, click_type)
            )

    def _get_element_for_click(self, locator):
        element = self.ctx.get_element(locator)
        if hasattr(element.item, "SetActive"):
            element.item.SetActive()
        element.item.MoveCursorToMyCenter(simulateMove=self.ctx.simulate_move)
        return element

    @keyword(tags=["action"])
    def select(self, locator: Union[WindowsElement, str], value: str):
        """Select value on Control element if action is supported.

        Will print warning if it is not possible to select on element.

        :param locator: string locator or Control element
        :param value: string value to select on Control element

        Example:

        .. code-block:: robotframework

            Select  type:SelectControl   option2
        """
        element = self.ctx.get_element(locator)
        if hasattr(element.item, "Select"):
            element.item.Select(value)
        else:
            raise ActionNotPossible(
                "Element '%s' does not have 'Select' attribute" % locator
            )

    @keyword(tags=["action"])
    def send_keys(
        self,
        locator: Optional[Union[WindowsElement, str]] = None,
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
         library `wait_time`, see keyword ``Set Wait Time``
        :param send_enter: if True then {Enter} is sent at the end of the keys

        Example:

        .. code-block:: robotframework

            Send Keys  desktop   {Ctrl}{F4}
            Send Keys  keys={Ctrl}{F4}   # locator will be NONE, keys send to desktop
            Send Keys  id:input5  username   send_enter=True
            ${element}=   Get Element   id:pass
            Send Keys  ${element}  password   send_enter=True
        """
        element = self.ctx.get_element(locator)
        keys_wait_time = wait_time or self.ctx.wait_time
        if send_enter:
            keys += "{Enter}"
        if hasattr(element.item, "SendKeys"):
            element.item.SendKeys(keys, interval=interval, waitTime=keys_wait_time)
        else:
            raise ActionNotPossible(
                "Element '%s' does not have 'SendKeys' attribute" % locator
            )

    @keyword
    def get_text(self, locator: Union[WindowsElement, str]) -> str:
        """Get text from Control element defined by the locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            ${date}=  Get Text   type:Edit name:'Date of birth'
        """
        element = self.ctx.get_element(locator)
        if hasattr(element.item, "GetWindowText"):
            return element.item.GetWindowText()
        raise ActionNotPossible(
            "Element '%s' does not have 'GetWindowText' attribute" % locator
        )

    @keyword
    def get_value(self, locator: Union[WindowsElement, str]) -> str:
        """Get value of the element defined by the locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            ${value}=   Get Value   type:DataItem name:column1
        """
        element = self.ctx.get_element(locator)
        if hasattr(element.item, "GetValuePattern"):
            value_pattern = element.item.GetValuePattern()
            return value_pattern.Value
        raise ActionNotPossible(
            "Element '%s' does not have 'GetValuePattern' attribute" % locator,
        )

    @keyword(tags=["action"])
    def set_value(
        self, locator: Union[WindowsElement, str], value: str, enter: bool = False
    ) -> None:
        """Set value of the element defined by the locator.

        :param locator: string locator or Control element
        :param value: string value to set
        :param enter: set True to send ENTER key to the element

        Example:

        .. code-block:: robotframework

            Set Value   type:DataItem name:column1   ab c  # Set value to "ab c"
            # Press ENTER after setting the value
            Set Value    type:Edit name:'File name:'    console.txt    True
        """
        element = self.ctx.get_element(locator)
        if hasattr(element.item, "GetValuePattern"):
            value_pattern = element.item.GetValuePattern()
            value_pattern.SetValue(value)
            if enter:
                self.send_keys(element, "{enter}")
        else:
            raise ActionNotPossible(
                "Element '%s' does not have 'ValuePattern' attribute to set" % locator,
            )

    @keyword
    def set_wait_time(self, wait_time: float) -> float:
        """Set library wait time for action keywords.

        The wait_time is spent after each keyword performing
        mouse or keyboard action.

        Library default wait_time is `0.5`

        Returns value of the previous wait_time value.

        :param wait_time: float value (in seconds), e.g. `0.1`

        Example:

        .. code-block:: robotframework

            ${old_wait_time}=  Set Wait Time  0.2
        """
        old_value = self.ctx.wait_time
        self.ctx.wait_time = wait_time
        return old_value

    @keyword
    def screenshot(self, locator: Union[WindowsElement, str], filename: str):
        """Take a screenshot of the element defined by the locator.

        :param locator: string locator or Control element
        :param filename: image filename
        """
        filepath = Path(filename).resolve()
        element = self.ctx.get_element(locator)
        if hasattr(element.item, "CaptureToImage"):
            element.item.CaptureToImage(str(filepath))
        else:
            raise ActionNotPossible(
                "Element '%s' does not have 'CaptureToImage' attribute" % locator,
            )
