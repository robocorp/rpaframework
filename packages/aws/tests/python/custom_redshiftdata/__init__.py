from .models import redshiftdata_backends
from moto.core.models import base_decorator

mock_redshiftdata = base_decorator(redshiftdata_backends)
