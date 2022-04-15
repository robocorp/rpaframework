from pathlib import Path
from typing import Optional

from RPA.core.windows.locators import Locator, WindowsElement

from RPA.Windows import utils
from RPA.Windows.keywords import keyword
from RPA.Windows.keywords.context import ActionNotPossible, LibraryContext

if utils.IS_WINDOWS:
    import uiautomation as auto


class ActionKeywords(LibraryContext):
    """Keywords for performing desktop actions"""

    @keyword(tags=["action", "mouse"])
    def click(
        self,
        locator: Locator,
        wait_time: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> WindowsElement:
        """Mouse click on element matching given locator.

        Exception ``ActionNotPossible`` is raised if element does not
        allow Click action.

        :param locator: string locator or Control element
        :param wait_time: time to wait after click, default is a
         library `wait_time`, see keyword ``Set Wait Time``
        :param timeout: float value in seconds, see keyword
         ``Set Global Timeout``
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            Click  id:button1
            Click  id:button2 offset:10,10
            ${element}=  Click  name:SendButton  wait_time=5.0
        """
        return self._mouse_click(locator, "Click", wait_time, timeout)

    @keyword(tags=["action", "mouse"])
    def double_click(
        self,
        locator: Locator,
        wait_time: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> WindowsElement:
        """Double mouse click on element matching given locator.

        Exception ``ActionNotPossible`` is raised if element does not
        allow Click action.

        :param locator: string locator or Control element
        :param wait_time: time to wait after click, default is a
         library `wait_time`, see keyword ``Set Wait Time``
        :param timeout: float value in seconds, see keyword
         ``Set Global Timeout``
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            ${element}=  Double Click  name:ResetButton
        """
        return self._mouse_click(locator, "DoubleClick", wait_time, timeout)

    @keyword(tags=["action", "mouse"])
    def right_click(
        self,
        locator: Locator,
        wait_time: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> WindowsElement:
        """Right mouse click on element matching given locator.

        Exception ``ActionNotPossible`` is raised if element does not
        allow Click action.

        :param locator: string locator or Control element
        :param wait_time: time to wait after click, default is a
         library `wait_time`, see keyword ``Set Wait Time``
        :param timeout: float value in seconds, see keyword
         ``Set Global Timeout``
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            ${element}=  Right Click  name:MenuButton
        """
        return self._mouse_click(locator, "RightClick", wait_time, timeout)

    @keyword(tags=["action", "mouse"])
    def middle_click(
        self,
        locator: Locator,
        wait_time: Optional[float] = None,
        timeout: Optional[float] = None,
    ) -> WindowsElement:
        """Right mouse click on element matching given locator.

        Exception ``ActionNotPossible`` is raised if element does not
        allow Click action.

        :param locator: string locator or Control element
        :param wait_time: time to wait after click, default is a
         library `wait_time`, see keyword ``Set Wait Time``
        :param timeout: float value in seconds, see keyword
         ``Set Global Timeout``
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            ${element}=  Middle Click  name:button2
        """
        return self._mouse_click(locator, "MiddleClick", wait_time, timeout)

    def _mouse_click(self, element, click_type, wait_time, timeout):
        click_wait_time = wait_time or self.ctx.wait_time
        with self.set_timeout(timeout):
            element = self.ctx.get_element(element)
            if element.item.robocorp_click_offset:
                self.ctx.logger.debug("Click element with offset")
                self._click_element_coordinates(element, click_type, click_wait_time)
            else:
                self.ctx.logger.debug("Click element")
                self._click_element(element, click_type, click_wait_time)
        return element

    def _click_element_coordinates(self, element, click_type, click_wait_time):
        callable_attribute = hasattr(element.item, click_type)
        if callable_attribute:
            rect = element.item.BoundingRectangle
            offset_x, offset_y = [
                int(v) for v in element.item.robocorp_click_offset.split(",")
            ]
            getattr(element.item, click_type)(
                rect.xcenter() + offset_x,
                rect.ycenter() + offset_y,
                waitTime=click_wait_time,
            )
        else:
            raise ActionNotPossible(
                f"Element {element!r} does not have {click_type!r} attribute"
            )

    def _click_element(self, element, click_type, click_wait_time):
        attr = hasattr(element.item, click_type)
        if attr:
            getattr(element.item, click_type)(
                waitTime=click_wait_time,
                simulateMove=False,
            )
        else:
            raise ActionNotPossible(
                f"Element {element!r} does not have {click_type!r} attribute"
            )

    @keyword(tags=["action"])
    def select(self, locator: Locator, value: str) -> WindowsElement:
        """Select value on Control element if action is supported.

        Exception ``ActionNotPossible`` is raised if element does not
        allow Select action.

        :param locator: string locator or Control element
        :param value: string value to select on Control element
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            Select  type:SelectControl   option2
        """
        element = self.ctx.get_element(locator)
        if hasattr(element.item, "Select"):
            element.item.Select(value)
        else:
            raise ActionNotPossible(
                f"Element {locator!r} does not have 'Select' attribute"
            )
        return element

    @keyword(tags=["action"])
    def send_keys(
        self,
        locator: Optional[Locator] = None,
        keys: Optional[str] = None,
        interval: float = 0.01,
        wait_time: Optional[float] = None,
        send_enter: bool = False,
    ) -> WindowsElement:
        """Send keys to desktop, current window or to Control element
        defined by given locator.

        If ``locator`` is `None` then keys are sent to desktop.

        Exception ``ActionNotPossible`` is raised if element does not
        allow SendKeys action.

        :param locator: string locator or Control element (default None means desktop)
        :param keys: the keys to send
        :param interval: time between sending keys, default 0.01 seconds
        :param wait_time: time to wait after sending keys, default is a
         library `wait_time`, see keyword ``Set Wait Time``
        :param send_enter: if True then {Enter} is sent at the end of the keys
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            Send Keys  desktop   {Ctrl}{F4}
            Send Keys  keys={Ctrl}{F4}   # locator will be NONE, keys send to desktop
            ${element}=   Send Keys  id:input5  username   send_enter=True
            ${element}=   Get Element   id:pass
            Send Keys  ${element}  password   send_enter=True
        """
        if locator:
            element = self.ctx.get_element(locator).item
        else:
            element = auto
        keys_wait_time = wait_time or self.ctx.wait_time
        if send_enter:
            keys += "{Enter}"
        if hasattr(element, "SendKeys"):
            self.logger.info("Sending keys %r to element %r", keys, element)
            element.SendKeys(text=keys, interval=interval, waitTime=keys_wait_time)
        else:
            raise ActionNotPossible(
                f"Element found with {locator!r} does not have 'SendKeys' attribute"
            )

    @keyword
    def get_text(self, locator: Locator) -> str:
        """Get text from Control element defined by the locator.

        Exception ``ActionNotPossible`` is raised if element does not
        allow GetWindowText action.

        :param locator: string locator or Control element
        :return: value of WindowText attribute of an element

        Example:

        .. code-block:: robotframework

            ${date} =  Get Text   type:Edit name:"Date of birth"
        """
        element = self.ctx.get_element(locator)
        if hasattr(element.item, "GetWindowText"):
            return element.item.GetWindowText()
        raise ActionNotPossible(
            f"Element found with {locator!r} does not have 'GetWindowText' attribute"
        )

    @keyword
    def get_value(self, locator: Locator) -> str:
        """Get value of the element defined by the locator.

        Exception ``ActionNotPossible`` is raised if element does not
        allow GetValuePattern action.

        :param locator: string locator or Control element
        :return: value of ValuePattern attribute of an element

        Example:

        .. code-block:: robotframework

            ${value}=   Get Value   type:DataItem name:column1
        """
        element = self.ctx.get_element(locator)
        if hasattr(element.item, "GetValuePattern"):
            value_pattern = element.item.GetValuePattern()
            return value_pattern.Value
        raise ActionNotPossible(
            f"Element found with {locator!r} does not have 'GetValuePattern' attribute"
        )

    @keyword(tags=["action"])
    def set_value(
        self,
        locator: Optional[Locator] = None,
        value: Optional[str] = None,
        append: bool = False,
        enter: bool = False,
        newline: bool = False,
    ) -> WindowsElement:
        """Set value of the element defined by the locator.

        *Note.* Anchor works only on element structures where it can
        be relied on that root/child element tree will remain the same.
        Usually these kind of structures are tables.

        Exception ``ActionNotPossible`` is raised if element does not
        allow SetValue action.

        :param locator: string locator or Control element
        :param value: string value to set
        :param append: False for setting value, True for appending value
        :param enter: set True to press enter key at the end of the line
        :param newline: set True to add newline to the end of value
        :return: WindowsElement object

        *Note.* It is important to set ``append=True`` if you want keep text in
        the element. Other option is to read current text into a variable and
        modify that value to pass for ``Set Value`` keyword.

        Example:

        .. code-block:: robotframework

            Set Value   type:DataItem name:column1   ab c  # Set value to "ab c"
            # Press ENTER after setting the value
            Set Value    type:Edit name:"File name:"    console.txt    enter=True

            # Add newline (manually) at the end of the string (Notepad example)
            Set Value    name:"Text Editor"  abc\\n
            # Add newline with parameter
            Set Value    name:"Text Editor"  abc   newline=${True}

            # Clear Notepad window and start appending text
            Set Anchor  name:"Text Editor"
            # all following keyword calls will use anchor element as locator
            # UNLESS they specify locator specifically or `Clear Anchor` is used
            ${time}=    Get Time
            # Clears when append=False (default)
            Set Value    value=time now is ${time}
            # Append text and add newline to the end
            Set Value    value= and it's task run time    append=True    newline=True
            # Continue appending
            Set Value    value=this will appear on the 2nd line    append=True
        """
        value = value or ""
        element = self.ctx.get_element(locator)
        current_value = ""
        newline_string = "\n" if newline else ""
        if hasattr(element.item, "GetValuePattern"):
            value_pattern = element.item.GetValuePattern()
            if append:
                current_value = value_pattern.Value
            value_pattern.SetValue(f"{current_value}{value}{newline_string}")
        elif hasattr(element.item, "GetLegacyIAccessiblePattern"):
            pattern = element.item.GetLegacyIAccessiblePattern()
            if append:
                current_value = pattern.Value
            pattern.SetValue(f"{current_value}{value}{newline_string}")
        else:
            raise ActionNotPossible(
                f"Element found with {locator!r} doesn't support value setting"
            )
        if enter:
            self.send_keys(element, "{Ctrl}{End}{Enter}")
        return element

    @keyword
    def set_wait_time(self, wait_time: float) -> float:
        """Set library wait time for action keywords.

        The wait_time is spent after each keyword performing
        mouse or keyboard action.

        Library default wait_time is `0.5`

        Returns value of the previous wait_time value.

        :param wait_time: float value (in seconds), e.g. `0.1`
        :return: previous wait value

        Example:

        .. code-block:: robotframework

            ${old_wait_time}=  Set Wait Time  0.2
        """
        old_value = self.ctx.wait_time
        self.ctx.wait_time = wait_time
        return old_value

    @keyword
    def screenshot(self, locator: Locator, filename: str) -> str:
        """Take a screenshot of the element defined by the locator.

        Exception ``ActionNotPossible`` is raised if element does not
        allow CaptureToImage action.

        :param locator: string locator or Control element
        :param filename: image filename
        :return: absolute path to the screenshot file

        Example:

        .. code-block:: robotframework

            Screenshot  desktop   desktop.png
            Screenshot  subname:Notepad   notepad.png
        """
        element = self.ctx.get_element(locator)
        if not hasattr(element.item, "CaptureToImage"):
            raise ActionNotPossible(
                f"Element found with {locator!r} does not have 'CaptureToImage' "
                "attribute"
            )

        element.item.SetFocus()
        filepath = str(Path(filename).expanduser().resolve())
        element.item.CaptureToImage(filepath)
        return filepath

    @keyword
    def set_global_timeout(self, timeout: float) -> float:
        """Set global timeout for element search. Applies also
        to ``Control Window`` keyword.

        By default library has timeout of 10 seconds.

        :param timeout: float value in seconds
        :return: previous timeout value

        Example:

        .. code-block:: robotframework

            ${old_timeout}=  Set Global Timeout  20
            ${old_timeout}=  Set Global Timeout  9.5
        """
        previous_timeout = self.ctx.global_timeout
        self.ctx.global_timeout = timeout
        auto.SetGlobalSearchTimeout(self.ctx.global_timeout)
        return previous_timeout
