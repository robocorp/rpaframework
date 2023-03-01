from pathlib import Path
from typing import Callable, Optional

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

    def _mouse_click(
        self,
        locator: Locator,
        click_type: str,
        wait_time: Optional[float],
        timeout: Optional[float],
    ) -> WindowsElement:
        click_wait_time: float = wait_time or self.ctx.wait_time
        with self.set_timeout(timeout):
            element = self.ctx.get_element(locator)
            self._click_element(element, click_type, click_wait_time)
        return element

    def _click_element(
        self, element: WindowsElement, click_type: str, click_wait_time: float
    ):
        item = element.item
        click_function = getattr(item, click_type, None)
        if not click_function:
            raise ActionNotPossible(
                f"Element {element!r} does not have {click_type!r} attribute"
            )

        # Attribute added in `RPA.core.windows.locators.LocatorMethods`.
        offset: Optional[str] = item.robocorp_click_offset
        offset_x: Optional[int] = None
        offset_y: Optional[int] = None
        log_message = f"{click_type}-ing element"
        if offset:
            # Get a new fresh bounding box each time, since the element might have been
            #  moved from its initial spot.
            rect = item.BoundingRectangle
            # Now compute the new coordinates starting from the element center.
            dist_x, dist_y = (int(dist.strip()) for dist in offset.split(","))
            pos_x, pos_y = rect.xcenter() + dist_x, rect.ycenter() + dist_y
            # If we pass the newly obtained absolute position to the clicking function
            #  that won't work as expected. You see (`help(item.Click)`), if the passed
            #  offset is positive then it gets relative to the left-top corner and if
            #  is negative then the right-bottom corner is used.
            # Let's assume we end up with a positive relative offset. (using left-top
            #  fixed corner)
            offset_x, offset_y = pos_x - rect.left, pos_y - rect.top
            # If by any chance an offset is negative, it gets relative to the
            #  right-bottom corner, therefore adjust it accordingly.
            if offset_x < 0:
                offset_x -= rect.width()
            if offset_y < 0:
                offset_y -= rect.height()
            log_message += f" with offset: {offset_x}, {offset_y}"

        self.logger.debug(log_message)
        click_function(
            x=offset_x,
            y=offset_y,
            simulateMove=self.ctx.simulate_move,
            waitTime=click_wait_time,
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
            # NOTE(cmin764): This is not supposed to work on `*Pattern` or `TextRange`
            #  objects. (works with `Control`s and its derived flavors only)
            element.item.Select(
                value, simulateMove=self.ctx.simulate_move, waitTime=self.ctx.wait_time
            )
        else:
            raise ActionNotPossible(
                f"Element {locator!r} does not have 'Select' attribute"
            )
        return element

    @keyword(tags=["action", "keyboard"])
    def send_keys(
        self,
        locator: Optional[Locator] = None,
        keys: Optional[str] = None,
        interval: float = 0.01,
        wait_time: Optional[float] = None,
        send_enter: bool = False,
    ):
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
            Send Keys  id:input5  username   send_enter=True
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

    @keyword(tags=["action"])
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

    @keyword(tags=["action"])
    def get_value(self, locator: Locator) -> Optional[str]:
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
            return value_pattern.Value if value_pattern else None

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
        send_keys_fallback: bool = False,
    ) -> WindowsElement:
        """Set value of the element defined by the locator.

        *Note:* Anchor works only on element structures where it can
        be relied on that root/child element tree, as remaining the same.
        Usually these kind of structures are tables.

        *Note:* It is important to set ``append=${True}`` if you want to keep the
        current text in the element. Other option is to read the current text into a
        variable, then modify that value as you wish and pass it to the ``Set Value``
        keyword for text replacement.

        The following exceptions are raised:

            - ``ActionNotPossible`` if the element does not allow the `SetValue` action
              to be run on it nor having ``send_keys_fallback=${True}``.
            - ``ValueError`` if the new value to be set can't be set.

        :param locator: String locator or element object.
        :param value: String value to be set.
        :param append: `False` for setting the value, `True` for appending it. (OFF by
            default)
        :param enter: Set it to `True` to press the *Enter* key at the end of the line.
            (nothing is pressed by default)
        :param newline: Set it to `True` to add a new line at the end of the value. (no
            default EOL)
        :param send_keys_fallback: Tries to set the value by sending it through keys
            if the expected way of setting it fails. (disabled by default)
        :returns: The `WindowsElement` object identified through the passed `locator`.

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Set Values In Notepad
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
                Set Value    value= and it's task run time   append=True  newline=True
                # Continue appending
                Set Value    value=this will appear on the 2nd line    append=True
        """
        value = value or ""
        if newline and enter:
            self.logger.warning(
                "Both `newline` and `enter` switches detected, expect to see multiple"
                " new lines in the final text area."
            )
        newline_string = "\n" if newline else ""
        element = self.ctx.get_element(locator)
        item = element.item
        get_pattern: Optional[Callable] = getattr(
            item, "GetValuePattern", getattr(item, "GetLegacyIAccessiblePattern", None)
        )
        action = "Appending" if append else "Setting"

        if get_pattern:
            func_name = get_pattern.__name__
            self.logger.info(
                "%s the element value with the %r method.", action, func_name
            )
            value_pattern = get_pattern()
            current_value = value_pattern.Value if append else ""
            new_value = f"{current_value}{value}{newline_string}"
            value_pattern.SetValue(new_value)
            if value_pattern.Value != new_value:
                raise ValueError(
                    f"Element found with {locator!r} can't set value: {new_value}"
                )
        elif send_keys_fallback:
            self.logger.info(
                "%s the element value with `Send Keys`. (no patterns found)", action
            )
            if newline_string:
                self.logger.warning(
                    "The `newline` switch is ignored when setting a value"
                    " through keys! (enable it with the `enter` parameter only)"
                )
            self.send_keys(element, keys=value, send_enter=False)
        else:
            raise ActionNotPossible(
                f"Element found with {locator!r} doesn't support value setting"
            )

        if enter:
            self.logger.info("Inserting a new line by sending the *Enter* key.")
            self.send_keys(element, keys="{Ctrl}{End}{Enter}")

        return element

    @keyword(tags=["action"])
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
        self.logger.info("Previous wait time: %f", old_value)
        self.ctx.wait_time = wait_time
        self.logger.info("Current wait time: %f", self.ctx.wait_time)
        return old_value

    @keyword(tags=["action"])
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

    @keyword(tags=["action"])
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

    @keyword(tags=["action"])
    def set_focus(self, locator: Locator) -> None:
        """Set view focus to the element defined by the locator.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            Set Focus  name:Buy type:Button
        """
        element = self.ctx.get_element(locator)
        if not hasattr(element.item, "SetFocus"):
            raise ActionNotPossible(
                f"Element found with {locator!r} does not have 'SetFocus' attribute"
            )
        element.item.SetFocus()

    @keyword(tags=["action", "mouse"])
    def drag_and_drop(
        self,
        source_element: Locator,
        target_element: Locator,
        speed: Optional[float] = 1.0,
        copy: Optional[bool] = False,
        wait_time: Optional[float] = 1.0,
    ):
        """Drag and drop the source element into target element.

        :param source: source element for the operation
        :param target: target element for the operation
        :param speed: adjust speed of operation, bigger value means more speed
        :param copy: on True does copy drag and drop, defaults to move
        :param wait_time: time to wait after drop, default 1.0 seconds

        Example:

        .. code-block:: robotframework

            # copying a file, report.html, from source (File Explorer) window
            # into a target (File Explorer) Window
            # locator
            Drag And Drop
            ...    name:C:\\temp type:Windows > name:report.html type:ListItem
            ...    name:%{USERPROFILE}\\Documents\\artifacts type:Windows > name:"Items View"
            ...    copy=True

        Example:

        .. code-block:: robotframework

            # moving *.txt files into subfolder within one (File Explorer) window
            ${source_dir}=    Set Variable    %{USERPROFILE}\\Documents\\test
            Control Window    name:${source_dir}
            ${files}=    Find Files    ${source_dir}${/}*.txt
            # first copy files to folder2
            FOR    ${file}    IN    @{files}
                Drag And Drop    name:${file.name}    name:folder2 type:ListItem    copy=True
            END
            # second move files to folder1
            FOR    ${file}    IN    @{files}
                Drag And Drop    name:${file.name}    name:folder1 type:ListItem
            END
        """  # noqa: E501
        source = self.ctx.get_element(source_element)
        target = self.ctx.get_element(target_element)
        try:
            if copy:
                auto.PressKey(auto.Keys.VK_CONTROL)
            auto.DragDrop(
                source.xcenter,
                source.ycenter,
                target.xcenter,
                target.ycenter,
                moveSpeed=speed,
                waitTime=wait_time,
            )
        finally:
            if copy:
                self.click(source)
                auto.ReleaseKey(auto.Keys.VK_CONTROL)

    @keyword(tags=["action"])
    def set_mouse_movement(self, simulate: bool) -> bool:
        """Enable or disable mouse movement simulation during clicks and other actions.

        Returns the previous set value as `True`/`False`.

        :param simulate: Decide whether to simulate the move. (ON by default)
        :returns: Previous state.

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Disable Mouse Move
                ${previous} =   Set Mouse Movement      ${False}
                Log To Console   Previous mouse simulation: ${previous} (now disabled)

        **Example: Python**

        .. code-block:: python

            from RPA.Windows import Windows

            lib_win = Windows()
            previous = lib_win.set_mouse_movement(False)
            print(f"Previous mouse simulation: {previous} (now disabled)")
        """
        to_str = lambda state: "ON" if state else "OFF"  # noqa: E731
        previous = self.ctx.simulate_move
        self.logger.info("Previous mouse movement simulation: %s", to_str(previous))
        self.ctx.simulate_move = simulate
        self.logger.info(
            "Current mouse movement simulation: %s", to_str(self.ctx.simulate_move)
        )
        return previous
