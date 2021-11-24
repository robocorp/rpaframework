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
TOOLS = GIT_ROOT / "tools"

CLEAN_PATTERNS = [
    "coverage",
    "dist",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    "**/__pycache__",
    "**/*.pyc",
    "**/*.egg-info",
    "tests/output",
]


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
def test_robot(ctx):
    """Run Robot Framework tests"""
    poetry(ctx, "run robot -d tests/output -L TRACE tests/test_dialogs.robot")


# lint, typecheck, test
@task(lint)
def build(ctx):
    """Build distributable python package"""
    spec_file = "RPA_Windows.libspec"
    source_file = Path("../../docs/source/libspec") / spec_file
    shutil.copy(source_file, Path(".").resolve())
    poetry(ctx, "build -v")
    try:
        Path(spec_file).unlink()
    except OSError as e:
        pass


@task(clean, build, help={"ci": "Publish package to devpi instead of PyPI"})
def publish(ctx, ci=False):
    """Publish python package"""
    if ci:
        poetry(ctx, "publish -v --no-interaction --repository devpi")
    else:
        poetry(ctx, "publish -v")
