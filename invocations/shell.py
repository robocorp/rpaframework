import os
import platform
from pathlib import Path
import re
from typing import Union
from invoke import Context

from invocations.util import REPO_ROOT, get_package_paths, remove_blank_lines

try:
    from colorama import Fore, Style

    color = True
except ModuleNotFoundError:
    color = False

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


def get_venv_activate_cmd(is_meta: bool, package_dir: Union[str, Path] = None) -> str:
    """Determines and returns the path to the package's .venv
    activation scripts based on configuration values passed in.
    """
    if is_meta:
        abs_activate_path = REPO_ROOT / REL_ACTIVATE_PATH
    else:
        abs_activate_path = Path(package_dir) / REL_ACTIVATE_PATH
    return ACTIVATE_TEMPLATE.format(abs_activate_path)


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
    # TODO: consider that since this is one invocation package, you could
    #       pass the actual task object.
    our_packages = get_package_paths()
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
        if color:
            result_header = (
                Fore.BLUE + f"Results from 'invoke {command}' for package '{package}':"
            )
            result_msg = Style.RESET_ALL + remove_blank_lines(result.stdout)
        else:
            result_header = (
                f"*** Results from 'invoke {command}' for package '{package}':"
            )
            result_msg = remove_blank_lines(result.stdout)
        print(result_header)
        print(result_msg)
        if hasattr(result, "stderr"):
            print(remove_blank_lines(result.stderr))
        print(os.linesep)
        results.append(result)
    print(f"Invocations complete.")
    return results


def is_poetry_version_2(ctx: Context) -> bool:
    """Determins if the version of Poetry available in the
    provided context is version 2 and returns True if so.
    """
    results = poetry(ctx, "--version", hide=True)
    poetry_version = (
        re.search(SEMANTIC_VERSION_PATTERN, results.stdout).group().split(".")
    )
    return poetry_version[0] == "2"
