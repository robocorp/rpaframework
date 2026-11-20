"""Access to the files of a Sema4.ai project workspace through the local file system.

On the Sema4.ai platform the files of a project are mounted into the sandbox as a
normal directory, whose location the platform gives in the
``BLOCKPARTY_WORKSPACE_ROOT`` environment variable. This module keeps every
operation inside that directory and uses workspace-relative paths, the same way
the platform's own interfaces do.
"""

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from .errors import (
    NotOnPlatformError,
    WorkspaceFileExistsError,
    WorkspaceFileNotFoundError,
    WorkspacePathError,
)

WORKSPACE_ROOT_ENV = "BLOCKPARTY_WORKSPACE_ROOT"

# Top-level names the platform owns. Skills, memories, schemas, workflows and
# verified logic live under ``.blockparty`` and are changed through their own
# review flows, not by writing files.
MANAGED_NAMES = (".blockparty", ".workspace_mcp")
MANAGED_PREFIXES = (".blockparty-workspace-ready-",)

PathLike = str | os.PathLike
FileEntry = dict[str, str | int]


def is_managed(first_part: str) -> bool:
    """Tell whether a top-level workspace name belongs to the platform."""
    return first_part in MANAGED_NAMES or first_part.startswith(MANAGED_PREFIXES)


def find_workspace_root(explicit: PathLike | None = None) -> Path:
    """Return the workspace root from the argument or the platform environment.

    :param explicit: Directory to use instead of the one the platform provides.
    :raises NotOnPlatformError: No root was given and the platform variable is unset.
    :raises WorkspacePathError: The root is not an existing directory.
    """
    value = (
        explicit if explicit not in (None, "") else os.environ.get(WORKSPACE_ROOT_ENV)
    )
    if value in (None, ""):
        raise NotOnPlatformError(
            f"No workspace root: the {WORKSPACE_ROOT_ENV} environment variable is not "
            "set, so this does not look like a Sema4.ai sandbox. Give the library a "
            "'workspace_root' to work on a local directory."
        )
    root = Path(value).expanduser()
    if not root.is_dir():
        raise WorkspacePathError(f"Workspace root {str(root)!r} is not a directory")
    return root.resolve()


def split_workspace_path(path: PathLike) -> list[str]:
    """Split a workspace-relative path and refuse anything that could leave the root."""
    text = os.fspath(path) if path is not None else ""
    if not isinstance(text, str) or not text.strip():
        raise WorkspacePathError("Workspace path is empty")
    if "\x00" in text:
        raise WorkspacePathError("Workspace path contains a NUL character")
    normalized = text.replace("\\", "/")
    if normalized.startswith("/") or (len(normalized) > 1 and normalized[1] == ":"):
        raise WorkspacePathError(
            f"Workspace path {text!r} is absolute; use a path relative to the "
            "workspace root"
        )
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    if ".." in parts:
        raise WorkspacePathError(
            f"Workspace path {text!r} contains a '..' segment, which is not allowed"
        )
    return parts


def check_not_managed(parts: list[str]) -> None:
    """Refuse a path whose first part is a platform-managed name."""
    if parts and is_managed(parts[0]):
        raise WorkspacePathError(
            f"Workspace path {'/'.join(parts)!r} is in a platform-managed area "
            f"({parts[0]}); change such content through the platform, or create "
            "the library with protect_managed=False"
        )


