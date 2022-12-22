import atexit
import logging
import os
import signal
from types import NoneType
from typing import Callable, List, Optional, Union

import flet
from flet import Control, Page, ScrollMode
from flet.utils import is_windows

from .dialog_types import Result


class FletEvent:
    target: str
    name: str
    data: str
    control: Control
    page: Page


class FletClient:
    def __init__(self) -> None:
        self._conn = self._preload_flet()
        self.elements: List[List[Control]] = [[]]
        self.invisible_elements: List[List[Control]] = [[]]
        self.results: Result = {}
        self._pagination = 0
        self.page: Optional[Page] = None
        self._fvp = None
        atexit.register(self._cleanup)

    @property
    def current_elements(self):
        return self.elements[self._pagination]

    @property
    def current_invisible_elements(self):
        return self.invisible_elements[self._pagination]

    def _cleanup(self) -> None:
        # Source: https://github.com/flet-dev/flet/blob/89364edec81f0f9591a37bdba5f704215badb0d3/sdk/python/flet/flet.py#L146
        self._conn.close()
        if self._fvp is not None and not is_windows():
            try:
                logging.debug(f"Flet View process {self._fvp.pid}")
                os.kill(self._fvp.pid + 1, signal.SIGKILL)
            except:
                pass

    def _execute(
        self, page: Optional[Page] = None
    ) -> Callable[[Optional[Page]], NoneType]:
        def inner_execute(inner_page: Optional[Page] = None):
            if page:
                inner_page = page
            for element in self.current_elements:
                inner_page.add(element)
            for element in self.current_invisible_elements:
                inner_page.overlay.append(element)
            # self.add
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
            assets_dir=None,
            upload_dir=None,
            web_renderer="canvaskit",
            route_url_strategy="hash",
        )

    def _show_flet(
        self,
        target,
        title: str = "Dialog",
        height: Union[int, str] = "AUTO",
        width: int = 480,
        on_top: bool = False,
    ):
        def on_session_created(conn, session_data):
            page = Page(conn, session_data.sessionID)
            page.title = title
            if height != "AUTO":
                page.window_height = height
            page.window_width = width
            page.window_always_on_top = on_top
            conn.sessions[session_data.sessionID] = page
            try:
                assert target is not None
                target(page)
            except Exception as e:
                page.error(f"There was an error while rendering the page: {e}")

        self._conn.on_session_created = on_session_created
        self._fvp = flet.flet._open_flet_view(self._conn.page_url, False)
        try:
            self._fvp.wait()
        except Exception:
            pass

    def _make_flet_event_handler(self, name: str):
        def change_listener(e: FletEvent):
            self.results[name] = e.data
            e.page.update()

        return change_listener

    def add_element(self, element: flet.Control, name: Optional[str] = None):
        # TODO: validate that element "name" is unique
        self.elements[-1].append(element)
        if name is not None:
            # TODO: might be necessary to check that it doesn't already have change handler
            element.on_change = self._make_flet_event_handler(name)
            # element._add_event_handler("change", self._make_flet_event_handler(name))

    def add_invisible_element(self, element: flet.Control, name: Optional[str] = None):
        self.invisible_elements[-1].append(element)
        if name is not None:
            element.on_change = self._make_flet_event_handler(name)

    def display_flet_window(
        self,
        title: str = "Dialog",
        height: Union[int, str] = "AUTO",
        width: int = 480,
        on_top: bool = False,
    ):
        self._show_flet(self._execute(), title, height, width, on_top)

    def clear_elements(self):
        if self.page:
            self.page.controls.clear()
            self.page.overlay.clear()
            self.page.update()
        self.elements[self._pagination] = []
        self.invisible_elements[self._pagination] = []
        return

    def update_elements(self, page):
        return self._execute(page)()
