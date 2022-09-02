from invoke import Collection

import invocations


configuration = {"is_meta": True}
ns: Collection = invocations.create_namespace(is_meta=True)
ns.configure(configuration)
