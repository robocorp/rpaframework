# -*- coding: utf-8 -*-

import importlib.util
import shutil
import subprocess
import sys
from glob import glob
from pathlib import Path

from invoke import task


# Import rpaframework/tasks_common.py module from file location.
tasks_common_path = Path(__file__).parent.parent.parent / "tasks_common.py"
spec = importlib.util.spec_from_file_location("tasks_common", tasks_common_path)
tasks_common = importlib.util.module_from_spec(spec)
sys.modules["tasks_common"] = tasks_common
spec.loader.exec_module(tasks_common)

poetry = tasks_common.poetry


def _git_root():
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
    output = output.decode().strip()
    return Path(output)


GIT_ROOT = _git_root()
CONFIG = GIT_ROOT / "config"
TOOLS = GIT_ROOT / "tools"
PACKAGE_DIR = GIT_ROOT / "packages" / "pdf"

CLEAN_PATTERNS = [
    "coverage",
    "dist",
    ".cache",
    ".pytest_cache",
    ".venv",
    ".mypy_cache",
    "**/__pycache__",
    "**/*.pyc",
    "**/*.egg-info",
    "tests/output",
    "*.libspec",
    "*.pkl",
]


@task
def libspec(ctx):
    """Generate library libspec files."""
    tasks_common.libspec(ctx, package_dir=PACKAGE_DIR)


@task
def cleanlibspec(ctx):
    tasks_common.cleanlibspec(ctx, package_dir=PACKAGE_DIR)


@task
def clean(_):
    """Remove all generated files."""
    for pattern in CLEAN_PATTERNS:
        for path in glob(pattern, recursive=True):
            print(f"Removing: {path}")
            shutil.rmtree(path, ignore_errors=True)


@task
def install(ctx):
    """Install development environment."""
    poetry(ctx, "install")


@task(install)
def lint(ctx):
    """Run format checks and static analysis."""
    poetry(ctx, "run black --check --diff src tests")
    poetry(ctx, f'run flake8 --config {CONFIG / "flake8"} src')
    poetry(ctx, f'run pylint -j1 --rcfile {CONFIG / "pylint"} src')


@task(install)
def pretty(ctx):
    """Run code formatter on source files."""
    poetry(ctx, "run black src")


@task(install)
def typecheck(ctx):
    """Run static type checks."""
    # TODO: Add --strict mode
    poetry(ctx, "run mypy src")


@task(install)
def test_python(ctx):
    """Run Python unit-tests."""
    poetry(ctx, "run pytest")


@task(install)
def test_robot(ctx):
    """Run Robot Framework tests."""
    exclude = "--exclude manual --exclude skip"
    poetry(
        ctx,
        f"run robot -d tests/output {exclude} -L TRACE tests/robot",
    )


@task(test_python, test_robot)
def test(_):
    """Run all tests."""


# TODO(cmin764): add `typecheck`
@task(cleanlibspec, lint, test, libspec)
def build(ctx):
    """Build distributable python package. (after linting, tests and libspec)"""
    poetry(ctx, "build -vv -f sdist")
    poetry(ctx, "build -vv -f wheel")
    cleanlibspec(ctx)


@task(clean, build, help={"ci": "Publish package to devpi instead of PyPI"})
def publish(ctx, ci=False):
    """Publish python package."""
    if ci:
        poetry(ctx, "publish -v --no-interaction --repository devpi")
    else:
        poetry(ctx, "publish -v")
        ctx.run(f'{TOOLS / "tag.py"}')
