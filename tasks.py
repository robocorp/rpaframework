from glob import glob
import platform
import re
import shutil
import toml
import subprocess
from pathlib import Path
from invoke import task, call


def _git_root():
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
    output = output.decode().strip()
    return Path(output)


GIT_ROOT = _git_root()
PACKAGES_ROOT = GIT_ROOT / "packages"

if platform.system() != "Windows":
    ACTIVATE_PATH = GIT_ROOT / ".venv" / "bin" / "activate"
    ACTIVATE = f"source {ACTIVATE_PATH}"
else:
    ACTIVATE_PATH = GIT_ROOT / ".venv" / "Scripts" / "activate"
    ACTIVATE = f"{ACTIVATE_PATH}.bat"


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
        package_paths[project_config["tool"]["poetry"]["name"]] = Path(
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
        packages = _get_package_paths()
        with ctx.prefix(ACTIVATE):
            result = pip(ctx, "freeze", echo=False, hide="out")
            local_packages = re.findall(
                f"^{r'(?=={2})|'.join([str(k) for k in packages.keys()])}(?=={2})",
                result.stdout,
                re.MULTILINE,
            )
            for local_package in local_packages:
                pip(ctx, f"uninstall {local_package} -y")
        poetry(ctx, "install --remove-untracked")
    else:
        poetry(ctx, "install")


@task(pre=[call(install, reset=True)], iterable=["package"])
def install_local(ctx, package):
    """Installs local environment with provided package in local
    editable form instead of from PyPi. This task always resets
    the virtual environment first.

    Package must exist as a subfolder module in ``\\packages``,
    see those packages' ``pyproject.toml`` for package names.
    If ran with no packages, all optional packages will be installed
    from PyPi.

    **WARNING**: This essentially produces a dirty virtual environment
    that is a cross between all local packages requested. It may
    not be stable.
    """
    if package:
        packages = _get_package_paths()
        for pkg in package:
            # activate meta context
            with ctx.prefix(ACTIVATE):
                # uninstall package
                pip(ctx, f"uninstall {pkg} -y")
                # cd to selected package and run poetry install
                with ctx.cd(packages[pkg]):
                    poetry(ctx, "install")
