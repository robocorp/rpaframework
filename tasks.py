from glob import glob
import os
import platform
import re
import shutil
import subprocess
import toml
from pathlib import Path
from invoke import Promise, task, call, ParseError
from colorama import Fore, Style


def _git_root():
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
    output = output.decode().strip()
    return Path(output)


def _remove_blank_lines(text):
    return os.linesep.join([s for s in text.splitlines() if s])


GIT_ROOT = _git_root()
PACKAGES_ROOT = GIT_ROOT / "packages"
DOCS_ROOT = GIT_ROOT / "docs"
DOCS_SOURCE_DIR = DOCS_ROOT / "source"
DOCS_BUILD_DIR = DOCS_ROOT / "build" / "html"
TOOLS_DIR = GIT_ROOT / "tools"
GIT_HOOKS_DIR = GIT_ROOT / "config" / "git-hooks"

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
DOCGEN_EXCLUDES = [
    "--exclude RPA.core*",
    "--exclude RPA.recognition*",
    "--exclude RPA.scripts*",
    "--exclude RPA.Desktop.keywords*",
    "--exclude RPA.Desktop.utils*",
    "--exclude RPA.PDF.keywords*",
    "--exclude RPA.Cloud.objects*",
    "--exclude RPA.Cloud.Google.keywords*",
    "--exclude RPA.Robocorp.utils*",
    "--exclude RPA.Dialogs.*",
    "--exclude RPA.Windows.keywords*",
    "--exclude RPA.Windows.utils*",
    "--exclude RPA.Cloud.AWS.textract*",
]

EXPECTED_POETRY_CONFIG = {
    "virtualenvs": {"in-project": True, "create": True, "path": "null"},
    "experimental": {"new-installer": True},
    "installer": {"parallel": True},
    "repositories": {"devpi": {"url": "https://devpi.robocorp.cloud/ci/test"}},
}


def _get_package_paths():
    project_tomls = glob(str(PACKAGES_ROOT / "**/pyproject.toml"), recursive=True)
    package_paths = {}
    for project_toml in project_tomls:
        project_config = toml.load(project_toml)
        package_paths[str(project_config["tool"]["poetry"]["name"])] = Path(
            project_toml
        ).parent
    return package_paths


def _is_poetry_configured():
    try:
        poetry_toml = toml.load(GIT_ROOT / "poetry.toml")
        return poetry_toml == EXPECTED_POETRY_CONFIG
    except FileNotFoundError:
        return False


def _run(ctx, app, command, **kwargs):
    kwargs.setdefault("echo", True)
    if platform.system() != "Windows":
        kwargs.setdefault("pty", True)

    return ctx.run(f"{app} {command}", **kwargs)


def poetry(ctx, command, **kwargs):
    return _run(ctx, "poetry", command, **kwargs)


def pip(ctx, command, **kwargs):
    return _run(ctx, "pip", command, **kwargs)


def sphinx(ctx, command, **kwargs):
    return poetry(ctx, f"run sphinx-build {command}", **kwargs)


def docgen(ctx, command, *flags, **kwargs):
    return poetry(ctx, f"run docgen {' '.join(flags)} {command}", **kwargs)


def python_tool(ctx, tool, *args, **kwargs):
    if tool[-3:] != ".py":
        tool_path = TOOLS_DIR / f"{tool}.py"
    else:
        tool_path = TOOLS_DIR / tool
    return poetry(ctx, f"run python {tool_path} {' '.join(args)}", **kwargs)


def package_invoke(ctx, directory, command, **kwargs):
    with ctx.cd(directory):
        return _run(ctx, "invoke", command, **kwargs)


def git(ctx, command, **kwargs):
    return _run(ctx, "git", command, **kwargs)


