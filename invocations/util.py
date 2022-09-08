"""Utility functions used throughout the invocations package.
This module should not be added to any package invoke collections.
"""

from functools import reduce
import os
import subprocess
from pathlib import Path
import toml
from glob import glob

from invoke import task, ParseError, Context


def _get_package_root():
    try:
        output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
        output = output.decode().strip()
        return Path(output)
    except (FileNotFoundError, subprocess.SubprocessError):
        # handles the case where git is not installed correctly, but
        # assumes the invocations package is installed from root.
        return Path(__file__).parents[1].resolve()


REPO_ROOT = _get_package_root()
PACKAGES_ROOT = REPO_ROOT / "packages"
MAIN_PACKAGE = PACKAGES_ROOT / "main"


def get_package_paths():
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


def safely_load_config(ctx, config_path, default=None):
    """Tries to load a configuration item from the context provided,
    if it fails to find that configuration item, returns the default.

    The config path must be provided as a string using the same dot
    format expected when loading short-hand config items from
    the context. The leading 'ctx' can be ommitted.

    Example:

    .. code-block:: python

        config_foo_bar = safely_load_config(ctx, 'ctx.foo.bar', DEFAULT_FOO_BAR)
    """
    if not isinstance(ctx, Context):
        raise TypeError(f"ctx: expected Context instance, found {type(ctx)}")
    if not isinstance(config_path, str):
        raise TypeError(
            f"config_path: expected str instance, found {type(config_path)}"
        )
    if config_path[:1] == ".":
        config_path = config_path[1:]
    if config_path[:4] == "ctx.":
        config_path = config_path[4:]
    path_components = config_path.split(".")
    try:
        config_value = reduce(getattr, path_components, ctx)
        return config_value if config_value is not None else default
    except AttributeError:
        return default

    # try:
    #     root = eval(path_components[0])
    # except NameError:
    #     root = ctx
    # if not isinstance(eval(path_components[0]),Context) or assume_ctx:
    #     root = ctx
    # elif isinstance(eval(path_components[0]),Context):
    #     root = eval()
    # for component in path_components:
    #     get_component_value = lambda c:
    # try:
    #     return eval(path)
    # except AttributeError:
    #     return default


@task
def require_package(ctx):
    """Checks if the context includes the ``is_meta`` config
    item, and if it does, raises an error because this task
    should only be called from a package.
    """
    if getattr(ctx, "is_meta", False):
        raise ParseError("This task must be called from within a package.")
