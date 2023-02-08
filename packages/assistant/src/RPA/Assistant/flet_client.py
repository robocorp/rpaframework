import atexit
from logging import getLogger
import os
import signal
import time
from collections import namedtuple
from subprocess import Popen, SubprocessError
from timeit import default_timer as timer
from typing import Callable, Literal, Optional, Tuple, Union, List

import flet
from flet import Page, ScrollMode
from flet.control_event import ControlEvent
from flet.utils import is_windows, is_macos
from RPA.Assistant.types import Location, Result

from RPA.Assistant.utils import nix_get_pid


def resolve_absolute_position(
    location: Union[Location, Tuple],
) -> Tuple[int, int]:

    if location is Location.TopLeft:
        return (0, 0)
    elif isinstance(location, tuple):
        return location
    else:
        raise ValueError(f"Invalid location {location}")


class TimeoutException(RuntimeError):
    """Timeout while waiting for dialog to finish."""


Elements = namedtuple("Elements", ["visible", "invisible"])


class FletClient:
    """Class for wrapping flet operations"""

    def __init__(self) -> None:
        atexit.register(self._cleanup)
        self.logger = getLogger(__name__)
        self.results: Result = {}
        self.page: Optional[Page] = None
        self.pending_operation: Optional[Callable] = None

        self._conn = None
        self._elements: Elements = Elements([], [])
        self._to_disable: List[flet.Control] = []
        self._fvp: Optional[Popen] = None

    def _cleanup(self) -> None:
        # Source: https://github.com/flet-dev/flet/blob/89364edec81f0f9591a37bdba5f704215badb0d3/sdk/python/flet/flet.py#L146 # noqa: E501
        if self._conn is not None:
            self._conn.close()
        if self._fvp is not None and not is_windows():
            try:
                fletd_pid = nix_get_pid("fletd")
                self.logger.debug(f"Flet View process {self._fvp.pid}")
                self.logger.debug(f"Fletd Server process {fletd_pid}")
                os.kill(fletd_pid, signal.SIGKILL)
            except (SubprocessError, OSError) as err:
                self.logger.error(
                    f"Unexpected error {err} when killing Flet subprocess"
                )
            except ValueError:
                pass  # no leftover process found

        # kill the graphical application on macOS,
        # otherwise it can hang around after cleanup
        if is_macos():
            try:
                fletd_app_pid = nix_get_pid("Flet")
                self.logger.debug(f"Flet application process {fletd_app_pid}")
                os.kill(fletd_app_pid, signal.SIGKILL)
            except ValueError:
                pass  # no leftover process found
            except (SubprocessError, OSError) as err:
                self.logger.error(
                    f"Unexpected error {err} when killing Flet subprocess"
                )

    def _create_flet_target_function(
        self, page: Optional[Page] = None
    ) -> Callable[[Optional[Page]], None]:
        def inner_execute(inner_page: Optional[Page] = None):
            if page:
                inner_page = page
            for element in self._elements.visible:
                inner_page.add(element)
            for element in self._elements.invisible:
                inner_page.overlay.append(element)
            inner_page.scroll = ScrollMode.AUTO
            inner_page.on_disconnect = lambda _: self._fvp.terminate()
            self.page = inner_page
            inner_page.update()

        return inner_execute

    def _preload_flet(self):
        # We access Flet internals because it is simplest way to control the specifics
        # In the future we should migrate / ask for a stable API that fits our needs
        # pylint: disable=protected-access
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
        target: Callable[[Optional[Page]], None],
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

            target(page)

        if not self._conn:
            self._conn = self._preload_flet()
        self._conn.on_session_created = on_session_created
        # We access Flet internal function here to enable using of cached flet process
        # for the lifetime of FletClient
        # pylint: disable=protected-access
        self._fvp = flet.flet._open_flet_view(self._conn.page_url, False)
        view_start_time = timer()
        try:
            while not self._fvp.poll():
                if callable(self.pending_operation):
                    self.pending_operation()  # pylint: disable=not-callable
                    self.pending_operation = None
                if timer() - view_start_time >= timeout:
                    self._fvp.terminate()
                    raise TimeoutException(
                        "Reached timeout while waiting for Assistant Dialog"
                    )
                time.sleep(0.1)
        except TimeoutException:
            # pylint: disable=raise-missing-from
            raise TimeoutException("Reached timeout while waiting for Assistant Dialog")

    def _make_flet_event_handler(self, name: str):
        def change_listener(e: ControlEvent):
            self.results[name] = e.data
            e.page.update()

        return change_listener

    def add_element(self, element: flet.Control, name: Optional[str] = None):
        # TODO: validate that element "name" is unique
        self._elements.visible.append(element)
        if name is not None:
            # TODO: might be necessary to check that it doesn't already have change
            # handler
            element.on_change = self._make_flet_event_handler(name)

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
        location: Union[Location, Tuple[int, int], None],
        timeout: int,
    ):
        self._show_flet(
            self._create_flet_target_function(),
            title,
            height,
            width,
            on_top,
            location,
            timeout,
        )

    def clear_elements(self):
        if self.page:
            self.page.controls.clear()
            self.page.overlay.clear()
            self.page.update()
        self._elements.visible.clear()
        self._elements.invisible.clear()

    def update_elements(self, page: Page):
        """Updates the UI and shows new elements which have been added into the element
        lists
        """
        return self._create_flet_target_function(page)(None)

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
