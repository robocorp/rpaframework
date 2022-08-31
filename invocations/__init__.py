"""Available invocations are organized in several namespaces
which can be accessed via dot notation. Use ``invoke --list``
to review all available tasks.
"""
import platform
from invoke import Collection
from invocations import analysis, build, config, docs, libspec

# NAMESPACE CONSTRUCTION
# ROOT NAMESPACE
ns = Collection()
# configure root namespace
ns.configure({"run": {"echo": True}})
if platform.system() != "Windows":
    ns.configure({"run": {"pty": True}})

# INSTALL NAMESPACE
ns.add_collection(Collection.from_module(config, "install"))

# DOCS NAMESPACE
ns.add_collection(Collection.from_module(docs))

# LIBSPEC NAMESPACE
ns.add_collection(Collection.from_module(libspec))

# CODE NAMESPACE
ns.add_collection(Collection.from_module(analysis, "code"))

# BUILD NAMESPACE
ns.add_collection(Collection.from_module(build))
