import os
from pathlib import Path
import toml
from glob import glob

from invoke import task, ParseError

REPO_ROOT = Path(__file__).parents[2].resolve()
PACKAGES_ROOT = REPO_ROOT / "packages"


def get_package_paths() -> dict:
    """Returns a dictionary of package names available within the
    meta repository where the key of each item is the package name as
    defined in its respective ``pyproject.toml`` and the value is
    the absolute path to that package directory.
    """
    project_tomls = glob(str(PACKAGES_ROOT / "**/pyproject.toml"), recursive=True)
    package_paths = {}
    for project_toml in project_tomls:
        project_config = toml.load(project_toml)
        package_paths[str(project_config["tool"]["poetry"]["name"])] = Path(
            project_toml
        ).parent.resolve()
    return package_paths


def remove_blank_lines(text):
    return os.linesep.join([s for s in text.splitlines() if s])


@task
def require_package(ctx):
    """Checks if the context includes the ``is_meta`` config
    item, and if it does, raises an error because this task
    should only be called from a package.
    """
    if getattr(ctx, "is_meta", False):
        raise ParseError("This task must be called from within a package.")
