import atexit
import os
import signal
from logging import getLogger
from subprocess import Popen, SubprocessError
from typing import Optional

from flet import flet as ft
from flet.connection import Connection
from flet.utils import is_macos, is_windows

from RPA.Assistant.utils import nix_get_pid


class BackgroundFlet:
    def __init__(self):
        atexit.register(self.cleanup)
        self.logger = getLogger(__name__)
        self._conn: Optional[Connection] = None
        self._fvp: Optional[Popen] = None

    def cleanup(self):
        # Source: https://github.com/flet-dev/flet/blob/89364edec81f0f9591a37bdba5f704215badb0d3/sdk/python/flet/flet.py#L146 # noqa: E501
        if self._conn is not None:
            self._conn.close()
        if not is_windows():
            try:
                fletd_pid = nix_get_pid("fletd")
                self.logger.debug(f"Fletd Server process {fletd_pid}")
                os.kill(fletd_pid, signal.SIGTERM)
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

    def start_flet_view(self, target):
        # We access Flet internals because it is simplest way to control the specifics
        # In the future we should migrate / ask for a stable API that fits our needs
        # pylint: disable=protected-access
        def on_session_created(conn, session_data):
            page = ft.Page(conn, session_data.sessionID)
            conn.sessions[session_data.sessionID] = page
            target(page)

        if not self._conn:
            self._conn = ft._connect_internal(
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
        self._conn.on_session_created = on_session_created
        self._fvp = ft._open_flet_view(self._conn.page_url, False)

    def terminate(self):
        self._fvp.terminate()

    def poll(self):
        return self._fvp.poll()
