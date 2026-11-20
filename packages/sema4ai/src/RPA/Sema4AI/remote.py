"""Access to the files of a Sema4.ai project from outside the platform.

Uses the VFS operations of the project-scoped REST API, described by the
OpenAPI document the platform serves at ``/api/v1/project-api/openapi.json``.
Requests are authenticated with a project API key, created in the project's
settings and sent as ``Authorization: Bearer bppk_...``.

Only the standard library is used, so the package stays free of dependencies.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .errors import (
    Sema4AIError,
    WorkspaceFileExistsError,
    WorkspaceFileNotFoundError,
    WorkspacePathError,
)
from .workspace import (
    FileEntry,
    PathLike,
    check_not_managed,
    is_managed,
    split_workspace_path,
)

PROJECT_ID_ENV = "SEMA4AI_PROJECT_ID"
API_KEY_ENV = "SEMA4AI_API_KEY"
BASE_URL_ENV = "SEMA4AI_BASE_URL"

PAGE_SIZE = 1000
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


class RemoteWorkspace:
    """Workspace-relative file operations on one project through the REST API."""

    def __init__(
        self,
        base_url: str,
        project_id: str,
        api_key: str,
        protect_managed: bool = True,
        timeout: float = 60.0,
    ):
        """
        :param base_url: Address of the Sema4.ai deployment, for example
            ``https://us3.sema4.ai``.
        :param project_id: ID of the project whose files are used.
        :param api_key: Project API key.
        :param protect_managed: Refuse to change platform-managed content.
        :param timeout: Seconds to wait for a connection or a response.
        """
        for name, value in (
            ("base_url", base_url),
            ("project_id", project_id),
            ("api_key", api_key),
        ):
            if not isinstance(value, str) or not value.strip():
                raise Sema4AIError(f"A {name} is required to reach a Sema4.ai project")
        parsed = urllib.parse.urlsplit(base_url.strip())
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise Sema4AIError(f"Base URL {base_url!r} is not an http(s) address")
        if parsed.scheme != "https" and parsed.hostname not in LOCAL_HOSTS:
            # The API key must not travel unencrypted.
            raise Sema4AIError(f"Base URL {base_url!r} must use https")
        self.base_url = base_url.strip().rstrip("/")
        self.project_id = project_id.strip()
        self.protect_managed = protect_managed
        self.timeout = timeout
        self._api_key = api_key.strip()

    def __repr__(self) -> str:
        return f"RemoteWorkspace({self.location!r})"

    @property
    def location(self) -> str:
        """Where this workspace lives, for logs and ``Get Workspace Root``."""
        project = urllib.parse.quote(self.project_id, safe="")
        return f"{self.base_url}/api/v1/project-api/projects/{project}/vfs"

    def _path(self, path: PathLike, *, writing: bool = False) -> str:
        parts = split_workspace_path(path)
        if not parts:
            raise WorkspacePathError("Workspace path points at the workspace root")
        if writing and self.protect_managed:
            check_not_managed(parts)
        return "/".join(parts)

    def _request(
        self,
        method: str,
        operation: str,
        query: dict[str, Any] | None = None,
        body: bytes | None = None,
        content_type: str | None = None,
    ) -> bytes:
        url = f"{self.location}/{operation}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, data=body, method=method)
        request.add_header("Authorization", f"Bearer {self._api_key}")
        request.add_header("Accept", "application/json, application/octet-stream")
        if content_type:
            request.add_header("Content-Type", content_type)
        try:
            # The scheme was checked in __init__, so only http(s) is ever opened.
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise self._error(method, operation, exc) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            raise Sema4AIError(f"Could not reach {self.base_url}: {reason}") from None

    def _error(
        self, method: str, operation: str, exc: urllib.error.HTTPError
    ) -> Sema4AIError:
        code, message, request_id = "", "", ""
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
            if isinstance(payload, dict):
                code = str(payload.get("code") or "")
                message = str(payload.get("message") or "")
                request_id = str(payload.get("request_id") or "")
        except (ValueError, OSError):
            pass
        detail = f"{exc.code} {code}".strip()
        text = f"{method} {operation} failed: {detail}"
        if message:
            text += f": {message}"
        if request_id:
            text += f" (request {request_id})"
        if exc.code == 404:
            return WorkspaceFileNotFoundError(text)
        if exc.code == 409 and operation == "files/move":
            # The platform refuses to move a file onto an occupied path.
            return WorkspaceFileExistsError(text)
        if exc.code in (401, 403):
            return Sema4AIError(
                f"{text}. Check the project API key and that it belongs to project "
                f"{self.project_id}"
            )
        return Sema4AIError(text)

    def _json(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raw = self._request(*args, **kwargs)
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise Sema4AIError(
                "The platform returned a response that is not JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise Sema4AIError("The platform returned an unexpected response")
        return payload

    def _entries(self, prefix: str | None, recursive: bool) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        offset = 0
        while True:
            query: dict[str, Any] = {
                "recursive": "true" if recursive else "false",
                "limit": PAGE_SIZE,
                "offset": offset,
            }
            if prefix:
                query["prefix"] = prefix
            page = self._json("GET", "entries", query)
            batch = page.get("entries") or []
            entries.extend(item for item in batch if isinstance(item, dict))
            if not page.get("has_more") or not batch:
                return entries
            offset += len(batch)

    def list_files(
        self,
        prefix: PathLike = ".",
        recursive: bool = True,
        include_managed: bool = False,
    ) -> list[FileEntry]:
        """List the files under a workspace directory."""
        parts = split_workspace_path(prefix)
        found = self._entries("/".join(parts) or None, recursive)
        if parts and not found:
            # Directories exist on the platform only while they hold a file, so
            # nothing under a prefix means the prefix is not there.
            raise WorkspaceFileNotFoundError(
                f"Workspace path {'/'.join(parts)!r} does not exist"
            )
        files: list[FileEntry] = []
        for item in found:
            path = str(item.get("path") or "")
            if item.get("kind") != "file" or not path:
                continue
            if not include_managed and is_managed(path.split("/", maxsplit=1)[0]):
                continue
            entry: FileEntry = {
                "path": path,
                "name": path.rsplit("/", maxsplit=1)[-1],
                "size": int(item.get("size_bytes") or 0),
            }
            if item.get("sha256"):
                entry["sha256"] = str(item["sha256"])
            files.append(entry)
        return files

    def exists(self, path: PathLike) -> bool:
        """Tell whether a workspace path is an existing file."""
        wanted = self._path(path)
        parent = wanted.rpartition("/")[0]
        try:
            entries = self._entries(parent or None, recursive=False)
        except WorkspaceFileNotFoundError:
            return False
        return any(
            item.get("path") == wanted and item.get("kind") == "file"
            for item in entries
        )

    def read_bytes(self, path: PathLike) -> bytes:
        """Return the content of an existing workspace file."""
        return self._request("GET", "files", {"path": self._path(path)})

    def write_bytes(self, path: PathLike, data: bytes, overwrite: bool = True) -> str:
        """Create or replace a workspace file and return its workspace-relative path."""
        target = self._path(path, writing=True)
        if not overwrite and self.exists(target):
            raise WorkspaceFileExistsError(f"Workspace file {target!r} already exists")
        self._json(
            "PUT",
            "files",
            {"path": target},
            body=bytes(data),
            content_type="application/octet-stream",
        )
        return target

    def move_file(
        self, from_path: PathLike, to_path: PathLike, overwrite: bool = False
    ) -> str:
        """Move one workspace file and return its new workspace-relative path."""
        source = self._path(from_path, writing=True)
        target = self._path(to_path, writing=True)
        if source == target:
            return target
        if self.exists(target):
            if not overwrite:
                raise WorkspaceFileExistsError(
                    f"Workspace file {target!r} already exists"
                )
            if not self.exists(source):
                raise WorkspaceFileNotFoundError(
                    f"Workspace file {source!r} does not exist"
                )
            # The platform refuses to move onto an occupied path, so the old
            # target is removed first. The two steps are not atomic.
            self.delete(target)
        body = json.dumps({"from": source, "to_path": target}).encode("utf-8")
        self._json("POST", "files/move", body=body, content_type="application/json")
        return target

    def delete(self, path: PathLike, missing_ok: bool = False) -> bool:
        """Delete one workspace file and tell whether a file was removed."""
        target = self._path(path, writing=True)
        try:
            self._json("DELETE", "files", {"path": target})
        except WorkspaceFileNotFoundError:
            if missing_ok:
                return False
            raise
        return True
