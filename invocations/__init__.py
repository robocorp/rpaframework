"""Available invocations are organized in several namespaces
which can be accessed via dot notation. Use ``invoke --list``
to review all available tasks.
"""
import platform
from invoke import Collection
from invocations import analysis, build, config, docs, libspec

DEFAULT_NS_CONFIGURATION = {"run": {"echo": True}}
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
    ns.add_collection(Collection.from_module(build))

    return ns
