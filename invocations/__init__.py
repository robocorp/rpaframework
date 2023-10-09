"""Available invocations are organized in several namespaces
which can be accessed via dot notation. Use ``invoke --list``
to review all available tasks.
"""
import platform

from invoke import Collection

# Exportable config options must be defined before invocation imports
# to prevent circular import errors.
ROBOT_BUILD_STRATEGY = "robot"
PYTHON_BUILD_STRATEGY = "python"

try:
    from invocations import analysis, bootstrap, build, config, docs, libspec

    bootstrap_mode = False
    if not bootstrap.check_dependancy_versions():
        print(
            "Bootstrap mode activated, please check requirements and "
            "use 'invoke install' to update your system."
        )
        bootstrap_mode = True
except ModuleNotFoundError as e:
    from invocations import bootstrap

    bootstrap_mode = True
    print(
        "Some dependencies are missing, tasks are in bootstrap mode. "
        "Use invoke install to install system dependencies and then try "
        "again. "
        f'The error encountered was "{e}"'
    )


DEFAULT_NS_CONFIGURATION = {"run": {"echo": True}, "is_ci_cd": False}
if platform.system() != "Windows":
    DEFAULT_NS_CONFIGURATION["run"]["pty"] = True


def create_namespace(is_meta=False):
    """Creates the standard namespace used throughout this meta-package.

    This function should be used in a ``tasks.py`` at the root of
    your package, for an example, please review the file
    ``/packages/main/tasks.py``.

    Alternate namespace setups can be created by importing the
    individual modules and/or task as necessary and settings them
    to a namespace created in your ``tasks.py``.
    """
    if bootstrap_mode:
        ns = Collection()
        ns.configure(DEFAULT_NS_CONFIGURATION)
        ns.add_task(bootstrap.install_invocations)
    else:
        # NAMESPACE CONSTRUCTION
        # ROOT NAMESPACE
        ns = Collection()
        # configure root namespace
        ns.configure(DEFAULT_NS_CONFIGURATION)

        # INSTALL NAMESPACE
        ns.add_collection(Collection.from_module(config, "install"))

        # DOCS NAMESPACE
        if is_meta:
            ns.add_collection(Collection.from_module(docs))

        # LIBSPEC NAMESPACE
        ns.add_collection(Collection.from_module(libspec))

        # CODE NAMESPACE
        ns.add_collection(Collection.from_module(analysis, "code"))

        # BUILD NAMESPACE
        if not is_meta:
            ns.add_collection(Collection.from_module(build))
        else:
            bd = Collection("build")
            bd.add_task(build.build, name="build-all", aliases=["build"], default=True)
            bd.add_task(build.publish_all, name="publish-all", aliases=["puball"])
            bd.add_task(build.setup_releasenotes)
            ns.add_collection(bd)

        # SELF NAMESPACE
        ns.add_collection(Collection.from_module(bootstrap, "self"))

    return ns
