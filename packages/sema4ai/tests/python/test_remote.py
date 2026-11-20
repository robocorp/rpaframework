"""The REST backend against a local stand-in for the project API.

The stand-in follows the published OpenAPI document (paths, query parameters,
bodies, the listing page shape and the error payload). How the real service
behaves beyond that document is not covered here.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest

from RPA.Sema4AI import (
    NotOnPlatformError,
    RemoteWorkspace,
    Sema4AI,
    Sema4AIError,
    WorkspaceFileExistsError,
    WorkspaceFileNotFoundError,
    WorkspacePathError,
)
from RPA.Sema4AI import remote
from RPA.Sema4AI.workspace import WORKSPACE_ROOT_ENV

PROJECT = "712acb53-ec27-423c-947b-8828bec317d7"
KEY = "bppk_test_0123456789abcdef"
PREFIX = f"/api/v1/project-api/projects/{PROJECT}/vfs"


class FakeProjectApi:
    def __init__(self):
        self.files = {
            "notes.txt": b"hello",
            "reports/summary.md": b"All matched.",
            "reports/2026/q3.csv": b"a,b\n1,2\n",
            ".blockparty/workflows/run.workflow.json": b"{}",
        }
        self.requests = []
        self.fail_with = None

    def directories(self):
        found = set()
        for path in self.files:
            parts = path.split("/")[:-1]
            for index in range(1, len(parts) + 1):
                found.add("/".join(parts[:index]))
        return found

    def entries(self, prefix, recursive):
        result = []
        for path in sorted(self.directories()):
            result.append({"path": path, "kind": "directory"})
        for path, data in sorted(self.files.items()):
            result.append(
                {
                    "path": path,
                    "kind": "file",
                    "size_bytes": len(data),
                    "sha256": "ab" * 32,
                }
            )
        result.append(
            {"path": "link", "kind": "symlink", "symlink_target": "notes.txt"}
        )
        if prefix:
            # As observed on the live service: a prefix naming a file returns that
            # file, and a prefix that does not exist returns an empty page.
            result = [
                e
                for e in result
                if e["path"].startswith(prefix + "/")
                or (e["path"] == prefix and e["kind"] == "file")
            ]
        if not recursive:
            depth = prefix.count("/") + 2 if prefix else 1
            result = [e for e in result if e["path"].count("/") + 1 == depth]
        return result


@pytest.fixture
def api():
    state = FakeProjectApi()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _send(self, status, payload=None, raw=None):
            body = raw if raw is not None else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header(
                "Content-Type",
                "application/octet-stream" if raw is not None else "application/json",
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _error(self, status, code, message):
            self._send(
                status,
                {
                    "code": code,
                    "message": message,
                    "request_id": "req-123",
                    "details": None,
                },
            )

        def _handle(self):
            url = urlsplit(self.path)
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            state.requests.append(
                (self.command, url.path, query, self.headers.get("Authorization"))
            )
            if self.headers.get("Authorization") != f"Bearer {KEY}":
                return self._error(401, "INFRA_UNAUTHORIZED", "Invalid API key")
            if state.fail_with:
                return self._error(*state.fail_with)
            if not url.path.startswith(PREFIX + "/"):
                return self._error(404, "INFRA_NOT_FOUND", "Not Found")
            operation = url.path[len(PREFIX) + 1 :]
            if self.command == "GET" and operation == "entries":
                found = state.entries(
                    query.get("prefix"), query.get("recursive", "true") == "true"
                )
                limit, offset = (
                    int(query.get("limit", 1000)),
                    int(query.get("offset", 0)),
                )
                page = found[offset : offset + limit]
                return self._send(
                    200,
                    {
                        "snapshot_id": "s",
                        "entries": page,
                        "limit": limit,
                        "offset": offset,
                        "has_more": offset + limit < len(found),
                    },
                )
            changed = []
            if operation == "files" and self.command in ("PUT", "DELETE"):
                changed = [query["path"]]
            elif operation == "files/move" and self.command == "POST":
                changed = list(json.loads(body).values())
            for path in changed:
                if path.split("/")[0] == ".blockparty":
                    return self._error(
                        400,
                        "INFRA_VALIDATION_FAILED",
                        f"system-managed paths cannot be edited via VFS APIs: {path}",
                    )
            if operation == "files" and self.command == "GET":
                if query["path"] not in state.files:
                    return self._error(404, "INFRA_NOT_FOUND", "File not found")
                return self._send(200, raw=state.files[query["path"]])
            if operation == "files" and self.command == "PUT":
                if not body:
                    return self._error(
                        422, "INFRA_VALIDATION_FAILED", "Upload payload is empty."
                    )
                state.files[query["path"]] = body
                return self._send(201, {"path": query["path"], "size_bytes": len(body)})
            if operation == "files" and self.command == "DELETE":
                if query["path"] not in state.files:
                    return self._error(404, "INFRA_NOT_FOUND", "File not found")
                del state.files[query["path"]]
                return self._send(200, {"path": query["path"]})
            if operation == "files/move" and self.command == "POST":
                move = json.loads(body)
                if move["from"] not in state.files:
                    return self._error(404, "INFRA_NOT_FOUND", "File not found")
                if move["to_path"] in state.files:
                    return self._error(
                        409, "INFRA_CONFLICT", "destination is occupied."
                    )
                state.files[move["to_path"]] = state.files.pop(move["from"])
                return self._send(
                    200, {"from_path": move["from"], "to_path": move["to_path"]}
                )
            return self._error(404, "INFRA_NOT_FOUND", "Not Found")

        do_GET = do_PUT = do_POST = do_DELETE = _handle

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    ).start()
    state.url = f"http://127.0.0.1:{server.server_port}"
    yield state
    server.shutdown()
    server.server_close()


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in (
        WORKSPACE_ROOT_ENV,
        "SEMA4AI_BASE_URL",
        "SEMA4AI_PROJECT_ID",
        "SEMA4AI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def library(api):
    return Sema4AI(project_id=PROJECT, api_key=KEY, base_url=api.url)


class TestConfiguration:
    def test_settings_from_the_environment(self, api, monkeypatch):
        monkeypatch.setenv("SEMA4AI_BASE_URL", api.url)
        monkeypatch.setenv("SEMA4AI_PROJECT_ID", PROJECT)
        monkeypatch.setenv("SEMA4AI_API_KEY", KEY)

        assert Sema4AI().read_workspace_file("notes.txt") == "hello"

    def test_connect_keyword_switches_to_the_project(self, api):
        library = Sema4AI()
        library.connect_to_sema4_project(PROJECT, KEY, base_url=api.url)

        assert library.read_workspace_file("notes.txt") == "hello"
        assert library.get_workspace_root() == f"{api.url}{PREFIX}"

    def test_connect_uses_the_base_url_given_at_import(self, api):
        library = Sema4AI(base_url=api.url)
        library.connect_to_sema4_project(PROJECT, KEY)

        assert library.workspace_file_exists("notes.txt") is True

    def test_nothing_configured_explains_every_option(self):
        with pytest.raises(NotOnPlatformError, match="Connect To Sema4 Project"):
            Sema4AI().list_workspace_files()

    @pytest.mark.parametrize(
        "given, missing",
        [
            ({"project_id": PROJECT}, "base_url, api_key"),
            ({"project_id": PROJECT, "api_key": KEY}, "base_url"),
            ({"base_url": "https://example.test", "api_key": KEY}, "project_id"),
        ],
    )
    def test_incomplete_settings_name_what_is_missing(self, given, missing):
        with pytest.raises(Sema4AIError, match=f"missing: {missing}"):
            Sema4AI(**given).list_workspace_files()

    def test_local_root_wins_over_api_settings(self, api, tmp_path):
        (tmp_path / "local.txt").write_text("local")
        library = Sema4AI(
            workspace_root=str(tmp_path),
            project_id=PROJECT,
            api_key=KEY,
            base_url=api.url,
        )

        assert library.read_workspace_file("local.txt") == "local"
        assert api.requests == []

    def test_platform_sandbox_wins_over_api_settings(self, api, tmp_path, monkeypatch):
        (tmp_path / "local.txt").write_text("sandbox")
        monkeypatch.setenv(WORKSPACE_ROOT_ENV, str(tmp_path))
        library = Sema4AI(project_id=PROJECT, api_key=KEY, base_url=api.url)

        assert library.read_workspace_file("local.txt") == "sandbox"
        assert api.requests == []

    @pytest.mark.parametrize(
        "url",
        [
            "http://us3.sema4.ai",
            "http://example.test:8080",
            "ftp://x",
            "us3.sema4.ai",
            "",
        ],
    )
    def test_plain_http_to_a_remote_host_is_refused(self, url):
        with pytest.raises(Sema4AIError):
            RemoteWorkspace(url, PROJECT, KEY)

    @pytest.mark.parametrize("field", ["project_id", "api_key"])
    @pytest.mark.parametrize("value", ["", "   ", None])
    def test_blank_values_are_refused(self, field, value):
        settings = {
            "base_url": "https://us3.sema4.ai",
            "project_id": PROJECT,
            "api_key": KEY,
            field: value,
        }

        with pytest.raises(Sema4AIError, match=field):
            RemoteWorkspace(**settings)

    def test_connect_without_any_base_url_is_refused(self):
        with pytest.raises(Sema4AIError, match="base_url"):
            Sema4AI().connect_to_sema4_project(PROJECT, KEY)


class TestSecrets:
    def test_api_key_is_sent_as_a_bearer_token_and_only_there(self, library, api):
        library.read_workspace_file("notes.txt")

        method, path, query, authorization = api.requests[-1]
        assert authorization == f"Bearer {KEY}"
        assert KEY not in path and KEY not in json.dumps(query)

    def test_api_key_never_appears_in_errors_or_repr(self, api):
        workspace = RemoteWorkspace(api.url, PROJECT, "bppk_wrong_key_value")

        with pytest.raises(Sema4AIError) as error:
            workspace.read_bytes("notes.txt")

        assert "bppk_wrong_key_value" not in str(error.value)
        assert "bppk_wrong_key_value" not in repr(workspace)
        assert "bppk_wrong_key_value" not in workspace.location

    def test_wrong_key_is_an_authentication_error_with_a_hint(self, api):
        library = Sema4AI(project_id=PROJECT, api_key="bppk_wrong", base_url=api.url)

        with pytest.raises(
            Sema4AIError, match="401 INFRA_UNAUTHORIZED.*project API key"
        ):
            library.list_workspace_files()

    def test_project_id_is_url_quoted(self, api):
        workspace = RemoteWorkspace(api.url, "abc/../../other?x=1", KEY)

        with pytest.raises(Sema4AIError):
            workspace.read_bytes("notes.txt")
        assert all(
            "/other" not in path and "?" not in path for _, path, _, _ in api.requests
        )


class TestRemoteFiles:
    def test_listing_returns_files_only_and_hides_managed_content(self, library):
        entries = library.list_workspace_files()

        assert [e["path"] for e in entries] == [
            "notes.txt",
            "reports/2026/q3.csv",
            "reports/summary.md",
        ]
        assert entries[0] == {
            "path": "notes.txt",
            "name": "notes.txt",
            "size": 5,
            "sha256": "ab" * 32,
        }

    def test_listing_can_include_managed_content(self, library):
        paths = [e["path"] for e in library.list_workspace_files(include_managed=True)]

        assert ".blockparty/workflows/run.workflow.json" in paths

    def test_listing_a_directory_non_recursively(self, library, api):
        paths = [
            e["path"] for e in library.list_workspace_files("reports", recursive=False)
        ]

        assert paths == ["reports/summary.md"]
        assert api.requests[-1][2]["prefix"] == "reports"
        assert api.requests[-1][2]["recursive"] == "false"

    def test_listing_follows_every_page(self, library, api, monkeypatch):
        monkeypatch.setattr(remote, "PAGE_SIZE", 2)
        for number in range(7):
            api.files[f"bulk/file-{number}.txt"] = b"x"

        paths = [e["path"] for e in library.list_workspace_files("bulk")]

        assert len(paths) == 7
        assert len([r for r in api.requests if r[1].endswith("/entries")]) >= 4

    def test_read_text_and_bytes(self, library, api):
        api.files["data.bin"] = bytes(range(256))

        assert library.read_workspace_file("reports/summary.md") == "All matched."
        assert library.read_workspace_binary_file("data.bin") == bytes(range(256))

    def test_write_uploads_the_bytes(self, library, api):
        assert (
            library.write_workspace_file("out/lasku.txt", "12,50 € ✓")
            == "out/lasku.txt"
        )
        assert api.files["out/lasku.txt"] == "12,50 € ✓".encode()

    def test_write_without_overwrite_checks_first(self, library, api):
        with pytest.raises(WorkspaceFileExistsError):
            library.write_workspace_file("notes.txt", "new", overwrite=False)
        assert api.files["notes.txt"] == b"hello"
        assert not any(method == "PUT" for method, *_ in api.requests)

        library.write_workspace_file("fresh.txt", "new", overwrite=False)
        assert api.files["fresh.txt"] == b"new"

    def test_exists(self, library):
        assert library.workspace_file_exists("reports/summary.md") is True
        assert library.workspace_file_exists("reports/nope.md") is False
        assert library.workspace_file_exists("reports") is False
        assert library.workspace_file_exists("nowhere/at/all.txt") is False
        assert library.workspace_file_exists("link") is False

    def test_missing_file_maps_to_file_not_found(self, library):
        with pytest.raises(
            WorkspaceFileNotFoundError, match="404 INFRA_NOT_FOUND.*req-123"
        ):
            library.read_workspace_file("nope.txt")
        with pytest.raises(FileNotFoundError):
            library.delete_workspace_file("nope.txt")
        assert library.delete_workspace_file("nope.txt", missing_ok=True) is False

    def test_move(self, library, api):
        assert (
            library.move_workspace_file("notes.txt", "archive/notes.txt")
            == "archive/notes.txt"
        )
        assert (
            "notes.txt" not in api.files and api.files["archive/notes.txt"] == b"hello"
        )

    def test_move_does_not_overwrite_by_default(self, library, api):
        with pytest.raises(WorkspaceFileExistsError):
            library.move_workspace_file("notes.txt", "reports/summary.md")
        assert api.files["notes.txt"] == b"hello"

        library.move_workspace_file("notes.txt", "reports/summary.md", overwrite=True)
        assert api.files["reports/summary.md"] == b"hello"

    def test_move_of_a_missing_file(self, library, api):
        with pytest.raises(WorkspaceFileNotFoundError):
            library.move_workspace_file("nope.txt", "x.txt")
        with pytest.raises(WorkspaceFileNotFoundError):
            library.move_workspace_file("nope.txt", "notes.txt", overwrite=True)
        assert api.files["notes.txt"] == b"hello", (
            "target must survive a failed overwrite move"
        )

    def test_server_conflict_on_move_is_file_exists(self, api):
        # The destination appears between the check and the move.
        workspace = RemoteWorkspace(api.url, PROJECT, KEY)
        workspace.exists = lambda path: False

        with pytest.raises(WorkspaceFileExistsError, match="409 INFRA_CONFLICT"):
            workspace.move_file("notes.txt", "reports/summary.md")
        assert api.files["notes.txt"] == b"hello"

    def test_empty_content_is_refused_by_the_api(self, library, api):
        with pytest.raises(
            Sema4AIError, match="422 INFRA_VALIDATION_FAILED: Upload payload is empty"
        ):
            library.write_workspace_file("empty.txt", "")
        assert "empty.txt" not in api.files

    def test_listing_a_missing_prefix_is_an_error(self, library):
        with pytest.raises(WorkspaceFileNotFoundError, match="no-such-dir"):
            library.list_workspace_files("no-such-dir")

    def test_listing_a_prefix_that_names_a_file(self, library):
        assert [
            e["path"] for e in library.list_workspace_files("reports/summary.md")
        ] == ["reports/summary.md"]

    def test_empty_workspace_root_lists_nothing(self, library, api):
        api.files.clear()

        assert library.list_workspace_files() == []

    def test_delete(self, library, api):
        assert library.delete_workspace_file("notes.txt") is True
        assert "notes.txt" not in api.files

    def test_copy_in_and_out(self, library, api, tmp_path):
        local = tmp_path / "report.xlsx"
        local.write_bytes(b"PK\x03\x04")

        library.copy_file_to_workspace(str(local), "reports/report.xlsx")
        copy = library.copy_file_from_workspace(
            "reports/report.xlsx", str(tmp_path / "out")
        )

        assert api.files["reports/report.xlsx"] == b"PK\x03\x04"
        assert (tmp_path / "out").read_bytes() == b"PK\x03\x04"
        assert copy == str((tmp_path / "out").resolve())


class TestRemoteSafety:
    @pytest.mark.parametrize(
        "path", ["../other-project/secret", "/etc/passwd", "a/../../b", "", "C:\\x"]
    )
    def test_bad_paths_never_reach_the_api(self, library, api, path):
        for call in (
            lambda: library.read_workspace_file(path),
            lambda: library.write_workspace_file(path, "x"),
            lambda: library.delete_workspace_file(path),
            lambda: library.move_workspace_file("notes.txt", path),
            lambda: library.workspace_file_exists(path),
        ):
            with pytest.raises(WorkspacePathError):
                call()
        assert api.requests == []

    def test_managed_content_is_read_only(self, library, api):
        managed = ".blockparty/workflows/run.workflow.json"

        assert library.read_workspace_file(managed) == "{}"
        for call in (
            lambda: library.write_workspace_file(managed, "changed"),
            lambda: library.delete_workspace_file(managed),
            lambda: library.move_workspace_file(managed, "stolen.json"),
            lambda: library.move_workspace_file("notes.txt", ".blockparty/notes.txt"),
        ):
            with pytest.raises(WorkspacePathError, match="platform-managed"):
                call()
        assert api.files[managed] == b"{}"
        assert not any(
            method in ("PUT", "DELETE", "POST") for method, *_ in api.requests
        )

    def test_protection_can_be_switched_off(self, api):
        library = Sema4AI(
            project_id=PROJECT, api_key=KEY, base_url=api.url, protect_managed=False
        )

        library.write_workspace_file(".workspace_mcp/notes.md", "ok")

        assert api.files[".workspace_mcp/notes.md"] == b"ok"

    def test_platform_refuses_blockparty_even_with_protection_off(self, api):
        library = Sema4AI(
            project_id=PROJECT, api_key=KEY, base_url=api.url, protect_managed=False
        )
        managed = ".blockparty/workflows/run.workflow.json"

        for call in (
            lambda: library.write_workspace_file(".blockparty/notes.md", "x"),
            lambda: library.delete_workspace_file(managed),
            lambda: library.move_workspace_file(managed, "stolen.json"),
            lambda: library.move_workspace_file("notes.txt", ".blockparty/notes.txt"),
        ):
            with pytest.raises(
                WorkspacePathError, match="400 .*system-managed paths cannot be edited"
            ):
                call()
        assert api.files[managed] == b"{}"
        assert ".blockparty/notes.md" not in api.files
        assert "notes.txt" in api.files

    @pytest.mark.parametrize(
        "status, code, expected",
        [
            (403, "INFRA_FORBIDDEN", "403 INFRA_FORBIDDEN"),
            (409, "VFS_VOLUME_CONFLICT", "409 VFS_VOLUME_CONFLICT"),
            (413, "INFRA_PAYLOAD_TOO_LARGE", "413 INFRA_PAYLOAD_TOO_LARGE"),
            (429, "INFRA_RATE_LIMITED", "429 INFRA_RATE_LIMITED"),
            (500, "INFRA_INTERNAL_ERROR", "500 INFRA_INTERNAL_ERROR"),
        ],
    )
    def test_api_errors_carry_the_status_code_and_message(
        self, library, api, status, code, expected
    ):
        api.fail_with = (status, code, "explained by the platform")

        with pytest.raises(
            Sema4AIError, match=f"{expected}: explained by the platform"
        ):
            library.write_workspace_file("out.txt", "x")
        assert "out.txt" not in api.files

    def test_unreachable_host_is_a_library_error(self):
        workspace = RemoteWorkspace("http://127.0.0.1:9", PROJECT, KEY, timeout=2)

        with pytest.raises(Sema4AIError, match="Could not reach"):
            workspace.read_bytes("notes.txt")

    def test_projects_still_need_the_platform(self, library, monkeypatch):
        import sys

        monkeypatch.setitem(sys.modules, "sdk", None)
        monkeypatch.setitem(sys.modules, "sdk.meta", None)

        with pytest.raises(NotOnPlatformError):
            library.list_projects()
