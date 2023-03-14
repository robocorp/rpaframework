import pytest

from RPA.Assistant import Assistant


@pytest.fixture
def assistant() -> Assistant:
    assistant_lib = Assistant()
    return assistant_lib
