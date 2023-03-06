from time import sleep

import pytest
from RPA.Assistant import Assistant


def test_set_title_raises(assistant: Assistant):
    with pytest.raises(RuntimeError) as excinfo:
        assistant.set_title("test")
    assert "Flet update called when page is not open" in str(excinfo.value)
