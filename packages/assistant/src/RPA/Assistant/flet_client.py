import atexit
import logging
import os
import signal
from subprocess import TimeoutExpired
from typing import Callable, List, Optional, Union, Literal, Tuple

import flet
from flet import Control, Page, ScrollMode
from flet.utils import is_windows

from RPA.Assistant.types import Result, Location


def resolve_absolute_position(
    location: Union[Location, Tuple],
) -> Tuple[int, int]:

    if location is Location.TopLeft:
        return (0, 0)
    elif isinstance(location, tuple):
        return location
    else:
        raise ValueError(f"Invalid location {location}")


class FletEvent:
    target: str
    name: str
    data: str
    control: Control
    page: Page

class TimeoutException(RuntimeError):
    """Timeout while waiting for dialog to finish."""

class FletClient:
    """Class for wrapping flet operations"""

    def __init__(self) -> None:
        self.results: Result = {}
        self.page: Optional[Page] = None

        self._conn = self._preload_flet()
        self._elements: List[List[Control]] = [[]]
        self._invisible_elements: List[List[Control]] = [[]]
        self._pagination = 0
        self._fvp = None
        atexit.register(self._cleanup)

    @property
    def current_elements(self):
        return self._elements[self._pagination]

    @property
    def current_invisible_elements(self):
        return self._invisible_elements[self._pagination]

    def _cleanup(self) -> None:
        # Source: https://github.com/flet-dev/flet/blob/89364edec81f0f9591a37bdba5f704215badb0d3/sdk/python/flet/flet.py#L146
        self._conn.close()
        if self._fvp is not None and not is_windows():
            try:
                logging.debug(f"Flet View process {self._fvp.pid}")
                os.kill(self._fvp.pid + 1, signal.SIGKILL)
            except:
                pass

    def _execute(self, page: Optional[Page] = None) -> Callable[[Optional[Page]], None]:
        """TODO: document what this does exactly"""

        def inner_execute(inner_page: Optional[Page] = None):
            if page:
                inner_page = page
            for element in self.current_elements:
                inner_page.add(element)
            for element in self.current_invisible_elements:
                inner_page.overlay.append(element)
            inner_page.scroll = ScrollMode.AUTO
            self.page = inner_page
            inner_page.update()

        return inner_execute

    def _preload_flet(self):
        return flet.flet._connect_internal(
            page_name="",
            host=None,
            port=0,
            is_app=True,
            permissions=None,
            assets_dir="/",
            upload_dir=None,
            web_renderer="canvaskit",
            route_url_strategy="hash",
        )

    def _show_flet(
        self,
        target,
        title: str,
        height: Union[int, Literal["AUTO"]],
        width: int,
        on_top: bool,
        location: Union[Location, Tuple[int, int], None],
        timeout: int,
    ):
        def on_session_created(conn, session_data):
            page = Page(conn, session_data.sessionID)
            page.title = title
            if height != "AUTO":
                page.window_height = height
            page.window_width = width
            page.window_always_on_top = on_top

            # TODO: do we even allow None as argument?
            # or some Location.AUTO which would let OS handle position?
            if location is not None:
                if location is Location.Center:
                    page.window_center()
                else:
                    coordinates = resolve_absolute_position(location=location)
                    page.window_left = coordinates[0]
                    page.window_top = coordinates[1]
            conn.sessions[session_data.sessionID] = page
            try:
                assert target is not None
                target(page)
            except Exception as e:
                page.error(f"There was an error while rendering the page: {e}")

        self._conn.on_session_created = on_session_created
        self._fvp = flet.flet._open_flet_view(self._conn.page_url, False)
        try:
            self._fvp.wait(timeout=timeout)
        except TimeoutExpired:
            raise TimeoutException("Reached timeout while waiting for Assistant Dialog")
        except Exception:
            pass

    def _make_flet_event_handler(self, name: str):
        def change_listener(e: FletEvent):
            self.results[name] = e.data
            e.page.update()

        return change_listener

    def add_element(self, element: flet.Control, name: Optional[str] = None):
        # TODO: validate that element "name" is unique
        self._elements[-1].append(element)
        if name is not None:
            # TODO: might be necessary to check that it doesn't already have change handler
            element.on_change = self._make_flet_event_handler(name)
            # element._add_event_handler("change", self._make_flet_event_handler(name))

    def add_invisible_element(self, element: flet.Control, name: Optional[str] = None):
        self._invisible_elements[-1].append(element)
        if name is not None:
            element.on_change = self._make_flet_event_handler(name)

    def display_flet_window(
        self,
        title: str,
        height: Union[int, Literal["AUTO"]],
        width: int,
        on_top: bool,
        location: Union[Location, Tuple[int, int], None],
        timeout: int
    ):
        self._show_flet(self._execute(), title, height, width, on_top, location, timeout)

    def clear_elements(self):
        if self.page:
            self.page.controls.clear()
            self.page.overlay.clear()
            self.page.update()
        self._elements[self._pagination] = []
        self._invisible_elements[self._pagination] = []
        return

    def update_elements(self, page: Page):
        """Updates the UI and shows new elements which have been added into the element lists"""
        return self._execute(page)()

    def flet_update(self):
        """Runs a plain update of the flet UI, updating existing elements"""
        if not self.page:
            raise Exception("Flet update called when page is not open")
        self.page.update()