class Workspace:
    """Workspace-relative file operations confined to one root directory."""

    def __init__(self, root: PathLike | None = None, protect_managed: bool = True):
        self.root = find_workspace_root(root)
        self.protect_managed = protect_managed

    def parts(self, path: PathLike) -> list[str]:
        """Split a workspace-relative path and refuse anything that could leave the root."""
        return split_workspace_path(path)

    def resolve(
        self, path: PathLike, *, writing: bool = False, allow_root: bool = False
    ) -> Path:
        """Turn a workspace-relative path into a checked absolute path.

        :param path: Workspace-relative path.
        :param writing: The caller is about to create, change or remove the path.
        :param allow_root: Accept ``.`` (the workspace root itself).
        :raises WorkspacePathError: The path is not acceptable.
        """
        parts = self.parts(path)
        if not parts:
            if allow_root:
                return self.root
            raise WorkspacePathError("Workspace path points at the workspace root")
        if writing and self.protect_managed:
            check_not_managed(parts)
        candidate = self.root.joinpath(*parts)
        # A symbolic link inside the workspace must not lead out of it.
        resolved = candidate.resolve(strict=False)
        if resolved != self.root and self.root not in resolved.parents:
            raise WorkspacePathError(
                f"Workspace path {'/'.join(parts)!r} resolves outside the workspace"
            )
        return candidate

    def relative(self, absolute: Path) -> str:
        """Return the workspace-relative POSIX form of a path under the root."""
        return absolute.relative_to(self.root).as_posix()

    def _entry(self, absolute: Path) -> FileEntry:
        stat = absolute.stat()
        modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
        return {
            "path": self.relative(absolute),
            "name": absolute.name,
            "size": stat.st_size,
            "modified": modified.isoformat(timespec="seconds"),
        }

    def _walk(
        self, start: Path, recursive: bool, include_managed: bool
    ) -> Iterator[Path]:
        for current, dirnames, filenames in os.walk(start, followlinks=False):
            current_path = Path(current)
            if current_path == self.root and not include_managed:
                dirnames[:] = [name for name in dirnames if not is_managed(name)]
                filenames = [name for name in filenames if not is_managed(name)]
            dirnames.sort()
            for name in sorted(filenames):
                yield current_path / name
            if not recursive:
                dirnames[:] = []

    def list_files(
        self,
        prefix: PathLike = ".",
        recursive: bool = True,
        include_managed: bool = False,
    ) -> list[FileEntry]:
        """List the files under a workspace directory, or the one file a prefix names."""
        start = self.resolve(prefix, allow_root=True)
        if not start.exists():
            raise WorkspaceFileNotFoundError(
                f"Workspace path {os.fspath(prefix)!r} does not exist"
            )
        if start.is_file():
            return [self._entry(start)]
        entries = []
        for found in self._walk(start, recursive, include_managed):
            resolved = found.resolve(strict=False)
            if self.root not in resolved.parents or not resolved.is_file():
                # Broken links and links that leave the workspace are not files of it.
                continue
            entries.append(self._entry(found))
        return entries

    def existing_file(self, path: PathLike) -> Path:
        """Return the absolute path of an existing workspace file."""
        absolute = self.resolve(path)
        if not absolute.exists():
            raise WorkspaceFileNotFoundError(
                f"Workspace file {os.fspath(path)!r} does not exist"
            )
        if not absolute.is_file():
            raise WorkspacePathError(
                f"Workspace path {os.fspath(path)!r} is a directory, not a file"
            )
        return absolute

    def exists(self, path: PathLike) -> bool:
        """Tell whether a workspace path is an existing file."""
        return self.resolve(path).is_file()

    def target_for_write(self, path: PathLike, overwrite: bool) -> Path:
        """Check a path that is about to be written and create its parent directory."""
        absolute = self.resolve(path, writing=True)
        if absolute.is_dir():
            raise WorkspacePathError(
                f"Workspace path {os.fspath(path)!r} is a directory, not a file"
            )
        if absolute.exists() and not overwrite:
            raise WorkspaceFileExistsError(
                f"Workspace file {os.fspath(path)!r} already exists"
            )
        absolute.parent.mkdir(parents=True, exist_ok=True)
        return absolute

    def write(
        self,
        path: PathLike,
        content: str | bytes,
        overwrite: bool = True,
        encoding: str = "utf-8",
    ) -> Path:
        """Create or replace a workspace file with text or bytes."""
        if not isinstance(content, (str, bytes, bytearray)):
            raise TypeError(
                f"File content must be text or bytes, got {type(content).__name__}"
            )
        absolute = self.target_for_write(path, overwrite)
        if isinstance(content, str):
            absolute.write_text(content, encoding=encoding)
        else:
            absolute.write_bytes(bytes(content))
        return absolute

    def move(
        self, from_path: PathLike, to_path: PathLike, overwrite: bool = False
    ) -> Path:
        """Move one workspace file to another workspace path."""
        self.resolve(from_path, writing=True)
        source = self.existing_file(from_path)
        target = self.target_for_write(to_path, overwrite)
        if source.resolve() == target.resolve():
            return target
        os.replace(source, target)
        return target

    def delete(self, path: PathLike, missing_ok: bool = False) -> bool:
        """Delete one workspace file and tell whether a file was removed."""
        absolute = self.resolve(path, writing=True)
        if not absolute.exists() and not absolute.is_symlink():
            if missing_ok:
                return False
            raise WorkspaceFileNotFoundError(
                f"Workspace file {os.fspath(path)!r} does not exist"
            )
        if absolute.is_dir() and not absolute.is_symlink():
            raise WorkspacePathError(
                f"Workspace path {os.fspath(path)!r} is a directory; only files can "
                "be deleted"
            )
        absolute.unlink()
        return True

    @property
    def location(self) -> str:
        """Where this workspace lives, for logs and ``Get Workspace Root``."""
        return str(self.root)

    def read_bytes(self, path: PathLike) -> bytes:
        """Return the content of an existing workspace file."""
        return self.existing_file(path).read_bytes()

    def write_bytes(self, path: PathLike, data: bytes, overwrite: bool = True) -> str:
        """Create or replace a workspace file and return its workspace-relative path."""
        return self.relative(self.write(path, data, overwrite))

    def move_file(
        self, from_path: PathLike, to_path: PathLike, overwrite: bool = False
    ) -> str:
        """Move one workspace file and return its new workspace-relative path."""
        return self.relative(self.move(from_path, to_path, overwrite))
