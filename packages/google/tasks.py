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
PACKAGE_DIR = GIT_ROOT / "packages" / "google"

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
]


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
    source_match = m.group(1).replace("\\", "/")
    source = source_match.split("site-packages/")
    source_result = source[1] if len(source) == 2 else source[0]
    return f'source="./{source_result}'


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
    """Generate library libspec file"""
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


@task(install)
def test(ctx):
    """Run unittests"""
    poetry(ctx, "run pytest")


@task(install)
def testrobot(ctx, ci=False):
    """Run Robot Framework tests"""
    exclude = "--exclude manual --exclude skip"
    poetry(
        ctx,
        f"run robot -d tests/output {exclude} -L TRACE tests/robot",
    )


# lint, typecheck, test
@task(cleanlibspec, lint, libspec)
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
        poetry(ctx, f'run python {TOOLS / "tag.py"}')
