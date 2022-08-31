import platform

from invoke import Collection

import invocations


configuration = {"is_meta": True}
ns: Collection = Collection.from_module(invocations, config=configuration)
