"""Common invoke tasks that configure the development and/or run
environment.
"""

import platform
import os
import re
import shutil
from glob import glob
from pathlib import Path
import toml

from invoke import task, call, ParseError, Collection

from invocations import shell
from invocations.util import REPO_ROOT, get_package_paths

VENV_CLEAN_PATTERNS = [
    ".venv",
    ".cache",
    ".mypy_cache",
]
BUILD_CLEAN_PATTERNS = [
    "dist",
    "*.libspec",
    "*.pkl",
]
TEST_CLEAN_PATTERNS = [
    "coverage",
    ".pytest_cache",
    "tests/results",
]
DOCS_CLEAN_PATTERNS = [
    "docs/build",
    "docs/source/libspec",
    "docs/source/include/libdoc",
    "docs/source/include/latest.json",
    "docs/source/json",
]
PACKAGE_VENV_CLEAN_PATTERNS = [
    "**/__pycache__",
    "**/*.pyc",
    "**/*.egg-info",
]


EXPECTED_POETRY_CONFIG = {
    "virtualenvs": {"in-project": True, "create": True, "path": "null"},
    "experimental": {"new-installer": True},
    "installer": {"parallel": True},
}
ROBOCORP_DEVPI_URL = "https://devpi.robocorp.cloud/ci/test"

GIT_HOOKS_DIR = REPO_ROOT / "config" / "git-hooks"


def is_poetry_configured(config_path: Path) -> bool:
    try:
        poetry_toml = toml.load(config_path)
        return all(
            [
                poetry_toml.get(key, None) == value
                for key, value in EXPECTED_POETRY_CONFIG.items()
            ]
        )
    except FileNotFoundError:
        return False


@task
def clean(ctx, venv=True, build=True, test=True, docs=False, all=False):
    """Cleans the virtual development environment depending on parameters
    supplied. Default is to clean the .venv and all build and test
    artifacts, but you can use flags to modify default as described
    below:

    * ``--venv`` (enabled by default): Removes the .venv directory and
      all caches (e.g., ``__pycache__``).
    * ``--build`` (enabled by default): Removes all build artifacts.
    * ``--test`` (enabled by default): Removes all test artifacts and
      any related caches.
    * ``--docs`` (disabled by default): When invoked from the meta
      package level, the build artifacts for local documentation will
      also be cleaned.
    * ``--all`` (disabled by default): When invoked from the meta
      package level, all packages across the meta-package will be
      cleaned as well.
    """
    union_clean_patterns = []
    if venv:
        union_clean_patterns.extend(VENV_CLEAN_PATTERNS)
    if build:
        union_clean_patterns.extend(BUILD_CLEAN_PATTERNS)
    if test:
        union_clean_patterns.extend(TEST_CLEAN_PATTERNS)
    is_meta = getattr(ctx, "is_meta", False)
    if is_meta and docs:
        union_clean_patterns.extend(DOCS_CLEAN_PATTERNS)
    if not is_meta:
        union_clean_patterns.extend(PACKAGE_VENV_CLEAN_PATTERNS)

    for pattern in union_clean_patterns:
        for path in glob(pattern, recursive=True):
            print(f"Removing: {path}")
            shutil.rmtree(path, ignore_errors=True)
            try:
                os.remove(path)
            except OSError:
                pass
    if is_meta and all:
        shell.invoke_each(ctx, "clean")


@task
def setup_poetry(
    ctx,
    username=None,
    password=None,
    token=None,
    devpi_url=None,
):
    """Configure local poetry installation for development.
    If you provide ``username`` and ``password``, you can
    also configure your pypi access. Our version of poetry
    uses ``keyring`` so the password is not stored in the
    clear.

    Alternatively, you can set ``token`` to use a pypi token, be sure
    to include the ``pypi-`` prefix in the token.

    NOTE: Robocorp developers can use ``https://devpi.robocorp.cloud/ci/test``
    as the devpi_url and obtain credentials from the Robocorp internal
    documentation.
    """
    shell.poetry(ctx, "config -n --local virtualenvs.in-project true")
    shell.poetry(ctx, "config -n --local virtualenvs.create true")
    shell.poetry(ctx, "config -n --local virtualenvs.path null")
    shell.poetry(ctx, "config -n --local experimental.new-installer true")
    shell.poetry(ctx, "config -n --local installer.parallel true")
    if devpi_url:
        shell.poetry(
            ctx,
            f"config -n --local repositories.devpi.url '{devpi_url}'",
        )
    if username and password and token:
        raise ParseError(
            "You cannot specify username-password combination and token simultaneously"
        )
    if username and password:
        shell.poetry(ctx, f"config -n http-basic.pypi {username} {password}")
    else:
        raise ParseError("You must specify both username and password")
    if token:
        shell.poetry(ctx, f"config -n pypi-token.pypi {token}")


@task(default=True)
def install(ctx, reset=False):
    """Install development environment. If ``reset`` is set,
    poetry will remove untracked packages, reverting the
    .venv to the lock file.

    If ``reset`` is attempted before an initial install, it
    is ignored.
    """
    if not is_poetry_configured(REPO_ROOT / "poetry.toml"):
        call(setup_poetry)
    if reset:
        our_packages = get_package_paths()
        with ctx.prefix(shell.ACTIVATE):
            pip_freeze = shell.pip(ctx, "freeze", echo=False, hide="out")
            # Identifies locally installed packages in development mode.
            #  (not from PyPI)
            package_exprs = [
                rf"{name}(?=={{2}})" for name in our_packages if name != "rpaframework"
            ]
            pattern = "|".join(package_exprs)
            local_packages = re.findall(
                pattern,
                pip_freeze.stdout,
                re.MULTILINE | re.IGNORECASE,
            )
            for local_package in local_packages:
                shell.pip(ctx, f"uninstall {local_package} -y")
        shell.poetry(ctx, "install --remove-untracked")
    else:
        shell.poetry(ctx, "install")


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
    valid_packages = get_package_paths()
    if not package:
        package = valid_packages.keys()
    for pkg in package:
        with ctx.prefix(shell.ACTIVATE):
            # Installs our package in development mode under the currently active venv.
            #  (local package)
            shell.pip(ctx, f"uninstall {pkg} -y")
            with ctx.cd(valid_packages[pkg]):
                shell.poetry(ctx, "install")


@task
def install_node(ctx):
    """Installs and configures a node instance in the poetry .venv.
    Primarily used for ``Playwright`` tasks.
    """
    shell.run_in_venv(ctx, "rfbrowser init --skip-browsers")


@task
def install_hooks(ctx):
    """Installs standard git hooks."""
    shell.git(ctx, f"config core.hooksPath {GIT_HOOKS_DIR}")


@task
def uninstall_hooks(ctx):
    """Uninstalls the standard git hooks."""
    shell.git(ctx, "config --unset core.hooksPath")


@task
def exports(ctx):
    """Create setup.py and requirements.txt files"""
    shell.poetry(ctx, "export --without-hashes -f requirements.txt -o requirements.txt")
    shell.poetry(
        ctx, "export --dev --without-hashes -f requirements.txt -o requirements-dev.txt"
    )
    # TODO. fix setup.py
    # poetry(ctx, f'run python {TOOLS / "setup.py"}')


# Configure how this namespace will be loaded
ns = Collection("install")
