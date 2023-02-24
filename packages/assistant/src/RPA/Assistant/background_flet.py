import atexit
from subprocess import Popen, SubprocessError
import os
import signal
from logging import getLogger
from typing import Optional
import threading

from flet import flet as ft
from flet import Page
from flet_core.connection import Connection
from flet.utils import is_windows, is_macos

from RPA.Assistant.utils import nix_get_pid

_connect_internal_sync = ft.__connect_internal_sync


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

    def _app_sync(
        self,
        target,
        name="",
        host=None,
        port=0,
        view: ft.AppViewer = ft.FLET_APP,
        assets_dir=None,
        upload_dir=None,
        web_renderer="canvaskit",
        route_url_strategy="path",
        auth_token=None,
    ):
        force_web_view = os.environ.get("FLET_FORCE_WEB_VIEW")
        # assets_dir = __get_assets_dir_path(assets_dir)

        conn = _connect_internal_sync(
            page_name=name,
            view=view if not force_web_view else ft.WEB_BROWSER,
            host=host,
            port=port,
            auth_token=auth_token,
            session_handler=target,
            assets_dir=assets_dir,
            upload_dir=upload_dir,
            web_renderer=web_renderer,
            route_url_strategy=route_url_strategy,
        )

        url_prefix = os.getenv("FLET_DISPLAY_URL_PREFIX")
        if url_prefix is not None:
            print(url_prefix, conn.page_url)
        else:
            self.logger.info(f"App URL: {conn.page_url}")

        self.logger.info("Connected to Flet app and handling user sessions...")

        assert url_prefix is None

        fvp, pid_file = ft.open_flet_view(
            conn.page_url, assets_dir, view == ft.FLET_APP_HIDDEN
        )
        return conn, fvp, pid_file
        try:
            fvp.wait()
        except (Exception) as e:
            pass

    def start_flet_view(self, target):
        # We access Flet internals because it is simplest way to control the specifics
        # In the future we should migrate / ask for a stable API that fits our needs
        # pylint: disable=protected-access
        def on_session_created(conn, session_data):
            page = Page(conn, session_data.sessionID)
            conn.sessions[session_data.sessionID] = page
            target(page)

        # self._conn.on_session_created = on_session_created

        self._conn, self._fvp, self._pid_file = self._app_sync(target)

    def close_flet_view(self):
        self._conn.close()
        ft.close_flet_view(self._pid_file)

    def terminate(self):
        self._fvp.terminate()

    def poll(self):
        return self._fvp.poll()
