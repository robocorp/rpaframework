"""Common tasks for the sema4ai package."""

from pathlib import Path
from invoke import task


@task
def lint(ctx, check=False):
    """Run code quality checks."""
    cmd = "ruff check"
    if not check:
        cmd += " --fix"
    
    ctx.run(cmd)


@task  
def format(ctx, check=False):
    """Format code."""
    cmd = "ruff format"
    if check:
        cmd += " --check"
    
    ctx.run(cmd)


@task
def typecheck(ctx):
    """Run type checking."""
    ctx.run("python -m mypy src/")


@task
def test(ctx):
    """Run tests."""
    ctx.run("python -m pytest tests/")


@task
def build(ctx):
    """Build the package."""
    ctx.run("uv build")


@task
def clean(ctx):
    """Clean build artifacts."""
    import shutil
    import os
    
    dirs_to_clean = ["dist", "build", "*.egg-info"]
    for pattern in dirs_to_clean:
        if "*" in pattern:
            import glob
            for path in glob.glob(pattern):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        elif os.path.exists(pattern):
            shutil.rmtree(pattern)


@task
def docs(ctx):
    """Generate documentation."""
    from RPA.Sema4ai import Sema4ai
    
    # Generate libdoc
    ctx.run("python -m robot.libdoc RPA.Sema4ai docs/Sema4ai.html")
    ctx.run("python -m robot.libdoc RPA.Sema4ai::REST docs/Sema4ai.rst")