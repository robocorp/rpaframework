"""Collection of tasks associated with building and publishing 
packages.
"""
import keyring
import yaml
from keyring.errors import KeyringError
from pathlib import Path
from invoke import task, Collection, ParseError, Context, config as inv_config

from invocations import shell, config, libspec, ROBOT_BUILD_STRATEGY
from invocations.util import require_package, safely_load_config, REPO_ROOT


@task(
    pre=[
        require_package,
        config.install,
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
        is_robot_build = (
            safely_load_config(ctx, "build_strategy") == ROBOT_BUILD_STRATEGY
        )
        if test:
            shell.invoke(ctx, "code.lint -e", echo=False)
            shell.invoke(ctx, "code.test -a", echo=False)
        if is_robot_build:
            libspec.clean_libspec(ctx)
            libspec.build_libspec(ctx)
        shell.poetry(ctx, "build -vv -f sdist")
        shell.poetry(ctx, "build -vv -f wheel")
        if is_robot_build:
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
        require_package,
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
        "yes_to_all": (
            "Turns off confirmation prompts before publishing to "
            "the remote package repository."
        ),
    },
    aliases=["pub"],
)
def publish(ctx, ci=False, build_=True, version=None, yes_to_all=False):
    """Publish python package. By default, this task will completely
    clean the dev environment, rebuild the distributable packages and
    then publish to the public production PyPI repository. It will
    fail to publish to production PyPI if the current branch is not
    ``master``. Arguments can be used to modify behavior:

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
    * ``--yes-to-all``: You can deactivate the confirmation prompts
      displayed before publishing to the remote package repository.
    """
    if not build_ and not ci:
        raise ParseError("You cannot disable build when publishing to production.")
    if not ci:
        shell.require_git_branch(ctx)
        shell.invoke(ctx, "install.clean", echo=False)
    if version:
        shell.invoke(ctx, f"build.version --version={version}", echo=False)
    if build_:
        test_arg = "--no-test" if ci else ""
        shell.invoke(
            ctx,
            f"install.clean --no-venv {test_arg}",
            echo=False,
        )
        shell.invoke(ctx, f"build {test_arg}", echo=False)
    if not yes_to_all:
        confirm = input(
            f"Do you wish to publish to the '{'devpi' if ci else 'PyPI'}' repository? (y/N) "
        )
        confirm = confirm.lower() in ["y", "yes", "true", "continue"]
    else:
        confirm = True
    if ci and confirm:
        shell.poetry(ctx, "publish -v --no-interaction --repository devpi")
    elif confirm:
        shell.poetry(ctx, "publish -v")
        shell.meta_tool(ctx, "tag")
    else:
        print("Aborting publish...")


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
    if not safely_load_config(ctx, "is_meta", False):
        raise ParseError("You must execute this task at the meta-package level")
    args = [
        "--ci" if ci else "",
        "--no-build" if not build_ else "",
        f"--version={version}" if version is not None else "",
    ]
    shell.invoke_each(ctx, f"build.publish {' '.join(args)}")


@task(
    help={
        "apikey": "The releasenotes.io apikey to be saved to the system keyring.",
        "project_id": "The releasenotes.io project ID where notes will be posted.",
        "allow_insecure": "Allow tokens to be stored in plaintext config files.",
    }
)
def setup_releasenotes(ctx, apikey, project_id, allow_insecure=False):
    """Configures releasenotes.io used as part of the publish tasks
    to publish release notes. By default, this saves tokens to the
    system keyring. Upon failure, if ``--allow-insecure`` is set, it
    will save settings and credentials in plaintext to to the
    invoke.yaml configuration file.

    * ``--apikey`` (required): The releasenotes.io apikey to be saved
      to the system keyring.
    * ``--project_id``: The releasenotes.io project ID where notes will
      be posted.
    """
    config = {"releasenotes": {}}
    try:
        keyring.set_password("releasenotes", "apikey", apikey)
        config["releasenotes"]["apikey"] = "keyring"
    except KeyringError:
        if allow_insecure:
            config["releasenotes"]["apikey"] = apikey
    config["releasenotes"]["project_id"] = project_id
    if safely_load_config(ctx, "is_meta", False):
        config_file = REPO_ROOT / "invoke.yaml"
    else:
        config_file = (
            Path(safely_load_config(ctx, "package_dir", ctx.cwd)) / "invoke.yaml"
        )
    try:
        with config_file.open("r") as c:
            current_config = yaml.load(c, Loader=yaml.FullLoader)
            current_config.update(config)
            config = current_config
    except (yaml.error.YAMLError, AttributeError, FileNotFoundError):
        pass
    with config_file.open("w") as c:
        yaml.dump(config, c)


def get_releasenotes_config(ctx: Context) -> inv_config.DataProxy:
    """Attempts to retreive the releasenotes configuration from
    the system keyring and invoke configuration in ctx.

    Returns a dictionary representing the complete
    configuration obtained from both keyring and config.
    """
    config = safely_load_config(ctx, "releasenotes")
    if config["apikey"] == "keyring":
        config["apikey"] = keyring.get_password("releasenotes", "apikey")
    return config


# Configure how this namespace will be loaded.
ns = Collection("build")
