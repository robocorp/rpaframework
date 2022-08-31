"""Collection of tasks associated with static code analysis and testing
of the code base.
"""
import platform
from pathlib import Path

from invoke import task, call, ParseError, Collection

from invocations import shell, config
from invocations.util import REPO_ROOT

CONFIG = REPO_ROOT / "config"
FLAKE8_CONFIG = CONFIG / "flake8"
PYLINT_CONFIG = CONFIG / "pylint"
PYTHON_TEST_SOURCE = Path("tests/python")
ROBOT_TEST_SOURCE = Path("tests/robot")
ROBOT_TEST_OUTPUT = Path("tests/results")
ROBOT_TEST_RESOURCES = Path("tests/resources")

EXCLUDE_ROBOT_TASKS = ["skip"]
if platform.system() == "Windows":
    EXCLUDE_ROBOT_TASKS.append("posix")
else:
    EXCLUDE_ROBOT_TASKS.append("windows")


@task(config.install)
def lint(ctx):
    """Run format checks and static analysis"""
    if getattr(ctx, "is_meta", False):
        shell.invoke_each(ctx, "lint")
    else:
        try:
            flake8_config = Path(ctx.linters.flake8)
        except AttributeError:
            flake8_config = FLAKE8_CONFIG
        try:
            pylint_config = Path(ctx.linters.pylint)
        except AttributeError:
            pylint_config = PYLINT_CONFIG

        shell.poetry(ctx, "run black --diff --check src")
        shell.poetry(ctx, f"run flake8 --config {flake8_config} src")
        shell.poetry(ctx, f"run pylint --rcfile {pylint_config} src")


@task(config.install, aliases=["pretty"])
def format_code(ctx):
    """Run code formatter on source files"""
    if getattr(ctx, "is_meta", False):
        shell.invoke_each(ctx, "format-code")
    else:
        shell.run_in_venv(ctx, "black src")


@task(config.install, aliases=["typecheck"])
def type_check(ctx, strict=False):
    """Run static type checks"""
    shell.run_in_venv(ctx, f"mypy src{' --strict' if strict else ''}")


@task(config.install, aliases=["testpython"])
def test_python(ctx, asynchronous=None):
    """Executes unit tests using pytest."""
    try:
        python_test_source = Path(ctx.tests.python.source)
    except AttributeError:
        python_test_source = PYTHON_TEST_SOURCE
    return shell.run_in_venv(
        ctx, "pytest", python_test_source, asynchronous=asynchronous
    )


@task(config.install, aliases=["testrobot"])
def test_robot(ctx, robot=None, task=None, asynchronous=None):
    """Run Robot Framework tests."""
    try:
        robot_test_source = Path(ctx.tests.robot.source)
    except AttributeError:
        robot_test_source = ROBOT_TEST_SOURCE
    try:
        robot_test_output = Path(ctx.tests.robot.output)
    except AttributeError:
        robot_test_output = ROBOT_TEST_OUTPUT
    try:
        robot_test_resources = Path(ctx.tests.robot.resources)
    except AttributeError:
        robot_test_resources = ROBOT_TEST_RESOURCES

    exclude_list = EXCLUDE_ROBOT_TASKS[:]  # copy of the original list
    if task:
        # Run specific explicit task without exclusion. (during development)
        exclude_list.clear()
        robot_task = f' --task "{task}" '
    else:
        # Run all tasks and take into account exclusions. (during CI)
        robot_task = " "
    exclude_str = " ".join(f"--exclude {tag}" for tag in exclude_list)
    arguments = f"--loglevel TRACE --outputdir {robot_test_output} --pythonpath {robot_test_resources}"
    if robot:
        robot_test_source /= f"test_{robot}.robot"
    cmds = f"{arguments} {exclude_str}{robot_task}{robot_test_source}"
    return shell.run_in_venv(ctx, "robot", cmds, asynchronous=asynchronous)


@task(config.install, default=True)
def test(ctx, python=True, robot=True, asynchronous=None):
    """Run Python unit tests and Robot Framework tests, flags can
    be used to disable either set of tests. Tests can be ran
    in parallel by setting ``--asynchronous`` or by configuration.
    """
    try:
        run_async = bool(ctx.tests.asynchronous)
    except AttributeError:
        run_async = bool(asynchronous) or False

    if getattr(ctx, "is_meta", False):
        args = (
            "--python" if python else "--no-python",
            "--robot" if robot else "--no-robot",
        )
        shell.invoke_each(ctx, f"test {' '.join(args)}")

    elif run_async:
        test_promises = []
        if python:
            test_promises.append(test_python(ctx, asynchronous=True))
        if robot:
            test_promises.append(test_robot(ctx, asynchronous=True))
        for promise in test_promises:
            promise.join()

    else:
        if python:
            test_python(ctx)
        if robot:
            test_robot(ctx)


@task(aliases=["todo"])
def print_todo(ctx):
    """Print all TODO/FIXME comments"""
    shell.run_in_venv(ctx, "pylint", "--disable=all --enable=fixme --exit-zero src/")


# Configure how this namespace will be loaded
ns = Collection("code")
