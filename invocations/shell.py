import os
import platform
from pathlib import Path
import re
from colorama import Fore, Style
from invoke import Context

from invocations.util import (
    REPO_ROOT,
    get_package_paths,
    remove_blank_lines,
    safely_load_config,
)

POETRY = "poetry"
PIP = "pip"
SPHINX = "sphinx-build"
DOCGEN = "docgen"
PYTHON_EXECUTOR = "python"
INVOKE = "invoke"
GIT = "git"

SEMANTIC_VERSION_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(\-((0|[1-9A-Za-z-]+)((\.(0|[1-9A-Za-z-]+))+)?))?(\+(([0-9A-Za-z-]+)((\.([0-9A-Za-z-]+))+)?))?"  # noqa
)

TOOLS_DIR = REPO_ROOT / "tools"

if platform.system() != "Windows":
    REL_ACTIVATE_PATH = Path(".venv") / "bin" / "activate"
    ACTIVATE_TEMPLATE = "source {}"
else:
    REL_ACTIVATE_PATH = Path(".venv") / "Scripts" / "activate"
    ACTIVATE_TEMPLATE = "{}.bat"


def get_venv_activate_cmd(ctx: Context) -> str:
    """Determines and returns the path to the package's .venv
    activation scripts based on the context passed in.
    """
    if safely_load_config(ctx, "is_meta"):
        abs_activate_path = REPO_ROOT / REL_ACTIVATE_PATH
    else:
        abs_activate_path = (
            Path(safely_load_config(ctx, "package_dir")) / REL_ACTIVATE_PATH
        )
    return ACTIVATE_TEMPLATE.format(abs_activate_path.resolve())


def run(ctx: Context, app: str, command: str, **kwargs):
    """Generic run command for any shell executables"""
    return ctx.run(f"{app} {command}", **kwargs)


def poetry(ctx: Context, command: str, **kwargs):
    """Executes poetry commands on the shell."""
    return run(ctx, POETRY, f"{command}", **kwargs)


def run_in_venv(ctx: Context, app: str, command: str, **kwargs):
    """Execute a command within the poetry venv using
    ``poetry run``
    """
    return poetry(ctx, f"run {app} {command}", **kwargs)


def pip(ctx: Context, command: str, **kwargs):
    """Execute a pip command on the shell"""
    return run(ctx, PIP, command, **kwargs)


def sphinx(ctx: Context, command: str, **kwargs):
    """Execute a sphinx command using the venv"""
    return run_in_venv(ctx, SPHINX, command, **kwargs)


def docgen(ctx: Context, command: str, *flags, **kwargs):
    """Execute a docgen command using the venv"""
    cmd = f"{' '.join(flags)} {command}"
    return run_in_venv(ctx, DOCGEN, cmd, **kwargs)


def git(ctx: Context, command: str, **kwargs):
    """Executes a git command on the shell"""
    return run(ctx, GIT, command, **kwargs)


def invoke(ctx: Context, command: str, **kwargs):
    """Executes an invoke command within the current context."""
    return run(ctx, INVOKE, command, **kwargs)


def meta_tool(ctx: Context, tool: str, *args, command: str = None, **kwargs):
    """Runs a python script within the tools directory at the
    root of the repository. If supplied, args will be joined with a
    space on the terminal and ``command`` will be ignored. Alternatively,
    a full ``command`` string can be provided as long as no ``args`` are
    provided.
    """
    if tool[-3:] != ".py":
        tool_path = TOOLS_DIR / f"{tool}.py"
    else:
        tool_path = TOOLS_DIR / tool
    return run_in_venv(
        ctx,
        PYTHON_EXECUTOR,
        f"{tool_path} {' '.join([str(a) for a in args]) if args else command}",
        **kwargs,
    )


def package_invoke(ctx: Context, directory: Path, command: str, **kwargs):
    """Runs invoke within the specified package directory."""
    with ctx.cd(directory):
        return run(ctx, INVOKE, command, **kwargs)


def invoke_each(ctx: Context, command, **kwargs):
    """Runs invoke within each package"""
    our_packages = get_package_paths()
    promises = {}
    for _, pkg in our_packages.items():
        print(
            f"Starting asyncronous task 'invoke {command}' for package '{pkg['name']}'"
        )
        promises[pkg["name"]] = package_invoke(
            ctx, pkg["path"], command, asynchronous=True, warn=True, **kwargs
        )
    print("\nPlease wait for invocations to finish...\n")
    results = []
    for pkg_name, promise in promises.items():
        result = promise.join()
        result_header = (
            Fore.BLUE + f"Results from 'invoke {command}' for package '{pkg_name}':"
        )
        result_msg = Style.RESET_ALL + remove_blank_lines(result.stdout)
        print(result_header)
        print(result_msg)
        if hasattr(result, "stderr"):
            print(remove_blank_lines(result.stderr))
        print(os.linesep)
        results.append(result)
    total_errors = [r.ok for r in results].count(False)
    color = Fore.RED if total_errors > 0 else Fore.GREEN
    print(
        color
        + "Invocations complete."
        + (f" {total_errors} tasks failed." if total_errors else "")
        + Style.RESET_ALL
    )
    return results


def is_poetry_version_2(ctx: Context) -> bool:
    """Determins if the version of Poetry available in the
    provided context is version 1.2 and returns True if so.
    """
    results = poetry(ctx, "--version", hide=True)
    poetry_version = (
        re.search(SEMANTIC_VERSION_PATTERN, results.stdout).group().split(".")
    )
    return poetry_version[0] >= "1" and poetry_version[1] >= "2"
