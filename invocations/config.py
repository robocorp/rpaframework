"""Common invoke tasks that configure the development and/or run
environment.
"""

import errno
import json
import os
import re
import shutil
from glob import glob
from pathlib import Path
import toml
from colorama import Fore, Style

from invoke import task, ParseError, Collection

from invocations import shell
from invocations.util import (
    MAIN_PACKAGE,
    PACKAGES_ROOT,
    REPO_ROOT,
    get_current_package_name,
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
    ".coverage",
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
    artifacts, but you can use flags to modify default. If the venv
    is selected to be cleaned, the local packages are reset as well, see
    documentation for ``install.reset-local`` for more information.

    * ``--no-venv``: Disables removing the .venv directory and
      all caches (e.g., ``__pycache__``).
    * ``--no-build``: Disables removing all build artifacts.
    * ``--no-test``: Disables removing all test artifacts and
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
        reset_local(ctx)
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
        shell.invoke_each(ctx, "install.clean")


@task(
    help={
        "username": (
            "Configures credentials for PyPI or a devpi repository. "
            "The username will be stored by Poetry in the system keyring."
        ),
        "password": (
            "Configures credentials for PyPI or a devpi repository. "
            "The password will be stored by Poetry in the system keyring."
        ),
        "token": (
            "Can be used in place of '--username' and '--password', "
            "the token must be prefixed by 'pypi-'."
        ),
        "devpi-url": (
            "Provide a dev PyPi repositry URL to configure it for use "
            "with the task 'publish --ci'."
        ),
    }
)
def setup_poetry(
    ctx,
    username=None,
    password=None,
    token=None,
    devpi_url=None,
):
    """Configure local poetry installation for development.

    You may provide credentials to the production PyPI
    repository through the use of the ``--username`` and
    ``--password`` or ``--token`` arguments. Poetry uses
    the system ``keyring`` so the password is not stored
    in the clear.

    You can configure a dev PyPI repository if you provide
    it via argument ``--devpi-url``. If doing so, you must
    also provide credentials either as ``--username`` and
    ``--password`` or ``--token``.

    When setting ``--token`` to use a pypi token, be sure
    to include the ``pypi-`` prefix in the token.

    NOTE: Internal Robocorp developers can use
    ``https://devpi.robocorp.cloud/ci/test`` as the devpi_url
    and obtain credentials from the Robocorp internal
    documentation.
    """
    if (
        (username is not None and password is not None and token is not None)
        or (username is not None and password is None)
        or (username is None and password is not None)
    ):
        raise ParseError("You must specify a username-password combination or token.")
    repository = "pypi" if devpi_url is None else "devpi"

    # if not safely_load_config(ctx, "ctx.is_ci_cd", False):
    # TODO. the config --no-interaction --local virtualenvs.in-project true is needed by the Docs run
    shell.poetry(ctx, "config --no-interaction --local virtualenvs.in-project true")
    shell.poetry(ctx, "config --no-interaction --local virtualenvs.create true")
    shell.poetry(ctx, "config --no-interaction --local virtualenvs.path null")
    shell.poetry(ctx, "config --no-interaction --local installer.parallel true")

    if username is not None:
        print(f"Setting username and password for repository '{repository}'.")
        shell.poetry(
            ctx,
            f"config --no-interaction http-basic.{repository} {username} {password}",
            echo=False,
        )
    elif token is not None:
        print(f"Setting token for repository '{repository}'.")
        shell.poetry(
            ctx, f"config --no-interaction pypi-token.{repository} {token}", echo=False
        )
    else:
        print(
            "WARNING: PyPI credentials not configured, invoke "
            "setup-poetry with the --username and --password "
            "or --token parameters to configure."
        )

    if devpi_url is not None:
        clear_poetry_devpi(ctx)
        shell.poetry(
            ctx,
            f"config --no-interaction --local repositories.devpi '{devpi_url}'",
        )
    else:
        print(
            "WARNING: Dev PyPI repository not configured, invoke "
            "setup-poetry with the --devpi-url and --username and "
            "--password or --token parameters to configure."
        )


def clear_poetry_devpi(ctx):
    """Removes any devpi configurations in the current Poetry context."""
    current_config = toml.load(get_poetry_config_path(ctx))
    if current_config.get("repositories", {}).get("devpi", {}).get("url"):
        shell.poetry(
            ctx, "config --no-interaction --local --unset repositories.devpi.url"
        )
    if current_config.get("repositories", {}).get("devpi", {}):
        shell.poetry(ctx, "config --no-interaction --local --unset repositories.devpi")


@task(
    default=True,
    iterable=["extra"],
    help={
        "reset": (
            "Will reset the environment and restore backed up versions "
            "of pyproject.toml and poetry.lock. It will then sync the "
            "environment to that original lock file."
        ),
        "extra": (
            "A repeatable argument to have project-defined extras "
            "installed. To specify multiple extras, you must specify "
            "this argument flag for each, e.g. '--extra playwright "
            "--extra aws'."
        ),
        "all-extras": "All extras can be installed with this flag.",
    },
)
def install(ctx, reset=False, extra=None, all_extras=False):
    """Install development environment. If ``reset`` is set,
    poetry will revert changes caused by ``install.local``.
    You can install package extras as defined in the
    ``pyproject.toml`` with the ``--extra``
    parameter. You can repeat this parameter for each extra
    you wish to install. Alternatively, you can specify
    ``--all-extras`` to install with all extras.

    If ``reset`` is attempted before an initial install, it
    is ignored.
    """
    poetry_config_path = get_poetry_config_path(ctx)
    if not is_poetry_configured(poetry_config_path):
        shell.invoke(ctx, "install.setup-poetry", echo=False)
    if all_extras:
        extras_cmd = f"--all-extras"
    elif extra:
        extras_cmd = f"--extras \"{' '.join(extra)}\""
    else:
        extras_cmd = ""
    if reset:
        reset_local(ctx)
        shell.poetry(ctx, f"install --sync {extras_cmd}")

    else:
        shell.poetry(ctx, f"install {extras_cmd}")


@task(aliases=["reset"])
def reset_local(ctx):
    """Revert changes caused by ``install.local``. This task
    only restores dependency files and uninstalls editable
    versions of local packages.

    If ``reset`` is attempted before an initial install, it
    is ignored.
    """
    venv_activation_cmd = shell.get_venv_activate_cmd(ctx)
    if Path(venv_activation_cmd).exists():
        try:
            restore_dependency_files(ctx)
        except FileNotFoundError:
            print(
                Fore.RED + "Original dependency files cannot be restored. "
                "Please restore manually if required." + Style.RESET_ALL
            )
        our_pkg_name = [
            get_current_package_name(ctx),
            "rpaframework" if safely_load_config(ctx, "is_meta", False) else None,
        ]
        with ctx.prefix(venv_activation_cmd):
            pip_freeze = shell.pip(ctx, "list --format json", echo=False, hide="out")
            # Identifies locally installed packages in development mode.
            #  (not from PyPI)
            installed_pkgs = json.loads(pip_freeze.stdout)
            local_pkgs = [
                pkg
                for pkg in installed_pkgs
                if pkg["name"] not in our_pkg_name
                and pkg.get("editable_project_location", False)
            ]
            for local_pkg in local_pkgs:
                shell.pip(ctx, f"uninstall {local_pkg['name']} -y")
    else:
        print("No .venv exists to reset.")


@task(
    iterable=["package", "extra"],
    aliases=["local"],
    help={
        "package": (
            "Mandatory argument which specifies the local package to "
            "install. You can use either the package name as defined "
            "in the package's pyproject.toml or you can use the "
            "directory name the package exists in."
        ),
        "extra": (
            "A repeatable argument to have project-defined extras "
            "installed. To specify multiple extras, you must specify "
            "this argument flag for each, e.g. '--extra playwright "
            "--extra aws'."
        ),
        "all-extras": (
            "If Poetry v1.2 is installed on the system, all extras can "
            "be installed with this flag."
        ),
    },
)
def install_local(ctx, package, extra=None, all_extras=False):
    """Installs local environment with packages in local editable form
    instead of from PyPi. You can install current package extras
    as well, see help for ``invoke install`` for further
    documentation. If this has already been run for the current package
    a backup of the poetry files will not be done and the provided
    package will be added in to the current development environment.

    NOTE: This temporarily modifies the project's ``pyproject.toml`` and
    ``poetry.lock`` files. Backups is retained at
    ``.pyproject.original`` and ``.poetrylock.original`` and should not
    be modified while the environment is in this state. If it removed,
    you will need to restore them via git.

    You should not select an extra you are also installing with
    the ``--package`` argument as it may be installed in non-editable
    form.

    Package must exist as a sub-folder module in ``./packages``,
    see those packages' ``pyproject.toml`` for package names and
    local dependency groups must be defined (for new projects,
    see ``main`` configuration for example).

    If ran with no packages, all optional packages will be installed
    locally.

    In order to select multiple packages, the ``--package`` option
    must be specified for each package choosen, for example:

    .. code-block:: shell

        invoke install-local --package rpaframework-aws --package rpaframework-pdf
    """
    backup_dependency_files(ctx)
    valid_packages = get_package_paths()
    if not package:
        package = valid_packages.keys()
    opt_dependencies = []
    for pkg in package:
        if "rpaframework-" in pkg:
            pkg_name = re.search(r"(?<=-).*$", pkg).group(0)
        elif pkg == "rpaframework":
            pkg_name = "main"
        else:
            pkg_name = pkg
        pkg_root = get_current_package_root(ctx)
        dependency_path = PACKAGES_ROOT / pkg_name
        opt_dependencies.append(str(relative_path(pkg_root, dependency_path)))
        add_arg = " ".join(opt_dependencies)
    shell.poetry(ctx, f"add --editable {add_arg}")


def relative_path(first_path: Path, second_path: Path) -> Path:
    """Returns a relative path to second_path from first_path.
    The paths must have a common set of parents in their tree.

    Note: using this function iterates through all contents of
    parent directories of ``first_path`` and thus my hinder
    performance if it must traverse the tree up more than one
    or two levels.
    """
    if second_path.is_relative_to(first_path):
        return second_path.relative_to(first_path)
    else:
        for dir in first_path.parent.iterdir():
            if dir.is_dir() and dir == second_path:
                return Path("..") / dir.stem
        return Path("..") / relative_path(first_path.parent, second_path)


def get_current_package_root(ctx) -> Path:
    """Returns the root of the package the current context is
    operating in as a Path.
    """
    if safely_load_config(ctx, "is_meta"):
        return REPO_ROOT
    else:
        return Path(safely_load_config(ctx, "package_dir"))


def get_dependency_paths(ctx, backup=True):
    package_dir = get_current_package_root(ctx)

    spec_orig = package_dir / "pyproject.toml"
    spec_backup = package_dir / ".pyproject.original"
    lock_orig = package_dir / "poetry.lock"
    lock_backup = package_dir / ".poetrylock.original"
    if backup:
        return spec_orig, spec_backup, lock_orig, lock_backup
    else:
        return spec_backup, spec_orig, lock_backup, lock_orig


def backup_dependency_files(ctx):
    spec_src_path, spec_dest_path, lock_src_path, lock_dest_path = get_dependency_paths(
        ctx
    )
    if spec_dest_path.exists() or lock_dest_path.exists():
        print("Backup files exist, no backup will be completed.")
    else:
        print("Attempting to backup pyproject.toml and poetry.lock")
        shutil.copyfile(spec_src_path, spec_dest_path)
        if lock_src_path.exists():
            shutil.copyfile(lock_src_path, lock_dest_path)
            was_lock = True
        else:
            was_lock = False
        warn_msg = (
            f"WARNING: Original pyproject.toml {'and poetry.lock' if was_lock else ''} "
            f"backed up at .pyproject.original {'and .poetrylock.original' if was_lock else ''}. "
            f"Do not modify or remove without calling invoke install.reset"
        )
        print(Fore.RED + warn_msg + Style.RESET_ALL)


def restore_dependency_files(ctx):
    spec_src_path, spec_dest_path, lock_src_path, lock_dest_path = get_dependency_paths(
        ctx, backup=False
    )
    print("Attempting to restore pyproject.toml and poetry.lock")
    if spec_src_path.exists():
        shutil.copyfile(spec_src_path, spec_dest_path)
        os.remove(spec_src_path)
        print("Package pyproject.toml file restored")
    else:
        print(f"The file {spec_src_path.name} does not exist and cannot be restored.")
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), spec_src_path.name
        )

    if lock_src_path.exists():
        shutil.copyfile(lock_src_path, lock_dest_path)
        os.remove(lock_src_path)
        print("Lock file restored successfully.")
    else:
        print("No lock file existed to be restored.")


@task(
    aliases=["update"],
    help={
        "all": (
            "If this flag is used at the meta package level, all "
            "packages will be updated."
        )
    },
)
def install_updates(ctx, all=False):
    """Checks for package dependency updates and rewrites the Poetry
    lock file.
    """
    if all and safely_load_config(ctx, "is_meta", False):
        shell.invoke_each(ctx, "install.update")
    else:
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
