"""Exceptions raised by the ``RPA.Sema4AI`` library."""


class Sema4AIError(RuntimeError):
    """Base class for every error the library raises on purpose."""


class NotOnPlatformError(Sema4AIError):
    """The operation needs the Sema4.ai platform runtime, and it is not available."""


class WorkspacePathError(Sema4AIError, ValueError):
    """A workspace path is empty, absolute, leaves the workspace or is protected."""


class WorkspaceFileNotFoundError(Sema4AIError, FileNotFoundError):
    """The workspace path does not exist."""


class WorkspaceFileExistsError(Sema4AIError, FileExistsError):
    """The workspace path already exists and overwriting was not allowed."""


class ProjectNotFoundError(Sema4AIError, LookupError):
    """No project, or more than one project, matches the given identifier."""
