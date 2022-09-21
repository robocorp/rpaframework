"""Collection of tasks associated with building and publishing 
packages.
"""
from invoke import task, Collection, ParseError

from invocations import shell, config, libspec, util


@task(
    pre=[
        util.require_package,
        config.install,
        libspec.clean_libspec,
        libspec.build_libspec,
    ],
    default=True,
    help={
        "test": (
            "Toggles linting and testing of code before building the "
            "code. Should only be disabled when building for ci."
        )
    },
)
def build(ctx, test=True):
    """Build a distributable python package. By default this task
    will lint and test the code before attempting to build it, you
    can set ``--no-test`` to disable this behaviour, but that argument
    should only be used for CI publishing.
    """
    if getattr(ctx, "is_meta", False):
        shell.invoke_each(ctx, "build")
    else:
        if test:
            shell.invoke("code.lint", echo=False)
            shell.invoke("code.test -a", echo=False)
        shell.poetry(ctx, "build -vv -f sdist")
        shell.poetry(ctx, "build -vv -f wheel")
        libspec.clean_libspec(ctx)


@task(
    aliases=["vers", "ver", "v"],
    help={
        "version": (
            "Bumps the package version as part of "
            "publishing if a valid bump rule is provided."
        )
    },
)
def version(ctx, version=None):
    """When ran with no arguments, returns the package's current version
    as defined in its pyproject.toml. If a valid semver version number
    or bump rule is supplied, it will update the version accordingly.
    """
    if version is not None:
        shell.poetry(ctx, f"version {version}", echo=False)
    else:
        shell.poetry(ctx, "version", echo=False)


@task(
    pre=[
        util.require_package,
    ],
    help={
        "ci": (
            "publishes to the devpi repository as configured via the "
            "install.setup-poetry task. This will disable cleaning and "
            "testing. If you want to run cleaning and testing before "
            "publishing to CI, please chain those tasks via invoke "
            "manually."
        ),
        "build": (
            "Toggles rebuilding distributable packages and "
            "attempts to publish currently existing packages. "
            "Defaults to True, can only be disabled "
            "with ``--ci``."
        ),
        "version": (
            "Bumps the package version as part of "
            "publishing if a valid bump rule is provided."
        ),
    },
    aliases=["pub"],
)
def publish(ctx, ci=False, build_=True, version=None):
    """Publish python package. By default, this task will completely
    clean the dev environment, rebuild the distributable packages and
    then publish to the public production PyPI repository. Arguments can
    be used to modify this behavior:

    * ``--ci``: publishes to the devpi repository as configured via the
      ``install.setup-poetry`` task. This will disable cleaning and
      testing. If you want to run cleaning and testing before publishing
      to CI, please chain those tasks via invoke manually.
    * ``--no-clean``: Disables pre-cleaning, leaving the current
      ``.venv`` in place. Can only be used with ``--ci``. Note: if this
      it not set (e.g., the ``.venv`` is cleaned), ``--build`` will be
      set.
    * ``--no-test``: Disables running unit tests during build. Can only be
      used with ``--ci`` and ``--build``.
    * ``--no-build``: Disables rebuilding distributable packages and
      attempts to publish currently existing packages. Can only be
      used with ``--ci``.
    * ``--version``: You can bump the version of the package by
      providing a valid bump rule. You can provide a valid ``semver``
      version number or one of these bump rules: ``patch``, ``minor``,
      ``major``, ``prepatch``, ``preminor``, ``premajor``,
      ``prerelease``.
    """
    if not build_ and not ci:
        raise ParseError("You cannot disable build when publishing to production.")

    if version:
        shell.invoke(ctx, f"build.version --version {version}", echo=False)
    if not ci:
        shell.invoke(ctx, "install.clean", echo=False)
    if build_:
        test_arg = "--no-test" if ci else ""
        shell.invoke(
            ctx,
            f"install.clean --no-venv --build {test_arg}",
            echo=False,
        )
        shell.invoke(ctx, f"build {test_arg}", echo=False)
    if ci:
        shell.poetry(ctx, "publish -v --no-interaction --repository devpi")
    else:
        shell.poetry(ctx, "publish -v")
        shell.meta_tool(ctx, "tag")


# Configure how this namespace will be loaded.
ns = Collection("build")
