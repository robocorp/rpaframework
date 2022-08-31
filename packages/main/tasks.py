# -*- coding: utf-8 -*-

import platform
import shutil
import subprocess
import sys
from glob import glob
from pathlib import Path

from invoke import task, Collection, Context


def _git_root():
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
    output = output.decode().strip()
    return Path(output)


REPO_ROOT = Path(__file__).parents[2].resolve()
CONFIG = REPO_ROOT / "config"
TASKS = REPO_ROOT / "invocations"
PACKAGE_DIR = REPO_ROOT / "packages" / "main"

# Import rpaframework/tasks_common.py module from file location.
# Note to VSCode users, in order to eliminate Pylance import errors
# in the IDE, you must add the following settings to your local project
# .vscode/settings.json file:
#
#     "python.analysis.extraPaths": [
#        "./invoke_tasks"
#    ]
sys.path.append(str(REPO_ROOT))
from invocations.common import (
    shell,
    libspec,
    config,
    PACKAGE_CLEAN_PATTERNS,
    EXCLUDE_ROBOT_TASKS,
)

# invocation or common, one of them needs most tasks, configure collection in tasks
# find similar tasks between packages put in common?


@task
def clean(ctx):
    """Remove all generated files"""
    for pattern in PACKAGE_CLEAN_PATTERNS:
        for path in glob(pattern, recursive=True):
            print(f"Removing: {path}")
            shutil.rmtree(path, ignore_errors=True)


@task
def install(ctx):
    """Install development environment"""
    shell.poetry(ctx, "install")


@task(install)
def lint(ctx):
    """Run format checks and static analysis"""
    shell.poetry(ctx, "run black --diff --check src")
    shell.poetry(ctx, f'run flake8 --config {CONFIG / "flake8"} src')
    shell.poetry(ctx, f'run pylint --rcfile {CONFIG / "pylint"} src')


@task(install)
def pretty(ctx):
    """Run code formatter on source files"""
    shell.poetry(ctx, "run black src")


@task(install)
def typecheck(ctx):
    """Run static type checks"""
    # TODO: Add --strict mode
    shell.poetry(ctx, "run mypy src")


@task
def test(ctx):
    """Run Python unit tests and Robot Framework tests"""
    test_python(ctx)
    test_robot(ctx)


@task(install)
def test_python(ctx):
    """Run Python unit tests"""
    shell.poetry(ctx, "run pytest tests/python")


@task(install)
def test_robot(ctx, robot_name=None, task_robot=None):
    """Run Robot Framework tests."""
    exclude_list = EXCLUDE_ROBOT_TASKS[:]  # copy of the original list
    if task_robot:
        # Run specific explicit task without exclusion. (during development)
        exclude_list.clear()
        task = f'--task "{task_robot}"'
    else:
        # Run all tasks and take into account exclusions. (during CI)
        task = ""
    exclude_str = " ".join(f"--exclude {tag}" for tag in exclude_list)
    arguments = (
        f"--loglevel TRACE --outputdir tests/results --pythonpath tests/resources"
    )
    robot = Path("tests") / "robot"
    if robot_name:
        robot /= f"test_{robot_name}.robot"
    run_cmd = f"robot {arguments} {exclude_str} {task} {robot}"
    shell.run_in_venv(ctx, "robot", run_cmd)


@task(install)
def todo(ctx):
    """Print all TODO/FIXME comments"""
    shell.poetry(ctx, "run pylint --disable=all --enable=fixme --exit-zero src/")


@task(install)
def exports(ctx):
    """Create setup.py and requirements.txt files"""
    shell.poetry(ctx, "export --without-hashes -f requirements.txt -o requirements.txt")
    shell.poetry(
        ctx, "export --dev --without-hashes -f requirements.txt -o requirements-dev.txt"
    )
    # TODO. fix setup.py
    # poetry(ctx, f'run python {TOOLS / "setup.py"}')


@task(libspec.clean_libspec, lint, libspec.build_libspec, test)
def build(ctx):
    """Build distributable python package"""
    shell.poetry(ctx, "build -vv -f sdist")
    shell.poetry(ctx, "build -vv -f wheel")
    libspec.clean_libspec(ctx)


@task(clean, build, help={"ci": "Publish package to devpi instead of PyPI"})
def publish(ctx, ci=False):
    """Publish python package"""
    if ci:
        shell.poetry(ctx, "publish -v --no-interaction --repository devpi")
    else:
        shell.poetry(ctx, "publish -v")
        shell.poetry(ctx, f'run python {TASKS / "tag.py"}')


# NAMESPACE CONSTRUCTION
# ROOT NAMESPACE
ns = Collection()
# add local tasks to root namespace
ns.add_task(config.setup_poetry)
# configure root namespace
ns.configure({"run": {"echo": True}})
if platform.system() != "Windows":
    ns.configure({"run": {"pty": True}})
ns.configure({"package_dir": PACKAGE_DIR})

# DOCS NAMESPACE
docs_ns = Collection("docs")
ns.add_collection(docs_ns)

# LIBSPEC NAMESPACE
libspec_ns = Collection("libspec")
docs_ns.add_collection(libspec_ns)
# add libspec tasks from common tasks
libspec_ns.add_task(
    libspec.build_libspec, name="build", aliases=["libspec", "lib"], default=True
)
libspec_ns.add_task(
    libspec.clean_libspec, name="clean", aliases=["cleanlibspec", "cleanlib"]
)
