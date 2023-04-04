from dataclasses import dataclass
import time
from logging import getLogger
from timeit import default_timer as timer
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

import flet
from flet import Container, Page, ScrollMode
from flet_core import Checkbox, Column, Control, AppBar, Row, Stack
from flet_core.control_event import ControlEvent
from typing_extensions import Literal

from RPA.Assistant.background_flet import BackgroundFlet
from RPA.Assistant.types import (
    LayoutError,
    PageNotOpenError,
    Result,
    SupportedFletLayout,
    WindowLocation,
)


def resolve_absolute_position(
    location: Union[WindowLocation, Tuple],
) -> Tuple[int, int]:

    if location is WindowLocation.TopLeft:
        return (0, 0)
    elif isinstance(location, tuple):
        return location
    else:
        raise ValueError(f"Invalid location {location}")


class TimeoutException(RuntimeError):
    """Timeout while waiting for dialog to finish."""


@dataclass
class Elements:
    """Lists of visible and invisible control elements"""

    visible: List[Control]
    visible_by_name: Dict[str, Control]
    invisible: List[Control]
    app_bar: Optional[AppBar]
    used_names: Set[str]


class FletClient:
    """Class for wrapping flet operations"""

    def __init__(self) -> None:
        self.logger = getLogger(__name__)
        self.results: Result = {}
        self.page: Optional[Page] = None
        self.pending_operation: Optional[Callable] = None

        self._elements: Elements = Elements([], {}, [], None, set())
        self._to_disable: List[flet.Control] = []
        self._layout_stack: List[Union[SupportedFletLayout, AppBar]] = []

        self._background_flet = BackgroundFlet()

    def _create_flet_target_function(
        self,
        title: str,
        height: Union[int, Literal["AUTO"]],
        width: int,
        on_top: bool,
        location: Union[WindowLocation, Tuple[int, int], None],
    ) -> Callable[[Page], None]:
        def inner_execute(page: Page):
            page.title = title
            if height != "AUTO":
                page.window_height = height
            page.window_width = width
            page.window_always_on_top = on_top

            # TODO: do we even allow None as argument?
            # or some Location.AUTO which would let OS handle position?
            if location is not None:
                if location is WindowLocation.Center:
                    page.window_center()
                else:
                    coordinates = resolve_absolute_position(location=location)
                    page.window_left = coordinates[0]
                    page.window_top = coordinates[1]
            page.scroll = ScrollMode.AUTO
            page.on_disconnect = lambda _: self._background_flet.close_flet_view()
            self.page = page
            self.update_elements()

        return inner_execute

    def _show_flet(
        self,
        target: Callable[[Page], None],
        timeout: int,
    ):
        self._background_flet.start_flet_view(target)
        view_start_time = timer()
        try:
            while self._background_flet.poll() is None:
                if callable(self.pending_operation):
                    self.pending_operation()  # pylint: disable=not-callable
                    self.pending_operation = None
                if timer() - view_start_time >= timeout:
                    self._background_flet.close_flet_view()
                    raise TimeoutException(
                        "Reached timeout while waiting for Assistant Dialog"
                    )
                time.sleep(0.1)
        except TimeoutException:
            # pylint: disable=raise-missing-from
            raise TimeoutException("Reached timeout while waiting for Assistant Dialog")
        finally:
            # Control's can't be re-used on multiple pages so we remove the page and
            # clear elements after flet closes
            self.page = None
            self.clear_elements()
            self._to_disable.clear()

    def _checkbox_data_saver(self, name: str, handler: Optional[Callable] = None):
        """_make_on_change_data_saver special case for checkboxes, until
        https://github.com/flet-dev/flet/issues/1251 is fixed"""

        def handle_string_bool(bool_string: Literal["true", "false"]):
            if bool_string == "true":
                return True
            elif bool_string == "false":
                return False
            else:
                raise ValueError(f"Invalid checkbox value {bool_string}")

        # We don't want the if inside the change_listener so it doesn't have to run on
        # every on_change event
        if not handler:

            def change_listener(e: ControlEvent):
                self.results[name] = handle_string_bool(e.data)

        else:

            def change_listener(e: ControlEvent):
                handler(e)
                self.results[name] = handle_string_bool(e.data)

        return change_listener

    def _make_on_change_data_saver(
        self, name: str, handler: Optional[Callable] = None
    ) -> Callable[[ControlEvent], None]:
        """Add flet event handler to record the element's data whenever content changes
        if ``handler`` is provided also call that.
        """

        # We don't want the if inside the change_listener so it doesn't have to run on
        # every on_change event
        if not handler:

            def change_listener(e: ControlEvent):
                self.results[name] = e.data

        else:

            def change_listener(e: ControlEvent):
                handler(e)
                self.results[name] = e.data

        return change_listener

    def _add_child_to_layout(self, child: Control):
        current_layout = self._layout_stack[-1]
        if isinstance(current_layout, (Row, Stack, Column)):
            current_layout.controls.append(child)
        elif isinstance(current_layout, AppBar):
            current_layout.actions.append(child)
        elif isinstance(current_layout, Container):
            if current_layout.content is not None:
                raise LayoutError("Attempting to place two content in one Container")
            current_layout.content = child
        else:
            raise RuntimeError("Unsupported layout element")

    def add_element(
        self,
        element: flet.Control,
        name: Optional[str] = None,
        extra_handler: Optional[Callable] = None,
        validation_func: Optional[Callable] = None,
    ):
        if name in self._elements.used_names:
            raise ValueError(f"Name `{name}` already in use")

        # if added element is a Container we don't create our own margin container to
        # not override added containers properties.
        if isinstance(element, Container):
            new_element = element
        else:
            # make a container that adds margin around the element
            new_element = Container(margin=5, content=element)

        if self._layout_stack:
            self._add_child_to_layout(new_element)
        else:
            self._elements.visible.append(new_element)

        if name is not None:
            self._elements.visible_by_name[name] = element
            self._elements.used_names.add(name)

            if isinstance(element, Checkbox):
                on_change_data_saver = self._checkbox_data_saver(name, extra_handler)

            else:
                on_change_data_saver = self._make_on_change_data_saver(
                    name, extra_handler
                )

            def on_change(event):
                if validation_func:
                    validation_func(event)
                on_change_data_saver(event)

            element.on_change = on_change

    def add_invisible_element(self, element: flet.Control, name: Optional[str] = None):
        self._elements.invisible.append(element)
        if name is not None:
            element.on_change = self._make_on_change_data_saver(name)

    def display_flet_window(
        self,
        title: str,
        height: Union[int, Literal["AUTO"]],
        width: int,
        on_top: bool,
        location: Union[WindowLocation, Tuple[int, int], None],
        timeout: int,
    ):
        self._show_flet(
            self._create_flet_target_function(title, height, width, on_top, location),
            timeout,
        )

    def clear_elements(self):
        self._elements = Elements([], {}, [], None, set())
        if self.page:
            if self.page.controls:
                self.page.controls.clear()
            self.page.overlay.clear()
            self.page.update()

    def update_elements(self):
        """Updates the UI and shows new elements which have been added into the element
        lists
        """
        if not self.page:
            raise PageNotOpenError("No page open when update_elements was called")

        # invisible elements have to be added before visible ones, for file pickers
        # to work correctly
        for element in self._elements.invisible:
            self.page.overlay.append(element)
        for element in self._elements.visible:
            self.page.add(element)
        if self._elements.app_bar:
            self.page.appbar = self._elements.app_bar
        self.page.update()

    def flet_update(self):
        """Runs a plain update of the flet UI, updating existing elements"""
        if not self.page:
            raise PageNotOpenError("Flet update called when page is not open")
        self.page.update()

    def lock_elements(self):
        for element in self._to_disable:
            element.disabled = True

    def unlock_elements(self):
        for element in self._to_disable:
            element.disabled = False

    def add_to_disablelist(self, element: flet.Control):
        """Added elements will be disabled when code is running from buttons"""
        self._to_disable.append(element)

    def set_title(self, title: str):
        """Set flet dialog title when it is running."""
        if not self.page:
            raise PageNotOpenError("Set title called when page is not open")
        self.page.title = title

    def add_layout(self, layout: SupportedFletLayout):
        """Add a layout element as the currently open layout element. Following
        add_element calls will add elements inside ``layout``."""
        self.add_element(layout)
        self._layout_stack.append(layout)

    def close_layout(self):
        """Stop adding layout elements to the latest opened layout"""
        self._layout_stack.pop()

    def set_appbar(self, app_bar: AppBar):
        if self._elements.app_bar:
            raise LayoutError("Only one navigation may be defined at a time")
        self._elements.app_bar = app_bar
        self._layout_stack.append(app_bar)

    def get_layout_dimensions(self) -> Tuple[Optional[float], Optional[float]]:
        if len(self._layout_stack) == 0:
            raise LayoutError("No parent element to determine dimensions from")
        current_layout = self._layout_stack[-1]
        if isinstance(current_layout, AppBar):
            raise LayoutError("Cannot use absolute positions in appbar")
        if current_layout.width is None or current_layout.height is None:
            raise RuntimeError("Cannot determine dimensions of parent element")

        return (current_layout.width, current_layout.height)

    def set_error(self, element_name: str, error: str):
        """Set an error for an element. The element must be a TextField or other
        Control that has error_text attribute."""
        element = self._elements.visible_by_name[element_name]
        if not hasattr(element, "error_text"):
            raise RuntimeError(
                "Tried to set error for element that does not have error_text attribute"
            )
        element.error_text = error
        self.flet_update()
