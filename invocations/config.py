"""Common invoke tasks that configure the development and/or run
environment.
"""

import os
import re
import shutil
from glob import glob
from pathlib import Path
import toml

from invoke import task, ParseError, Collection

from invocations import shell
from invocations.util import (
    MAIN_PACKAGE,
    REPO_ROOT,
    get_package_paths,
    safely_load_config,
)

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


def get_poetry_config_path(ctx):
    """Gets a path to the poetry configuration file depending on
    if context is_meta or not.
    """
    if safely_load_config(ctx, "is_meta", False):
        return REPO_ROOT / "poetry.toml"
    else:
        return (
            Path(safely_load_config(ctx, "package_dir", MAIN_PACKAGE)) / "poetry.toml"
        )


@task(
    help={
        "venv": (
            "Removes the .venv directory and all caches (e.g., "
            "__pycache__). Enabled by default."
        ),
        "build": "Removes all build artifacts. Enabled by default.",
        "test": (
            "Removes all test artifacts and any related caches. Enabled by default."
        ),
        "docs": (
            "When invoked from the meta"
            "package level, the build artifacts for local documentation will "
            "also be cleaned. Disabled by default."
        ),
        "all": (
            "When invoked from the meta "
            "package level, all packages across the meta-package will be "
            "cleaned as well. Disabled by default."
        ),
    }
)
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


@task(
    help={
        "devpi-url": (
            "Provide a dev PyPi repositry URL to configure it for use "
            "with the task 'publish --ci'."
        ),
        "username": (
            "Must be provided with '--devpi-url'. The user name will "
            "be stored by Poetry in the system keyring."
        ),
        "password": (
            "Must be provided with '--devpi-url'. The user name will "
            "be stored by Poetry in the system keyring."
        ),
        "token": (
            "Can be used in place of '--username' and '--password', "
            "the token must be prefixed by 'pypi-'."
        ),
    }
)
def setup_poetry(
    ctx,
    devpi_url=None,
    username=None,
    password=None,
    token=None,
):
    """Configure local poetry installation for development.

    You can configure a dev PyPI repository if you provide
    it via argument ``--devpi-url``. If doing so, you must
    also provide credentials either as ``--username`` and
    ``--password`` or ``--token``. Poetry uses ``keyring`` so
    the password is not stored in the clear.

    When setting ``--token`` to use a pypi token, be sure
    to include the ``pypi-`` prefix in the token.

    NOTE: Internal Robocorp developers can use
    ``https://devpi.robocorp.cloud/ci/test`` as the devpi_url
    and obtain credentials from the Robocorp internal
    documentation.
    """
    shell.poetry(ctx, "config -n --local virtualenvs.in-project true")
    shell.poetry(ctx, "config -n --local virtualenvs.create true")
    shell.poetry(ctx, "config -n --local virtualenvs.path null")
    shell.poetry(ctx, "config -n --local experimental.new-installer true")
    shell.poetry(ctx, "config -n --local installer.parallel true")
    if devpi_url:
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
        current_config = toml.load(get_poetry_config_path(ctx))
        if current_config.get("repositories", {}).get("devpi", {}).get("url"):
            shell.poetry(ctx, "config -n --local --unset repositories.devpi.url")
        shell.poetry(
            ctx,
            f"config -n --local repositories.devpi.url '{devpi_url}'",
        )
    else:
        print(
            "WARNING: Dev PyPI repository not configured, invoke "
            "setup-poetry with the --devpi-url and --username and "
            "--password or --token parameters to configure."
        )


