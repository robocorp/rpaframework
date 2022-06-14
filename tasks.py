import platform
import re
import shutil
import subprocess
import toml
from glob import glob
from pathlib import Path

from invoke import task, call


def _git_root():
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
    output = output.decode().strip()
    return Path(output)


GIT_ROOT = _git_root()
PACKAGES_ROOT = GIT_ROOT / "packages"

CLEAN_PATTERNS = [
    "coverage",
    "dist",
    ".cache",
    ".pytest_cache",
    ".venv",
    ".mypy_cache",
]


def _get_package_paths():
    project_tomls = glob(str(PACKAGES_ROOT / "**/pyproject.toml"), recursive=True)
    package_paths = {}
    for project_toml in project_tomls:
        project_config = toml.load(project_toml)
        package_paths[str(project_config["tool"]["poetry"]["name"])] = Path(
            project_toml
        ).parent
    return package_paths


def _run(ctx, app, command, **kwargs):
    kwargs.setdefault("echo", True)
    if platform.system() != "Windows":
        kwargs.setdefault("pty", True)

    return ctx.run(f"{app} {command}", **kwargs)


def poetry(ctx, command, **kwargs):
    return _run(ctx, "poetry", command, **kwargs)


def pip(ctx, command, **kwargs):
    return _run(ctx, "pip", command, **kwargs)


@task
def clean(ctx):
    """Cleans the virtual development environment by
    completely removing build artifacts and the .venv.
    """
    for pattern in CLEAN_PATTERNS:
        for path in glob(pattern, recursive=True):
            print(f"Removing: {path}")
            shutil.rmtree(path, ignore_errors=True)


@task
def install(ctx, reset=False):
    """Install development environment. If ``reset`` is set,
    poetry will remove untracked packages, reverting the
    .venv to the lock file.
    """
    if reset:
        our_packages = _get_package_paths()
        pip_freeze = pip(ctx, "freeze", echo=False, hide="out")
        # Identifies locally installed packages in development mode.
        #  (not from PyPI)
        package_exprs = [rf"{name}(?=={{2}})" for name in our_packages]
        pattern = "|".join(package_exprs)
        local_packages = re.findall(
            pattern,
            pip_freeze.stdout,
            re.MULTILINE | re.IGNORECASE,
        )
        for local_package in local_packages:
            pip(ctx, f"uninstall {local_package} -y")
        poetry(ctx, "install --remove-untracked")
    else:
        poetry(ctx, "install")


@task(pre=[call(install, reset=True)], iterable=["packages"])
def install_local(ctx, packages):
    """Installs local environment with provided package in local
    editable form instead of from PyPi. This task always resets
    the virtual environment first.

    Package must exist as a sub-folder module in ``\\packages``,
    see those packages' ``pyproject.toml`` for package names.
    If ran with no packages, all optional packages will be installed
    from PyPi.

    **WARNING**: This essentially produces a dirty virtual environment
    that is a cross between all local packages requested. It may
    not be stable.
    """
    if not packages:
        return

    our_packages = _get_package_paths()
    for package in packages:
        # Installs our package in development mode under the currently active venv.
        #  (local package)
        pip(ctx, f"uninstall {package} -y")
        with ctx.cd(our_packages[package]):
            poetry(ctx, "install")
