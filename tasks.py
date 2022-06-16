from glob import glob
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from invoke import task, call, ParseError

try:
    import toml
except ModuleNotFoundError:
    DEPENDENCIES_AVAILABLE = False
else:
    DEPENDENCIES_AVAILABLE = True


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
DOCS_CLEAN_PATTERNS = [
    "docs/build",
    "docs/source/libspec",
    "docs/source/include/libdoc",
    "docs/source/include/latest.json",
    "docs/source/json",
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


def package_invoke(ctx, directory, command, **kwargs):
    with ctx.cd(directory):
        return _run(ctx, "invoke", command, **kwargs)


@task()
def clean(ctx, venv=True, docs=False, all=False):
    """Cleans the virtual development environment by
    completely removing build artifacts and the .venv.
    You can set ``--no-venv`` to avoid this default.

    If ``--docs`` is supplied, the build artifacts for
    local documentation will also be cleaned.

    You can set flag ``all`` to clean all packages as
    well.
    """
    union_clean_patterns = []
    if venv:
        union_clean_patterns.extend(CLEAN_PATTERNS)
    if docs:
        union_clean_patterns.extend(DOCS_CLEAN_PATTERNS)
    for pattern in union_clean_patterns:
        for path in glob(pattern, recursive=True):
            print(f"Removing: {path}")
            shutil.rmtree(path, ignore_errors=True)
            try:
                os.remove(path)
            except OSError:
                pass
    if all:
        our_packages = _get_package_paths()
        for package_path in our_packages.values():
            package_invoke(ctx, package_path, "clean")


@task
def setup_poetry(ctx, username=None, password=None, token=None):
    """Configure local poetry installation for development.
    If you provide ``username`` and ``password``, you can
    also configure your pypi access. Our version of poetry
    uses ``keyring`` so the password is not stored in the
    clear.

    Alternatively, you can set ``token`` to use a pypi token, be sure
    to include the ``pypi-`` prefix in the token.
    """
    poetry(ctx, "config -n --local virtualenvs.in-project true")
    poetry(ctx, "config -n --local virtualenvs.create true")
    poetry(ctx, "config -n --local virtualenvs.path null")
    poetry(ctx, "config -n --local experimental.new-installer true")
    poetry(ctx, "config -n --local installer.parallel true")
    poetry(
        ctx,
        "config -n --local repositories.devpi.url https://devpi.robocorp.cloud/ci/test",
    )
    if username and password and token:
        raise ParseError(
            "You cannot specify username-password combination and token simultaneously"
        )
    if username ^ password:
        raise ParseError("You must specify both username and password")
    if username and password:
        poetry(ctx, f"config -n http-basic.pypi {username} {password}")
    if token:
        poetry(ctx, f"config -n pypi-token.pypi {token}")


@task(pre=[setup_poetry])
def install(ctx, reset=False):
    """Install development environment. If ``reset`` is set,
    poetry will remove untracked packages, reverting the
    .venv to the lock file.

    If ``reset`` is attempted before an initial install, it
    is ignored.
    """
    if not DEPENDENCIES_AVAILABLE:
        poetry(ctx, "install")
    else:
        if reset:
            our_packages = _get_package_paths()
            with ctx.prefix(ACTIVATE):
                pip_freeze = pip(ctx, "freeze", echo=False, hide="out")
                # Identifies locally installed packages in development mode.
                #  (not from PyPI)
                package_exprs = [
                    rf"{name}(?=={{2}})"
                    for name in our_packages
                    if name != "rpaframework"
                ]
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


@task(pre=[call(install, reset=True)], iterable=["package"])
def install_local(ctx, package):
    """Installs local environment with provided package in local
    editable form instead of from PyPi. This task always resets
    the virtual environment first.

    Package must exist as a sub-folder module in ``./packages``,
    see those packages' ``pyproject.toml`` for package names.
    If ran with no packages, all optional packages will be installed
    locally.

    In order to select multiple packages, the ``--package`` option
    must be specified for each package choosen, for example:

    .. code-block:: shell

        invoke install-local --package rpaframework-aws --package rpaframework-pdf

    **WARNING**: This essentially produces a dirty virtual environment
    that is a cross between all local packages requested. It may
    not be stable.
    """
    valid_packages = _get_package_paths()
    if not package:
        package = valid_packages.keys()
    for pkg in package:
        with ctx.prefix(ACTIVATE):
            # Installs our package in development mode under the currently active venv.
            #  (local package)
            pip(ctx, f"uninstall {pkg} -y")
            with ctx.cd(valid_packages[pkg]):
                poetry(ctx, "install")
