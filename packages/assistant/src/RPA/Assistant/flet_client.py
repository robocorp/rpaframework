import time
from logging import getLogger
from timeit import default_timer as timer
from typing import Callable, List, NamedTuple, Optional, Tuple, Union

import flet
from flet import Container, Page, ScrollMode
from flet_core import Control
from flet_core.control_event import ControlEvent
from typing_extensions import Literal

from RPA.Assistant.background_flet import BackgroundFlet
from RPA.Assistant.types import Result, WindowLocation


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


class Elements(NamedTuple):
    """Lists of visible and invisible control elements"""

    visible: List[Control]
    invisible: List[Control]


class FletClient:
    """Class for wrapping flet operations"""

    def __init__(self) -> None:
        self.logger = getLogger(__name__)
        self.results: Result = {}
        self.page: Optional[Page] = None
        self.pending_operation: Optional[Callable] = None

        self._elements: Elements = Elements([], [])
        self._to_disable: List[flet.Control] = []

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

    def _make_flet_event_handler(self, name: str, handler: Optional[Callable] = None):
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

    def add_element(
        self,
        element: flet.Control,
        name: Optional[str] = None,
        extra_handler: Optional[Callable] = None,
    ):
        # TODO: validate that element "name" is unique
        # make a container that adds margin around the element
        container = Container(margin=5, content=element)
        self._elements.visible.append(container)
        if name is not None:
            element.on_change = self._make_flet_event_handler(name, extra_handler)

    def add_invisible_element(self, element: flet.Control, name: Optional[str] = None):
        self._elements.invisible.append(element)
        if name is not None:
            element.on_change = self._make_flet_event_handler(name)

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
        self._elements.visible.clear()
        self._elements.invisible.clear()
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
            raise ValueError("No page open when update_elements was called")

        for element in self._elements.visible:
            self.page.add(element)
        for element in self._elements.invisible:
            self.page.overlay.append(element)
        self.page.update()

    def flet_update(self):
        """Runs a plain update of the flet UI, updating existing elements"""
        if not self.page:
            raise RuntimeError("Flet update called when page is not open")
        self.page.update()

    def lock_elements(self):
        for element in self._to_disable:
            element.disabled = True

    def unlock_elements(self):
        for element in self._to_disable:
            element.disabled = False

    def add_to_disablelist(self, element: flet.Control):
        """added elements will be disabled when code is running from buttons"""
        self._to_disable.append(element)
