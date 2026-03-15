import asyncio
import atexit
import signal
import threading
from logging import getLogger
from typing import Optional
from unittest.mock import patch

import flet as ft


class BackgroundFlet:
    """Class that manages the graphical flet window and related operations"""

    def __init__(self):
        atexit.register(self.close_flet_view)
        self.logger = getLogger(__name__)
        self._page: Optional[ft.Page] = None
        self._closed_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _run_flet_in_thread(self, target) -> None:
        """Run flet app, patching signal.signal to no-op since we're in a
        non-main thread where signal handlers cannot be registered."""

        original_signal = signal.signal

        def noop_signal(signalnum, handler):
            # Return current handler without registering, since we're not
            # in the main thread
            return signal.getsignal(signalnum)

        with patch.object(signal, "signal", noop_signal):
            ft.run(target)

        # ft.run() returns when the window is closed/destroyed
        self._closed_event.set()

    def start_flet_view(self, target) -> None:
        """Starts the flet app in a background daemon thread and waits until the
        target function has been called (page is available).
        """
        self._closed_event.clear()
        page_ready = threading.Event()

        def wrapped_target(page: ft.Page):
            self._page = page
            self._loop = asyncio.get_event_loop()
            page_ready.set()
            target(page)

        self._thread = threading.Thread(
            target=self._run_flet_in_thread,
            args=(wrapped_target,),
            daemon=True,
        )
        self._thread.start()
        if not page_ready.wait(timeout=30):
            self._closed_event.set()
            raise RuntimeError(
                "Flet app failed to start within 30 seconds"
            )

    def close_flet_view(self) -> None:
        """Close the currently open flet view"""
        if self._page is None:
            return
        try:
            if self._loop is not None and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._page.window.destroy(), self._loop
                ).result(timeout=5)
        except Exception:  # pylint: disable=broad-except
            pass
        self._closed_event.set()
        self._page = None
        self._thread = None
        self._loop = None

    def poll(self):
        """Returns None if the window is still open, non-None if closed.
        Preserves the same interface as the old Popen.poll() approach.
        """
        if self._closed_event.is_set():
            return 0
        return None
