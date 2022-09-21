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
        "all": (
            "If ran from the meta package, this will execute the "
            "publish command for all packages. If also providing "
            "--version, only use a bump rule as it will be applied "
            "to all packages, so if a version number is provided, it "
            "will set them all."
        ),
    },
    aliases=["pub"],
)
def publish(ctx, ci=False, build_=True, version=None, all=False):
    """Publish python package. By default, this task will completely
    clean the dev environment, rebuild the distributable packages and
    then publish to the public production PyPI repository. Arguments can
    be used to modify this behavior:

    * ``--ci``: publishes to the devpi repository as configured via the
      ``install.setup-poetry`` task. This will disable cleaning and
      testing. If you want to run cleaning and testing before publishing
      to CI, please chain those tasks via invoke manually.
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


@task(
    help={
        "ci": (
            "Publishes to the devpi repository as configured via the "
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
            "Bumps the versions of packages as part of "
            "publishing if a valid bump rule is provided."
        ),
    },
    aliases=["puball"],
)
def publish_all(ctx, ci=False, build_=True, version=None):
    """Publish all packages across the meta-package. Can only be called
    from the meta-package level. If you provide a version via
    ``--version``, you should only provide a bump rule because if you
    provide a version number, all packages will be published with that
    version number.

    Arguments can be used to modify this behavior:

    * ``--ci``: publishes to the devpi repository as configured via the
      ``install.setup-poetry`` task. This will disable cleaning and
      testing. If you want to run cleaning and testing before publishing
      to CI, please execute those tasks in their respective packages
      separately.
    * ``--no-build``: Disables rebuilding distributable packages and
      attempts to publish currently existing packages. Can only be
      used with ``--ci``.
    * ``--version``: You can bump the version of the package by
      providing a valid bump rule. You can provide a valid ``semver``
      version number or one of these bump rules: ``patch``, ``minor``,
      ``major``, ``prepatch``, ``preminor``, ``premajor``,
      ``prerelease``.
    """
    if not util.safely_load_config(ctx, "is_meta", False):
        raise ParseError("You must execute this task at the meta-package level")
    args = [
        "--ci" if ci else "",
        "--no-build" if not build_ else "",
        f"--version={version}" if version is not None else "",
    ]
    shell.invoke_each(ctx, f"build.publish {' '.join(args)}")


# Configure how this namespace will be loaded.
ns = Collection("build")