def invoke_each(ctx, command, **kwargs):
    our_packages = _get_package_paths()
    promises = {}
    for package, path in our_packages.items():
        print(f"Starting asyncronous task 'invoke {command}' for package '{package}'")
        promises[package] = package_invoke(
            ctx, path, command, asynchronous=True, warn=True, **kwargs
        )
    print("\nPlease wait for invocations to finish...\n")
    results = []
    for package, promise in promises.items():
        result = promise.join()
        print(Fore.BLUE + f"Results from 'invoke {command}' for package '{package}':")
        print(Style.RESET_ALL + _remove_blank_lines(result.stdout))
        if result.stderr:
            print(_remove_blank_lines(result.stderr))
        print(os.linesep)
        results.append(result)
    print(f"Invocations complete.")
    return results


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
        invoke_each(ctx, "clean")


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
        "config -n --local repositories.devpi.url 'https://devpi.robocorp.cloud/ci/test'",
    )
    if username and password and token:
        raise ParseError(
            "You cannot specify username-password combination and token simultaneously"
        )
    if username and password:
        poetry(ctx, f"config -n http-basic.pypi {username} {password}")
    else:
        raise ParseError("You must specify both username and password")
    if token:
        poetry(ctx, f"config -n pypi-token.pypi {token}")


@task
def install(ctx, reset=False):
    """Install development environment. If ``reset`` is set,
    poetry will remove untracked packages, reverting the
    .venv to the lock file.

    If ``reset`` is attempted before an initial install, it
    is ignored.
    """
    if not _is_poetry_configured():
        call(setup_poetry)
    if reset:
        our_packages = _get_package_paths()
        with ctx.prefix(ACTIVATE):
            pip_freeze = pip(ctx, "freeze", echo=False, hide="out")
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


@task
def install_node(ctx):
    """Installs and configures a node instance in the poetry .venv.
    Primarily used for ``Playwright`` tasks.
    """
    poetry(ctx, "run rfbrowser init --skip-browsers")


@task(pre=[install])
def build_libdocs(ctx):
    """Generates library specification and documentation using ``docgen``"""
    libspec_promise = docgen(
        ctx,
        "rpaframework",
        "--no-patches",
        "--format libspec",
        "--output docs/source/libspec/",
        *DOCGEN_EXCLUDES,
        asynchronous=True,
    )
    html_promise = docgen(
        ctx,
        "rpaframework",
        "--template docs/source/template/libdoc/libdoc.html",
        "--format html",
        "--output docs/source/include/libdoc/",
        *DOCGEN_EXCLUDES,
        asynchronous=True,
    )
    json_promise = docgen(
        ctx,
        "rpaframework",
        "--no-patches",
        "--format json-html",
        "--output docs/source/json/",
        *DOCGEN_EXCLUDES,
        asynchronous=True,
    )
    libspec_promise.join()
    html_promise.join()
    json_promise.join()
    shutil.copy2(
        "docs/source/template/iframeResizer.contentWindow.map",
        "docs/source/include/libdoc/",
    )


@task(pre=[install, build_libdocs])
def build_docs(ctx):
    """Builds documentation locally. These can then be browsed directly
    by going to ./docs/build/html/index.html or using ``invoke local-docs``
    and navigating to localhost:8000 in your browser.

    If you are developing documentation for an optional package, you must
    use the appropriate ``invoke install-local`` command first.
    """
    sphinx(ctx, f"-M clean {DOCS_SOURCE_DIR} {DOCS_BUILD_DIR}")
    python_tool(ctx, "todos", "packages/main/src", "docs/source/contributing/todos.rst")
    python_tool(
        ctx,
        "merge",
        "docs/source/json/",
        "docs/source/include/latest.json",
    )
    sphinx(ctx, f"-b html -j auto {DOCS_SOURCE_DIR} {DOCS_BUILD_DIR}")
    python_tool(ctx, "rss")


@task
def local_docs(ctx):
    """Hosts library documentation on a local http server. Navigate to
    localhost:8000 to browse."""
    poetry(ctx, "run python -m http.server -d docs/build/html/")


@task
def install_hooks(ctx):
    """Installs standard git hooks."""
    git(ctx, f"config core.hooksPath {GIT_HOOKS_DIR}")


@task
def uninstall_hooks(ctx):
    """Uninstalls the standard git hooks."""
    git(ctx, "config --unset core.hooksPath")


@task
def changelog(ctx):
    """Prints changes in latest release."""
    python_tool(ctx, "changelog")


@task
def lint_each(ctx):
    """Executes linting on all packages."""
    invoke_each(ctx, "lint")
