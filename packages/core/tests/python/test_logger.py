import pytest
from RPA.core import logger


def test_initialize_no_robot():
    assert logger.RobotLogListener()


def test_mute_no_robot():
    lib = logger.RobotLogListener()
    with pytest.raises(RuntimeError):
        lib.mute_run_on_failure("Whatever")


def test_register_no_robot():
    lib = logger.RobotLogListener()
    lib.register_protected_keywords("Whatever")
    assert logger.RobotLogListener.KEYWORDS_TO_PROTECT[-1] == "whatever"
