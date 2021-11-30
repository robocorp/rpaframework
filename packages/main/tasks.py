# -*- coding: utf-8 -*-
import os
import platform
import re
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
TOOLS = GIT_ROOT / "tools"
PACKAGE_DIR = GIT_ROOT / "packages" / "main"

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
    "tests/results",
    "*.libspec",
]

if platform.system() == "Windows":
    OS_ROBOT_ARGS = "--exclude skip --exclude posix"
else:
    OS_ROBOT_ARGS = "--exclude skip --exclude windows"


def poetry(ctx, command, **kwargs):
    kwargs.setdefault("echo", True)
    if platform.system() != "Windows":
        kwargs.setdefault("pty", True)

    ctx.run(f"poetry {command}", **kwargs)


@task
def cleanlibspec(ctx):
    files = glob(str(PACKAGE_DIR / "*.libspec"), recursive=False)
    for f in files:
        Path(f).unlink()


def replace_source(m):
    source = m.group(1).replace("\\", "/")
    return f'source="./{source}'


def modify_libspec_files():
    files = glob(str(PACKAGE_DIR / "src" / "*.libspec"), recursive=False)
    pattern = r"source=\"([^\"]+)"
    for f in files:
        outfilename = f"{f}.modified"
        with open(f) as file_in:
            file_content = file_in.read()
            with open(outfilename, "w") as file_out:
                new_content = re.sub(
                    pattern, replace_source, file_content, 0, re.MULTILINE
                )
                file_out.write(new_content)
        target_file = PACKAGE_DIR / Path(f).name
        Path(f).unlink()
        try:
            Path(target_file).unlink()
        except FileNotFoundError:
            pass
        Path(outfilename).rename(target_file)


@task
def clean(ctx):
    """Remove all generated files"""
    for pattern in CLEAN_PATTERNS:
        for path in glob(pattern, recursive=True):
            print(f"Removing: {path}")
            shutil.rmtree(path, ignore_errors=True)


@task
def libspec(ctx):
    """Generate library libspec files"""
    excludes = [
        "RPA.scripts*",
        "RPA.core*",
        "RPA.recognition*",
        "RPA.Desktop.keywords*",
        "RPA.Desktop.utils*",
        "RPA.PDF.keywords*",
        "RPA.Cloud.objects*",
        "RPA.Cloud.Google.keywords*",
        "RPA.Robocorp.utils*",
        "RPA.Dialogs.*",
        "RPA.Windows.keywords*",
        "RPA.Windows.utils*",
    ]
    exclude_commands = [f"--exclude {package}" for package in excludes]
    exclude_strings = " ".join(exclude_commands)
    command = f"run docgen --no-patches --relative-source --format libspec --output src {exclude_strings} rpaframework"
    poetry(ctx, command)
    modify_libspec_files()


@task
def install(ctx):
    """Install development environment"""
    poetry(ctx, "install")


@task(install)
def lint(ctx):
    """Run format checks and static analysis"""
    poetry(ctx, "run black --check src")
    poetry(ctx, f'run flake8 --config {CONFIG / "flake8"} src')
    poetry(ctx, f'run pylint --rcfile {CONFIG / "pylint"} src')


@task(install)
def pretty(ctx):
    """Run code formatter on source files"""
    poetry(ctx, "run black src")


@task(install)
def typecheck(ctx):
    """Run static type checks"""
    # TODO: Add --strict mode
    poetry(ctx, "run mypy src")


@task
def test(ctx):
    """Run Python unit tests and Robot Framework tests"""
    testpython(ctx)
    testrobot(ctx)


@task(install)
def testpython(ctx):
    """Run Python unit tests"""
    poetry(ctx, "run pytest tests/python")


@task(install)
def testrobot(ctx):
    """Run Robot Framework tests"""
    arguments = (
        "--loglevel TRACE --outputdir tests/results --pythonpath tests/resources"
    )
    poetry(
        ctx,
        f"run robot {arguments} {OS_ROBOT_ARGS} -L TRACE tests/robot",
    )


@task(install)
def todo(ctx):
    """Print all TODO/FIXME comments"""
    poetry(ctx, "run pylint --disable=all --enable=fixme --exit-zero src/")


@task(install)
def exports(ctx):
    """Create setup.py and requirements.txt files"""
    poetry(ctx, "export --without-hashes -f requirements.txt -o requirements.txt")
    poetry(
        ctx, "export --dev --without-hashes -f requirements.txt -o requirements-dev.txt"
    )
    # TODO. fix setup.py
    # poetry(ctx, f'run python {TOOLS / "setup.py"}')


@task(cleanlibspec, lint, libspec, test)
def build(ctx):
    """Build distributable python package"""
    poetry(ctx, "build -vv -f sdist")
    poetry(ctx, "build -vv -f wheel")
    cleanlibspec(ctx)


@task(clean, build, help={"ci": "Publish package to devpi instead of PyPI"})
def publish(ctx, ci=False):
    """Publish python package"""
    if ci:
        poetry(ctx, "publish -v --no-interaction --repository devpi")
    else:
        poetry(ctx, "publish -v")
        ctx.run(f'{TOOLS / "tag.py"}')
