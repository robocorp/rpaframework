from enum import Enum
from typing import Optional, Any, Union
from RPA.core.helpers import delay
from RPA.core.geometry import Point, Region
from RPA.Desktop.keywords import LibraryContext, keyword


class Action(Enum):
    """Possible mouse click actions."""

    click = 0
    left_click = 0
    double_click = 1
    triple_click = 2
    right_click = 3


def to_action(value):
    """Convert value to Action enum."""
    if isinstance(value, Action):
        return value

    sanitized = str(value).lower().strip().replace(" ", "_")
    try:
        return Action[sanitized]
    except KeyError as err:
        raise ValueError(f"Unknown mouse action: {value}") from err


def to_button(value):
    """Convert value to Button enum."""
    # pylint: disable=C0415
    from pynput.mouse import Button

    if isinstance(value, Button):
        return value

    sanitized = str(value).lower().strip().replace(" ", "_")
    try:
        return Button[sanitized]
    except KeyError as err:
        raise ValueError(f"Unknown mouse button: {value}") from err


class MouseKeywords(LibraryContext):
    """Keywords for sending inputs through an (emulated) mouse."""

    def __init__(self, ctx):
        super().__init__(ctx)
        try:
            # pylint: disable=C0415
            from pynput.mouse import Controller

            self._mouse = Controller()
            self._error = None
        except ImportError as exc:
            self._error = exc

    def _move(self, point: Point) -> None:
        """Move mouse to given point."""
        # TODO: Clamp to screen dimensions?
        self.logger.info("Moving mouse to (%d, %d)", *point)
        self._mouse.position = point.as_tuple()

    def _click(
        self,
        action: Action = Action.click,
        location: Optional[Union[Point, Region]] = None,
    ) -> None:
        """Perform defined mouse action, and optionally move to given point first."""
        # pylint: disable=C0415
        from pynput.mouse import Button

        action = to_action(action)

        if location:
            if isinstance(location, Region):
                self._move(location.center)
            else:
                self._move(location)
            # Delay is needed, otherwise move might not have "completed" before clicking
            delay(0.05)

        self.logger.info("Performing mouse action: %s", action)

        if action is Action.click:
            self._mouse.click(Button.left)
        elif action is Action.double_click:
            self._mouse.click(Button.left, 2)
        elif action is Action.triple_click:
            self._mouse.click(Button.left, 3)
        elif action is Action.right_click:
            self._mouse.click(Button.right)
        else:
            # TODO: mypy should handle enum exhaustivity validation
            raise ValueError(f"Unsupported action: {action}")

    @keyword
    def click(
        self,
        locator: Optional[str] = None,
        action: Action = Action.click,
    ) -> None:
        """Click at the element indicated by locator.

        :param locator: Locator for click position
        :param action:  Click action, e.g. right click

        Example:

        .. code-block:: robotframework

            Click
            Click    LoginForm.Button
            Click    coordinates:500,200    triple click
        """
        if self._error:
            raise self._error
        action = to_action(action)
        if locator:
            match = self.ctx.find_element(locator)
            self._click(action, match)
        else:
            self._click(action)

    @keyword
    def click_with_offset(
        self,
        locator: Optional[str] = None,
        x: int = 0,
        y: int = 0,
        action: Action = Action.click,
    ) -> None:
        """Click at a given pixel offset from the given locator.

        :param locator: Locator for click start position
        :param x:       Click horizontal offset in pixels
        :param y:       Click vertical offset in pixels
        :param action:  Click action, e.g. right click

        Example:

        .. code-block:: robotframework

            Click with offset    Robocorp.Logo    y=400
        """
        if self._error:
            raise self._error
        action = to_action(action)
        if locator:
            match = self.ctx.find_element(locator)
            match.offset(x, y)
            self._click(action, match)
        else:
            self._mouse.move(int(x), int(y))
            self._click(action)

    @keyword
    def get_mouse_position(self) -> Point:
        """Get current mouse position in pixel coordinates.

        Example:

        .. code-block:: robotframework

            ${position}=    Get mouse position
            Log    Current mouse position is ${position.x}, ${position.y}
        """
        if self._error:
            raise self._error
        x, y = self._mouse.position
        return Point(x, y)

    @keyword
    def move_mouse(self, locator: str) -> None:
        """Move mouse to given coordinates.

        :param locator: Locator for mouse position

        Example:

        .. code-block:: robotframework

            Move mouse    Robocorp.Logo
            Move mouse    offset:0,400
        """
        if self._error:
            raise self._error
        match = self.ctx.find_element(locator)
        self._move(match)

    @keyword
    def press_mouse_button(self, button: Any = "left") -> None:
        """Press down mouse button and keep it pressed."""
        if self._error:
            raise self._error
        button = to_button(button)
        self._mouse.press(button)

    @keyword
    def release_mouse_button(self, button: Any = "left") -> None:
        """Release mouse button that was previously pressed."""
        if self._error:
            raise self._error
        button = to_button(button)
        self._mouse.release(button)

    @keyword
    def drag_and_drop(
        self,
        source: str,
        destination: str,
        start_delay: float = 2.0,
        end_delay: float = 0.5,
    ) -> None:
        """Drag mouse from source to destination while holding the left mouse button.

        :param source:      Locator for start position
        :param destination: Locator for destination position
        :param start_delay: Delay in seconds after pressing down mouse button
        :param end_delay:   Delay in seconds before releasing mouse button
        """
        if self._error:
            raise self._error
        src = self.ctx.find_element(source)
        dst = self.ctx.find_element(destination)

        self.logger.info("Dragging from (%d, %d) to (%d, %d)", *src, *dst)

        self._move(src)
        self.press_mouse_button()
        delay(start_delay)
        self._move(dst)
        delay(end_delay)
        self.release_mouse_button()
