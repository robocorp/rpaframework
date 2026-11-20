import importlib
import logging
import os
from typing import Any

from .errors import (
    NotOnPlatformError,
    ProjectNotFoundError,
    Sema4AIError,
    WorkspaceFileExistsError,
    WorkspaceFileNotFoundError,
    WorkspacePathError,
)
from .workspace import WORKSPACE_ROOT_ENV, FileEntry, Workspace

__all__ = [
    "NotOnPlatformError",
    "ProjectNotFoundError",
    "Sema4AI",
    "Sema4AIError",
    "Workspace",
    "WorkspaceFileExistsError",
    "WorkspaceFileNotFoundError",
    "WorkspacePathError",
]

PROJECT_KEYS = ("project_id", "slug", "name")


class Sema4AI:
    """Library for working with a project on the `Sema4.ai <https://sema4.ai>`_
    cloud platform.

    This is the first part of the library. It covers the two things automation
    code running **on the platform** needs most often:

    - the **workspace files** of the project, which the platform mounts into the
      sandbox as a normal directory, and
    - the **projects** the current run can see.

    Access from outside the platform (a robot on a Control Room worker or on a
    developer machine reaching into a Sema4.ai project) is planned and not part
    of this version.

    **Workspace paths**

    Every file keyword takes a path relative to the workspace root, with ``/``
    as the separator, for example ``reports/2026/summary.md``. Absolute paths
    and ``..`` segments are refused, and a symbolic link cannot be used to step
    outside the workspace.

    The platform keeps its own content under ``.blockparty`` (workflows,
    skills, memories, schemas). Those files can be read, but the library
    refuses to write, move or delete them unless it is created with
    ``protect_managed=False``, because the platform expects such content to be
    changed through its own review flows. They are also left out of
    ``List Workspace Files`` by default.

    **Workspace root**

    On the platform the root comes from the ``BLOCKPARTY_WORKSPACE_ROOT``
    environment variable, so no configuration is needed. Elsewhere, give the
    library a ``workspace_root`` directory to develop and test against a local
    copy.

    **Robot Framework example**

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Sema4AI

        *** Tasks ***
        Write a report into the project
            Write Workspace File    reports/summary.md    All 12 invoices matched.
            ${files}=    List Workspace Files    reports
            FOR    ${file}    IN    @{files}
                Log    ${file}[path] (${file}[size] bytes)
            END

    **Python example**

    .. code-block:: python

        from RPA.Sema4AI import Sema4AI

        sema4 = Sema4AI()
        sema4.write_workspace_file("reports/summary.md", "All 12 invoices matched.")
        for file in sema4.list_workspace_files("reports"):
            print(file["path"], file["size"])
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(
        self,
        workspace_root: str | None = None,
        protect_managed: bool = True,
    ):
        """
        :param workspace_root: Directory to use as the workspace. Leave empty on
            the platform, where the root is taken from the environment.
        :param protect_managed: Refuse to write, move or delete files in
            platform-managed areas such as ``.blockparty``.
        """
        self.logger = logging.getLogger(__name__)
        self._workspace_root = workspace_root
        self._protect_managed = protect_managed
        self._workspace: Workspace | None = None

    @property
    def workspace(self) -> Workspace:
        """The workspace the file keywords operate on, resolved on first use."""
        if self._workspace is None:
            self._workspace = Workspace(self._workspace_root, self._protect_managed)
        return self._workspace

    def running_on_sema4_platform(self) -> bool:
        """Tell whether the code runs inside a Sema4.ai sandbox.

        :return: ``True`` when the platform's workspace variable is set.

        Robot Framework example:

        .. code-block:: robotframework

            ${on_platform}=    Running On Sema4 Platform
            IF    not ${on_platform}    Log    Using a local workspace copy

        Python example:

        .. code-block:: python

            if not sema4.running_on_sema4_platform():
                print("Using a local workspace copy")
        """
        return bool(os.environ.get(WORKSPACE_ROOT_ENV))

    def get_workspace_root(self) -> str:
        """Return the absolute path of the workspace root directory.

        :return: Directory under which every workspace path is resolved.

        Robot Framework example:

        .. code-block:: robotframework

            ${root}=    Get Workspace Root
            Log    Project files are in ${root}

        Python example:

        .. code-block:: python

            root = sema4.get_workspace_root()
        """
        return str(self.workspace.root)

    def list_workspace_files(
        self,
        prefix: str = ".",
        recursive: bool = True,
        include_managed: bool = False,
    ) -> list[FileEntry]:
        """List the files of the workspace, or of one directory in it.

        :param prefix: Workspace directory to list, ``.`` for the whole
            workspace. When it names a file, only that file is returned.
        :param recursive: Include the files of subdirectories.
        :param include_managed: Include platform-managed content such as
            ``.blockparty``.
        :return: One dictionary per file, with ``path`` (workspace-relative),
            ``name``, ``size`` (bytes) and ``modified`` (UTC, ISO 8601), sorted
            by path within each directory.
        :raises WorkspaceFileNotFoundError: The prefix does not exist.

        Robot Framework example:

        .. code-block:: robotframework

            ${files}=    List Workspace Files    reports    recursive=${FALSE}
            FOR    ${file}    IN    @{files}
                Log    ${file}[path]
            END

        Python example:

        .. code-block:: python

            for file in sema4.list_workspace_files("reports", recursive=False):
                print(file["path"], file["modified"])
        """
        return self.workspace.list_files(prefix, recursive, include_managed)

    def workspace_file_exists(self, path: str) -> bool:
        """Tell whether a file exists in the workspace.

        :param path: Workspace-relative path.
        :return: ``True`` for an existing file, ``False`` for a missing path
            or a directory.

        Robot Framework example:

        .. code-block:: robotframework

            ${exists}=    Workspace File Exists    reports/summary.md

        Python example:

        .. code-block:: python

            if sema4.workspace_file_exists("reports/summary.md"):
                ...
        """
        return self.workspace.exists(path)

    def read_workspace_file(self, path: str, encoding: str = "utf-8") -> str:
        """Read a workspace file as text.

        :param path: Workspace-relative path.
        :param encoding: Text encoding of the file.
        :return: The file content.
        :raises WorkspaceFileNotFoundError: The file does not exist.

        Robot Framework example:

        .. code-block:: robotframework

            ${text}=    Read Workspace File    email_templates/reminder.md

        Python example:

        .. code-block:: python

            text = sema4.read_workspace_file("email_templates/reminder.md")
        """
        return self.workspace.existing_file(path).read_text(encoding=encoding)

    def read_workspace_binary_file(self, path: str) -> bytes:
        """Read a workspace file as bytes.

        :param path: Workspace-relative path.
        :return: The file content.
        :raises WorkspaceFileNotFoundError: The file does not exist.

        Robot Framework example:

        .. code-block:: robotframework

            ${data}=    Read Workspace Binary File    invoices/1234.pdf

        Python example:

        .. code-block:: python

            data = sema4.read_workspace_binary_file("invoices/1234.pdf")
        """
        return self.workspace.existing_file(path).read_bytes()

    def write_workspace_file(
        self,
        path: str,
        content: str | bytes,
        overwrite: bool = True,
        encoding: str = "utf-8",
    ) -> str:
        """Create or replace a workspace file. Missing directories are created.

        :param path: Workspace-relative path.
        :param content: Text or bytes to write.
        :param overwrite: Replace an existing file. With ``False`` an existing
            file raises an error and is left untouched.
        :param encoding: Encoding used when ``content`` is text.
        :return: The workspace-relative path that was written.
        :raises WorkspaceFileExistsError: The file exists and ``overwrite`` is off.
        :raises WorkspacePathError: The path is not allowed, or is a directory.

        Robot Framework example:

        .. code-block:: robotframework

            Write Workspace File    reports/summary.md    All 12 invoices matched.
            Write Workspace File    reports/summary.md    Second try    overwrite=${FALSE}

        Python example:

        .. code-block:: python

            sema4.write_workspace_file("reports/summary.md", "All 12 invoices matched.")
            sema4.write_workspace_file("exports/data.bin", b"\\x00\\x01")
        """
        written = self.workspace.write(path, content, overwrite, encoding)
        relative = self.workspace.relative(written)
        self.logger.info("Wrote workspace file %s", relative)
        return relative

    def copy_file_to_workspace(
        self, source: str, path: str, overwrite: bool = True
    ) -> str:
        """Copy a file from the local file system into the workspace.

        Use this for files produced outside the workspace, for example in a
        temporary directory or the robot's output directory.

        :param source: Path of the local file to copy.
        :param path: Workspace-relative destination path.
        :param overwrite: Replace an existing workspace file.
        :return: The workspace-relative path that was written.
        :raises FileNotFoundError: The source file does not exist.
        :raises WorkspaceFileExistsError: The destination exists and
            ``overwrite`` is off.

        Robot Framework example:

        .. code-block:: robotframework

            Copy File To Workspace    ${OUTPUT_DIR}${/}report.xlsx    reports/report.xlsx

        Python example:

        .. code-block:: python

            sema4.copy_file_to_workspace("output/report.xlsx", "reports/report.xlsx")
        """
        written = self.workspace.copy_in(source, path, overwrite)
        relative = self.workspace.relative(written)
        self.logger.info("Copied %s to workspace file %s", source, relative)
        return relative

    def copy_file_from_workspace(
        self, path: str, target: str, overwrite: bool = True
    ) -> str:
        """Copy a workspace file to the local file system.

        :param path: Workspace-relative path of the file to copy.
        :param target: Local destination. When it is an existing directory the
            file keeps its name.
        :param overwrite: Replace an existing local file.
        :return: Absolute path of the copy.
        :raises WorkspaceFileNotFoundError: The workspace file does not exist.
        :raises FileExistsError: The target exists and ``overwrite`` is off.

        Robot Framework example:

        .. code-block:: robotframework

            ${copy}=    Copy File From Workspace    invoices/1234.pdf    ${OUTPUT_DIR}

        Python example:

        .. code-block:: python

            copy = sema4.copy_file_from_workspace("invoices/1234.pdf", "output")
        """
        return str(self.workspace.copy_out(path, target, overwrite))

    def move_workspace_file(
        self, from_path: str, to_path: str, overwrite: bool = False
    ) -> str:
        """Move or rename a workspace file. Missing directories are created.

        :param from_path: Workspace-relative path of the file to move.
        :param to_path: Workspace-relative destination path.
        :param overwrite: Replace an existing destination file.
        :return: The workspace-relative destination path.
        :raises WorkspaceFileNotFoundError: The source file does not exist.
        :raises WorkspaceFileExistsError: The destination exists and
            ``overwrite`` is off.

        Robot Framework example:

        .. code-block:: robotframework

            Move Workspace File    inbox/1234.pdf    processed/1234.pdf

        Python example:

        .. code-block:: python

            sema4.move_workspace_file("inbox/1234.pdf", "processed/1234.pdf")
        """
        moved = self.workspace.move(from_path, to_path, overwrite)
        relative = self.workspace.relative(moved)
        self.logger.info("Moved workspace file %s to %s", from_path, relative)
        return relative

    def delete_workspace_file(self, path: str, missing_ok: bool = False) -> bool:
        """Delete a workspace file. Directories are never deleted.

        :param path: Workspace-relative path.
        :param missing_ok: Return ``False`` for a missing file instead of
            raising an error.
        :return: ``True`` when a file was deleted.
        :raises WorkspaceFileNotFoundError: The file does not exist and
            ``missing_ok`` is off.
        :raises WorkspacePathError: The path is a directory or not allowed.

        Robot Framework example:

        .. code-block:: robotframework

            Delete Workspace File    reports/draft.md    missing_ok=${TRUE}

        Python example:

        .. code-block:: python

            sema4.delete_workspace_file("reports/draft.md", missing_ok=True)
        """
        deleted = self.workspace.delete(path, missing_ok)
        if deleted:
            self.logger.info("Deleted workspace file %s", path)
        return deleted

    def _platform_meta(self) -> Any:
        # The ``sdk`` package exists only inside the platform sandbox.
        try:
            return importlib.import_module("sdk.meta")
        except ImportError as exc:
            raise NotOnPlatformError(
                "Project information comes from the platform SDK, which is only "
                "available inside a Sema4.ai sandbox"
            ) from exc

    def list_projects(self, include_archived: bool = False) -> list[dict[str, Any]]:
        """List the projects the current run can see. Works on the platform only.

        :param include_archived: Include archived projects.
        :return: One dictionary per project, exactly as the platform returns
            it. At the time of writing the keys are ``project_id``, ``name``,
            ``slug``, ``kind``, ``status`` and ``description``.
        :raises NotOnPlatformError: The platform SDK is not available.

        Robot Framework example:

        .. code-block:: robotframework

            ${projects}=    List Projects
            FOR    ${project}    IN    @{projects}
                Log    ${project}[name] (${project}[project_id])
            END

        Python example:

        .. code-block:: python

            for project in sema4.list_projects():
                print(project["name"], project["project_id"])
        """
        meta = self._platform_meta()
        return list(meta.tenant.list_projects(include_archived=include_archived))

    def get_project(
        self, project: str, include_archived: bool = False
    ) -> dict[str, Any]:
        """Return one project by its ID, slug or name. Works on the platform only.

        The ID and slug are compared exactly, the name without regard to case.

        :param project: Project ID, slug or name.
        :param include_archived: Also look among archived projects.
        :return: The project dictionary, as in ``List Projects``.
        :raises ProjectNotFoundError: No project matches, or several do.
        :raises NotOnPlatformError: The platform SDK is not available.

        Robot Framework example:

        .. code-block:: robotframework

            ${project}=    Get Project    Invoice processing
            Log    ${project}[description]

        Python example:

        .. code-block:: python

            project = sema4.get_project("Invoice processing")
            print(project["description"])
        """
        wanted = str(project).strip()
        if not wanted:
            raise ProjectNotFoundError("Project identifier is empty")
        projects = self.list_projects(include_archived=include_archived)
        for key in PROJECT_KEYS:
            if key == "name":
                matches = [
                    item
                    for item in projects
                    if str(item.get(key, "")).casefold() == wanted.casefold()
                ]
            else:
                matches = [item for item in projects if item.get(key) == wanted]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                ids = ", ".join(str(item.get("project_id")) for item in matches)
                raise ProjectNotFoundError(
                    f"{len(matches)} projects have the {key} {wanted!r} ({ids}); "
                    "use the project ID"
                )
        raise ProjectNotFoundError(
            f"No project with the ID, slug or name {wanted!r} among "
            f"{len(projects)} visible projects"
        )
