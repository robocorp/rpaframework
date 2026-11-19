"""Connection handling of the Control Room API client behind `RPA.Robocorp.WorkItems`."""

import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import pytest

from RPA.Robocorp import utils
from RPA.Robocorp.utils import Requests


@pytest.fixture
def local_server():
    """A real HTTP/1.1 server that counts the connections it accepts."""
    state: dict = {"connections": 0, "hits": []}

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        timeout = 1  # close a keep-alive connection that is idle for 1 s

        def setup(self):
            state["connections"] += 1
            super().setup()

        def _ok(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            state["hits"].append(f"{self.command} {self.path}")
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        do_GET = do_POST = do_PUT = do_DELETE = _ok

        def log_message(self, *args):  # pylint: disable=arguments-differ
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    state["url"] = f"http://127.0.0.1:{httpd.server_port}/"
    yield state
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def forgetful_middlebox(local_server):
    """A TCP proxy that can silently drop the connections it currently carries.

    After `forget()`, bytes sent on an already-open connection are swallowed, nothing
    comes back and the socket stays open: what a firewall or NAT that dropped an idle
    flow looks like from the client. New connections keep working.
    """
    upstream = tuple(local_server["url"].removeprefix("http://").rstrip("/").split(":"))
    state = {"accepted": 0, "dead": set(), "sockets": []}

    def pump(src, dst, conn_id):
        try:
            while data := src.recv(65536):
                if conn_id not in state["dead"]:
                    dst.sendall(data)
        except OSError:
            pass
        if conn_id not in state["dead"]:
            for sock in (src, dst):
                try:
                    sock.close()
                except OSError:
                    pass

    def serve(listener):
        while True:
            try:
                client, _ = listener.accept()
            except OSError:
                return
            state["accepted"] += 1
            conn_id = state["accepted"]
            server = socket.create_connection((upstream[0], int(upstream[1])))
            state["sockets"] += [client, server]
            for pair in ((client, server), (server, client)):
                threading.Thread(
                    target=pump, args=(*pair, conn_id), daemon=True
                ).start()

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    threading.Thread(target=serve, args=(listener,), daemon=True).start()

    state["url"] = f"http://127.0.0.1:{listener.getsockname()[1]}/"
    state["forget"] = lambda: state["dead"].update(range(1, state["accepted"] + 1))
    yield state
    listener.close()
    for sock in state["sockets"]:
        try:
            sock.close()
        except OSError:
            pass


class TestConnectionReuse:
    def test_calls_reuse_one_connection(self, local_server):
        client = Requests(local_server["url"])

        client.post("reserve")
        client.get("payload")
        client.get("files")
        client.put("payload", json={})
        client.delete("file")
        client.post("release", json={})

        assert len(local_server["hits"]) == 6
        assert local_server["connections"] == 1

    def test_instances_do_not_share_connections(self, local_server):
        first = Requests(local_server["url"])
        second = Requests(local_server["url"])

        first.get("a")
        second.get("b")

        assert first._session is not second._session
        assert local_server["connections"] == 2

    def test_module_level_requests_are_not_used(self, local_server):
        with mock.patch("RPA.Robocorp.utils.requests.get") as module_get:
            Requests(local_server["url"]).get("a")

        module_get.assert_not_called()
        assert local_server["hits"] == ["GET /a"]

    def test_caller_headers_do_not_leak_into_later_calls(self, local_server):
        seen = []
        client = Requests(
            local_server["url"], default_headers={"Authorization": "Bearer secret"}
        )
        original = client._session.send

        def recording_send(request, **kwargs):
            seen.append(request.headers.get("Authorization"))
            return original(request, **kwargs)

        with mock.patch.object(client._session, "send", side_effect=recording_send):
            client.get("api")
            client.get("presigned", headers={})
            client.get("api")

        assert seen == ["Bearer secret", None, "Bearer secret"]


class TestStaleConnections:
    def test_recovers_when_server_closed_the_idle_connection(self, local_server):
        client = Requests(local_server["url"])

        client.post("reserve")
        time.sleep(1.6)
        start = time.monotonic()
        client.post("release", json={})

        assert time.monotonic() - start < 1, "no retry back-off expected"
        assert local_server["hits"].count("POST /release") == 1
        assert local_server["connections"] == 2

    def test_connection_idle_past_the_limit_is_not_reused(
        self, local_server, monkeypatch
    ):
        monkeypatch.setattr(utils, "MAX_IDLE", 0.2)
        client = Requests(local_server["url"])

        client.post("reserve")
        client.post("output", json={})
        assert local_server["connections"] == 1

        time.sleep(0.3)
        client.post("release", json={})

        assert local_server["connections"] == 2
        assert local_server["hits"].count("POST /release") == 1

    def test_silently_dropped_idle_connection_does_not_stall_the_call(
        self, local_server, forgetful_middlebox, monkeypatch
    ):
        monkeypatch.setattr(utils, "MAX_IDLE", 0.2)
        client = Requests(forgetful_middlebox["url"])

        client.post("reserve")
        forgetful_middlebox["forget"]()
        time.sleep(0.3)

        result = {}

        def release():
            result["response"] = client.post("release", json={})

        worker = threading.Thread(target=release, daemon=True)
        worker.start()
        worker.join(timeout=5)

        assert not worker.is_alive(), "call hung on the dropped connection"
        assert result["response"].status_code == 200
        assert local_server["hits"].count("POST /release") == 1

    @pytest.mark.parametrize("value, expected", [(None, 30.0), ("5", 5.0)])
    def test_idle_limit_comes_from_the_environment(self, value, expected):
        # Read at import time, so check it in a fresh interpreter instead of
        # reloading the module under the other tests.
        env = {k: v for k, v in os.environ.items() if k != "RC_API_CONNECTION_MAX_IDLE"}
        if value is not None:
            env["RC_API_CONNECTION_MAX_IDLE"] = value

        output = subprocess.run(
            [
                sys.executable,
                "-c",
                "from RPA.Robocorp import utils; print(utils.MAX_IDLE)",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        ).stdout

        assert float(output.strip().splitlines()[-1]) == expected
