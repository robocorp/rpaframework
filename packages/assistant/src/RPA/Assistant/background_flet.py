from subprocess import Popen
from logging import getLogger
from subprocess import Popen, SubprocessError
from typing import Optional

from flet import flet as ft

_connect_internal_sync = ft.__connect_internal_sync


class BackgroundFlet:
    def __init__(self):
        self.logger = getLogger(__name__)
        self._conn: Optional[ft.Connection] = None
        self._fvp: Optional[Popen] = None
        self._pid_file: Optional[str] = None

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
        # Based on https://github.com/flet-dev/flet/blob/035b00104f782498d084c2fd7ee96132a542ab7f/sdk/python/packages/flet/src/flet/flet.py#L96
        # We access Flet internals because it is simplest way to control the specifics
        # In the future we should migrate / ask for a stable API that fits our needs
        # pylint: disable=protected-access
        conn = _connect_internal_sync(
            page_name=name,
            view=ft.FLET_APP,
            host=host,
            port=port,
            auth_token=auth_token,
            session_handler=target,
            assets_dir=assets_dir,
            upload_dir=upload_dir,
            web_renderer=web_renderer,
            route_url_strategy=route_url_strategy,
        )

        self.logger.info("Connected to Flet app and handling user sessions...")

        fvp, pid_file = ft.open_flet_view(
            conn.page_url, assets_dir, view == ft.FLET_APP_HIDDEN
        )
        return conn, fvp, pid_file

    def start_flet_view(self, target):
        """Starts the flet process and places the connection, view process Popen and
        flet python server PID file into self
        """
        self._conn, self._fvp, self._pid_file = self._app_sync(target)

    def close_flet_view(self):
        assert self._conn is not None
        assert self._fvp is not None
        assert self._pid_file is not None
        self._conn.close()
        ft.close_flet_view(self._pid_file)
        self._fvp.terminate()
        self._conn = None
        self._fvp = None
        self._pid_file = None

    def terminate(self):
        self._fvp.terminate()

    def poll(self):
        return self._fvp.poll()