@task(
    default=True,
    iterable=["extra"],
    help={
        "reset": (
            "Setting this will remove untracked packages, reverting the "
            ".venv to the lock file. If Poetry v1.2 is installed, the "
            "'--sync' command is used instead."
        ),
        "extra": (
            "A repeatable argument to have project-defined extras "
            "installed. To specify multiple extras, you must specify "
            "this argument flag for each, e.g. '--extra playwright "
            "--extra aws'."
        ),
        "all-extras": (
            "If Poetry v1.2 is installed on the system, all extra can "
            "be installed with this flag."
        ),
    },
)
def install(ctx, reset=False, extra=None, all_extras=False):
    """Install development environment. If ``reset`` is set,
    poetry will remove untracked packages, reverting the
    .venv to the lock file. You can install package extras
    as defined in the ``pyproject.toml`` with the ``--extra``
    parameter. You can repeat this parameter for each extra
    you wish to install. Alternatively, you can specify
    ``--all-extras`` to install with all extras.

    If ``reset`` is attempted before an initial install, it
    is ignored.
    """
    poetry_config_path = get_poetry_config_path(ctx)
    if not is_poetry_configured(poetry_config_path):
        shell.invoke(ctx, "setup_poetry", echo=False)
    if all_extras:
        if shell.is_poetry_version_2(ctx):
            extras_cmd = f" --all-extras"
        else:
            raise ParseError(
                "Argument 'all-extras' is only available with Poetry 1.2. "
                "Please select specific extras when using Poetry 1.1."
            )
    elif extra:
        extras_cmd = f" --extras \"{' '.join(extra)}\""
    else:
        extras_cmd = ""
    if reset:
        our_packages = get_package_paths()
        with ctx.prefix(
            shell.get_venv_activate_cmd(
                safely_load_config(ctx, "is_meta"),
                safely_load_config(ctx, "package_dir"),
            )
        ):
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
        if shell.is_poetry_version_2(ctx):
            shell.poetry(ctx, f"install --sync{extras_cmd}")
        else:
            shell.poetry(ctx, f"install --remove-untracked{extras_cmd}")
    else:
        shell.poetry(ctx, f"install{extras_cmd}")


@task(
    iterable=["package", "extra"],
    aliases=["local"],
    help={
        "package": (
            "Mandatory argument which specifies the local package to "
            "install. You must use the package's name as defined in "
            "its own pyproject.toml."
        ),
        "extra": (
            "A repeatable argument to have project-defined extras "
            "installed. To specify multiple extras, you must specify "
            "this argument flag for each, e.g. '--extra playwright "
            "--extra aws'."
        ),
        "all-extras": (
            "If Poetry v1.2 is installed on the system, all extra can "
            "be installed with this flag."
        ),
    },
)
def install_local(ctx, package, extra=None, all_extras=False):
    """Installs local environment with packages in local editable form
    instead of from PyPi. This task always resets the virtual
    environment first. You can install package extras as well,
    see help for ``invoke install`` for further documentation.

    You should not select an extra you are also installing with
    the ``--package`` argument.

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
    if not all_extras:
        extras_arg = " ".join([f"-e {e}" for e in extra])
    else:
        extras_arg = "--all-extras" if all_extras else "--no-all-extras"
    shell.invoke(ctx, f"install --reset {extras_arg}", echo=False)
    valid_packages = get_package_paths()
    if not package:
        package = valid_packages.keys()
    for pkg in package:
        with ctx.prefix(
            shell.get_venv_activate_cmd(
                safely_load_config(ctx, "is_meta"),
                safely_load_config(ctx, "package_dir"),
            )
        ):
            # Installs our package in development mode under the
            # currently active venv. (local package)
            shell.pip(ctx, f"uninstall {pkg} -y")
            with ctx.cd(valid_packages[pkg]):
                shell.poetry(ctx, "install")


@task(aliases=["update"])
def install_updates(ctx):
    """Checks for package dependency updates and rewrites the Poetry
    lock file.
    """
    shell.poetry(ctx, "update")


@task(aliases=["node"])
def install_node(ctx):
    """Installs and configures a node instance in the poetry .venv.
    Primarily used for ``Playwright`` tasks. This task only
    works when the extra "playwright" is defined in the project's
    ``pyproject.toml``.
    """
    shell.invoke(ctx, 'install --extra "playwright"', echo=False)
    shell.run_in_venv(ctx, "rfbrowser", "init --skip-browsers")


@task(aliases=["hooks"])
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
