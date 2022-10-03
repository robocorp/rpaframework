"""Collection of tasks associated with static code analysis and testing
of the code base.
"""
import platform
import os
from pathlib import Path

from invoke import task, Collection

from invocations import shell, config
from invocations.util import REPO_ROOT, safely_load_config, remove_blank_lines

try:
    from colorama import Fore, Style

    color = True
except ModuleNotFoundError:
    color = False

CONFIG = REPO_ROOT / "config"
FLAKE8_CONFIG = CONFIG / "flake8"
PYLINT_CONFIG = CONFIG / "pylint"
PYTHON_TEST_SOURCE = Path("tests/python")
ROBOT_TEST_SOURCE = Path("tests/robot")
ROBOT_TEST_OUTPUT = Path("tests/results")
ROBOT_TEST_RESOURCES = Path("tests/resources")

EXCLUDE_ROBOT_TESTS = ["skip"]
if platform.system() == "Windows":
    EXCLUDE_ROBOT_TESTS.append("posix")
else:
    EXCLUDE_ROBOT_TESTS.append("windows")


@task(config.install)
def lint(ctx):
    """Run format checks and static analysis"""
    if getattr(ctx, "is_meta", False):
        shell.invoke_each(ctx, "code.lint")
    else:
        flake8_config = Path(
            safely_load_config(ctx, "ctx.linters.flake8", FLAKE8_CONFIG)
        )
        pylint_config = Path(
            safely_load_config(ctx, "ctx.linters.pylint", PYLINT_CONFIG)
        )

        shell.poetry(ctx, "run black --diff --check src")
        shell.poetry(ctx, f"run flake8 --config {flake8_config} src")
        shell.poetry(ctx, f"run pylint --rcfile {pylint_config} src")


@task(config.install, aliases=["pretty"])
def format_code(ctx):
    """Run code formatter on source files"""
    if getattr(ctx, "is_meta", False):
        shell.invoke_each(ctx, "code.format-code")
    else:
        shell.run_in_venv(ctx, "black", "src")


@task(
    config.install,
    aliases=["typecheck"],
    help={"strict": "Sets --strict checking for MyPy."},
)
def type_check(ctx, strict=False):
    """Run static type checks"""
    if getattr(ctx, "is_meta", False):
        shell.invoke_each(ctx, f"code.type-check{' --scrict' if strict else ''}")
    else:
        shell.run_in_venv(ctx, "mypy", f"src{' --strict' if strict else ''}")


@task(config.install, aliases=["testpython"])
def test_python(ctx, asynchronous=None):
    """Executes unit tests using pytest."""
    if getattr(ctx, "is_meta", False):
        shell.invoke_each(ctx, f"code.test-python{' -a' if asynchronous else ''}")
    else:
        python_test_source = Path(
            safely_load_config(ctx, "ctx.tests.python.source", PYTHON_TEST_SOURCE)
        )
        return shell.run_in_venv(
            ctx, "pytest", python_test_source, asynchronous=asynchronous
        )


@task(
    config.install,
    aliases=["testrobot"],
    help={
        "robot": (
            "Only run a specific .robot file, any selected file "
            "must have the format 'test_<robot name>.robot'."
        ),
        "test-name": (
            "Run only a specific test from the available test suites or robot file."
        ),
    },
)
def test_robot(ctx, robot=None, test_name=None, asynchronous=None):
    """Run Robot Framework tests."""
    if getattr(ctx, "is_meta", False):
        shell.invoke_each(ctx, f"code.test-robot{' -a' if asynchronous else ''}")
    else:
        # TODO: consider running robot tests using rcc, robot.yaml and conda.yaml.
        robot_test_source = Path(
            safely_load_config(ctx, "ctx.tests.robot.source", ROBOT_TEST_SOURCE)
        )
        robot_test_output = Path(
            safely_load_config(ctx, "ctx.tests.robot.output", ROBOT_TEST_OUTPUT)
        )
        robot_test_resources = Path(
            safely_load_config(ctx, "ctx.tests.robot.resources", ROBOT_TEST_RESOURCES)
        )
        if robot_test_source.exists():
            exclude_list = EXCLUDE_ROBOT_TESTS[:]  # copy of the original list
            if test_name:
                # Run specific explicit task without exclusion. (during development)
                exclude_list.clear()
                robot_test = f' --test "{test_name}" '
            else:
                # Run all tasks and take into account exclusions. (during CI)
                robot_test = " "
            exclude_str = " ".join(f"--exclude {tag}" for tag in exclude_list)
            arguments = (
                f"--runemptysuite --loglevel TRACE --outputdir {robot_test_output} "
                f"--pythonpath {robot_test_resources}"
            )
            if robot:
                robot_test_source /= f"test_{robot}.robot"
            cmds = f"{arguments} {exclude_str}{robot_test}{robot_test_source}"
            return shell.run_in_venv(ctx, "robot", cmds, asynchronous=asynchronous)
        else:
            return shell.run(
                ctx,
                "echo",
                "Robot tests path does not exist, skipping robot tests.",
                echo=False,
                asynchronous=asynchronous,
            )


def _test_async(ctx, python=True, robot=True):
    promises = {}
    results = {}
    if python:
        promises["Python"] = test_python(ctx, asynchronous=True)
    if robot:
        promises["Robot"] = test_robot(ctx, asynchronous=True)
    print("\nTests started asynchronously, please wait for them to finish...\n")
    for test, promise in promises.items():
        results[test] = promise.join()
    for test, result in results.items():
        if color:
            result_header = Fore.BLUE + f"Results from {test} tests:"
            result_msg = Style.RESET_ALL + remove_blank_lines(result.stdout)
        else:
            result_header = f"*** Results from {test} tests:"
            result_msg = remove_blank_lines(result.stdout)
        print(result_header)
        print(result_msg)
        if hasattr(result, "stderr"):
            print(remove_blank_lines(result.stderr))
        print(os.linesep)


@task(
    config.install,
    default=True,
    help={
        "python": "Toggles executing Python unit tests. Defaults to True.",
        "robot": "Toggles executing Robot Framework unit tests. Defaults to True.",
        "asynchronous": (
            "When running both Python and RFW unit tests, setting this "
            "will cause both to execute simultanously."
        ),
    },
)
def test(ctx, python=True, robot=True, asynchronous=False):
    """Run Python unit tests and Robot Framework tests, flags can
    be used to disable either set of tests. Tests can be ran
    in parallel by setting ``--asynchronous`` or by configuration.
    """
    run_async = bool(safely_load_config(ctx, "ctx.tests.asynchronous", asynchronous))

    if safely_load_config(ctx, "is_meta"):
        args = (
            "--python" if python else "--no-python",
            "--robot" if robot else "--no-robot",
            "--asynchronous" if run_async else "",
        )
        shell.invoke_each(ctx, f"code.test {' '.join(args)}")

    elif run_async:
        _test_async(ctx, python, robot)

    else:
        if python:
            test_python(ctx)
        if robot:
            test_robot(ctx)


@task(aliases=["todo"])
def print_todo(ctx):
    """Print all TODO/FIXME comments"""
    if getattr(ctx, "is_meta", False):
        shell.invoke_each(ctx, "code.print-todo")
    else:
        shell.run_in_venv(
            ctx, "pylint", "--disable=all --enable=fixme --exit-zero src/"
        )


# Configure how this namespace will be loaded
ns = Collection("code")
