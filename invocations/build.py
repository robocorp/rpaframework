"""Collection of tasks associated with building and publishing 
packages.
"""
from invoke import task, Collection

from invocations import shell, config, libspec, analysis, util


@task(
    util.require_package,
    libspec.clean_libspec,
    analysis.lint,
    libspec.build_libspec,
    analysis.test,
    default=True,
)
def build(ctx):
    """Build a distributable python package."""
    shell.poetry(ctx, "build -vv -f sdist")
    shell.poetry(ctx, "build -vv -f wheel")
    libspec.clean_libspec(ctx)


@task(
    util.require_package,
    config.clean,
    build,
    help={"ci": "Publish package to devpi instead of PyPI"},
)
def publish(ctx, ci=False):
    """Publish python package."""
    if ci:
        shell.poetry(ctx, "publish -v --no-interaction --repository devpi")
    else:
        shell.poetry(ctx, "publish -v")
        shell.meta_tool(ctx, "tag")


# Configure how this namespace will be loaded.
ns = Collection("build")
