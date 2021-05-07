import platform
import shutil
import subprocess
from glob import glob
from pathlib import Path
from invoke import task


def _git_root():
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
    output = output.decode().strip()
    return Path(output)


GIT_ROOT = _git_root()
CONFIG = GIT_ROOT / "config"

CLEAN_PATTERNS = [
    "coverage",
    "dist",
    ".cache",
    ".pytest_cache",
    "**/__pycache__",
    "**/*.pyc",
    "**/*.egg-info",
]

def yarn(ctx, command, **kwargs):
    kwargs.setdefault("echo", True)
    if platform.system() != "Windows":
        kwargs.setdefault("pty", True)

    ctx.run(f"yarn {command}", **kwargs)


def poetry(ctx, command, **kwargs):
    kwargs.setdefault("echo", True)
    if platform.system() != "Windows":
        kwargs.setdefault("pty", True)

    ctx.run(f"poetry {command}", **kwargs)


@task
def clean(ctx):
    """Remove all generated files"""
    for pattern in CLEAN_PATTERNS:
        for path in glob(pattern, recursive=True):
            print(f"Removing: {path}")
            shutil.rmtree(path, ignore_errors=True)

    yarn(ctx, "clean")


@task
def install(ctx):
    """Install development environment"""
    poetry(ctx, "install")
    yarn(ctx, "install --immutable")


@task(install)
def lint(ctx):
    """Run format checks and static analysis"""
    poetry(ctx, "run black --check RPA")
    poetry(ctx, f'run flake8 --config {CONFIG / "flake8"} RPA')
    poetry(ctx, f'run pylint --rcfile {CONFIG / "pylint"} RPA')
    yarn(ctx, "lint")


@task(install)
def pretty(ctx):
    """Run code formatter on source files"""
    poetry(ctx, "run black RPA")
    yarn(ctx, "pretty")


@task(install)
def typecheck(ctx):
    """Run static type checks"""
    # TODO: Add --strict mode
    poetry(ctx, "run mypy RPA")
    yarn(ctx, "typecheck")


@task(install)
def test(ctx):
    """Run unittests"""
    poetry(ctx, "run pytest")
    yarn(ctx, "test --passWithNoTests")


@task(install, help={"dev": "Development build of front-end"})
def build_js(ctx, dev=False):
    """Build javascript files"""
    if dev:
        yarn(ctx, "build-dev")
    else:
        yarn(ctx, "build")


@task(lint, typecheck, test, build_js)
def build(ctx):
    """Build distributable python package"""
    poetry(ctx, "build -v")


@task(clean, build, help={"ci": "Publish package to devpi instead of PyPI"})
def publish(ctx, ci=False):
    """Publish python package"""
    if ci:
        poetry(ctx, "publish -v --no-interaction --repository devpi")
    else:
        poetry(ctx, "publish -v")


@task(install)
def storybook(ctx):
    """Start UI component explorer"""
    yarn(ctx, "storybook")
