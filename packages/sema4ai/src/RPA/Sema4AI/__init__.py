import importlib
import logging
import os
from pathlib import Path
from typing import Any

from .errors import (
    NotOnPlatformError,
    ProjectNotFoundError,
    Sema4AIError,
    WorkspaceFileExistsError,
    WorkspaceFileNotFoundError,
    WorkspacePathError,
)
from .remote import API_KEY_ENV, BASE_URL_ENV, PROJECT_ID_ENV, RemoteWorkspace
from .workspace import WORKSPACE_ROOT_ENV, FileEntry, Workspace

__all__ = [
    "NotOnPlatformError",
    "ProjectNotFoundError",
    "RemoteWorkspace",
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

    It gives automation code two things:

    - the **workspace files** of a project, and
    - the **projects** the current run can see (on the platform only).

    **Where the code runs**

    *On the platform*, the files of the project are mounted into the sandbox as
    a normal directory and no configuration is needed.

    *Outside the platform*, for example a robot on a Control Room worker or on
    a developer machine, the same file keywords work through the project's
    REST API. Give the library the address of the deployment, the project ID
    and a **project API key**, which is created in the project's settings.
    They can be passed when the library is imported, set as the environment
    variables ``SEMA4AI_BASE_URL``, ``SEMA4AI_PROJECT_ID`` and
    ``SEMA4AI_API_KEY``, or given later with ``Connect To Sema4 Project``,
    which suits a key read from a vault.

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

    **Local directory**

    Give the library a ``workspace_root`` directory to develop and test against
    a local copy of a workspace. It takes precedence over everything else.

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
        project_id: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """
        :param workspace_root: Directory to use as the workspace. Leave empty on
            the platform, where the root is taken from the environment.
        :param protect_managed: Refuse to write, move or delete files in
            platform-managed areas such as ``.blockparty``.
        :param project_id: Project to reach through the REST API when the code
            runs outside the platform.
        :param api_key: Project API key for the REST API.
        :param base_url: Address of the Sema4.ai deployment, for example
            ``https://us3.sema4.ai``.
        """
        self.logger = logging.getLogger(__name__)
        self._workspace_root = workspace_root
        self._protect_managed = protect_managed
        self._project_id = project_id
        self._api_key = api_key
        self._base_url = base_url
        self._workspace: Workspace | RemoteWorkspace | None = None

    @property
    def workspace(self) -> Workspace | RemoteWorkspace:
        """The workspace the file keywords operate on, resolved on first use."""
        if self._workspace is None:
            self._workspace = self._open_workspace()
        return self._workspace

    def _open_workspace(self) -> Workspace | RemoteWorkspace:
        if self._workspace_root or os.environ.get(WORKSPACE_ROOT_ENV):
            return Workspace(self._workspace_root, self._protect_managed)
        settings = {
            "base_url": self._base_url or os.environ.get(BASE_URL_ENV),
            "project_id": self._project_id or os.environ.get(PROJECT_ID_ENV),
            "api_key": self._api_key or os.environ.get(API_KEY_ENV),
        }
        if not any(settings.values()):
            raise NotOnPlatformError(
                f"No workspace: the {WORKSPACE_ROOT_ENV} environment variable is not "
                "set, so this does not look like a Sema4.ai sandbox, and no project "
                "API settings were given. Use 'Connect To Sema4 Project', set "
                f"{BASE_URL_ENV}, {PROJECT_ID_ENV} and {API_KEY_ENV}, or give the "
                "library a 'workspace_root' to work on a local directory."
            )
        missing = [name for name, value in settings.items() if not value]
        if missing:
            raise Sema4AIError(
                "Incomplete project API settings, missing: " + ", ".join(missing)
            )
        return RemoteWorkspace(
            str(settings["base_url"]),
            str(settings["project_id"]),
            str(settings["api_key"]),
            self._protect_managed,
        )

    def connect_to_sema4_project(
        self, project_id: str, api_key: str, base_url: str | None = None
    ) -> None:
        """Use the files of a project through its REST API from now on.

        Meant for code running outside the platform. The API key is a project
        API key, created in the project's settings; read it from a vault rather
        than writing it into the robot.

        :param project_id: ID of the project.
        :param api_key: Project API key.
        :param base_url: Address of the Sema4.ai deployment, for example
            ``https://us3.sema4.ai``. When left out, the value given at import
            or in ``SEMA4AI_BASE_URL`` is used.
        :raises Sema4AIError: A value is missing, or the address is not https.

        Robot Framework example:

        .. code-block:: robotframework

            ${secret}=    Get Secret    sema4_project
            Connect To Sema4 Project    ${secret}[project_id]    ${secret}[api_key]
            ...    base_url=https://us3.sema4.ai
            ${files}=    List Workspace Files    reports

        Python example:

        .. code-block:: python

            sema4.connect_to_sema4_project(
                secret["project_id"], secret["api_key"], base_url="https://us3.sema4.ai"
            )
            files = sema4.list_workspace_files("reports")
        """
        address = base_url or self._base_url or os.environ.get(BASE_URL_ENV) or ""
        self._workspace = RemoteWorkspace(
            address, project_id, api_key, self._protect_managed
        )
        self.logger.info("Connected to Sema4.ai project %s at %s", project_id, address)

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
        """Return the location of the workspace: a directory, or an API address.

        :return: Directory under which every workspace path is resolved. For a
            project reached through the REST API, the address of its file API.

        Robot Framework example:

        .. code-block:: robotframework

            ${root}=    Get Workspace Root
            Log    Project files are in ${root}

        Python example:

        .. code-block:: python

            root = sema4.get_workspace_root()
        """
        return self.workspace.location

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
            ``name`` and ``size`` (bytes). A local workspace adds ``modified``
            (UTC, ISO 8601); a project reached through the REST API adds
            ``sha256`` when the platform reports it.
        :raises WorkspaceFileNotFoundError: The prefix does not exist. Through
            the REST API a directory exists only while it holds a file.

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
        return self.workspace.read_bytes(path).decode(encoding)

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
        return self.workspace.read_bytes(path)

    def write_workspace_file(
        self,
        path: str,
        content: str | bytes,
        overwrite: bool = True,
        encoding: str = "utf-8",
    ) -> str:
        """Create or replace a workspace file. Missing directories are created.

        :param path: Workspace-relative path.
        :param content: Text or bytes to write. The project REST API does not
            accept empty content, so an empty file can only be written on the
            platform or into a local workspace.
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
        if isinstance(content, str):
            data = content.encode(encoding)
        elif isinstance(content, (bytes, bytearray)):
            data = bytes(content)
        else:
            raise TypeError(
                f"File content must be text or bytes, got {type(content).__name__}"
            )
        relative = self.workspace.write_bytes(path, data, overwrite)
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
        local = Path(source).expanduser()
        if not local.is_file():
            raise FileNotFoundError(f"Source file {str(local)!r} does not exist")
        relative = self.workspace.write_bytes(path, local.read_bytes(), overwrite)
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
        data = self.workspace.read_bytes(path)
        local = Path(target).expanduser()
        if local.is_dir():
            local = (
                local
                / str(path).replace("\\", "/").rstrip("/").rsplit("/", maxsplit=1)[-1]
            )
        if local.exists() and not overwrite:
            raise FileExistsError(f"Target file {str(local)!r} already exists")
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(data)
        return str(local.resolve())

    def move_workspace_file(
        self, from_path: str, to_path: str, overwrite: bool = False
    ) -> str:
        """Move or rename a workspace file. Missing directories are created.

        :param from_path: Workspace-relative path of the file to move.
        :param to_path: Workspace-relative destination path.
        :param overwrite: Replace an existing destination file. Through the
            REST API this removes the old destination and then moves the file,
            which is two steps and not atomic.
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
        relative = self.workspace.move_file(from_path, to_path, overwrite)
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
