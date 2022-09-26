import time
import platform
import pytest
from RPA.Dialogs.dialog import Dialog

IS_LINUX = platform.system() == "Linux"
ELEMENTS = []


@pytest.fixture
def dialog():
    d = Dialog(
        elements=ELEMENTS,
        title="Test title",
        width=640,
        height=480,
        on_top=False,
        debug=False,
    )
    try:
        yield d
    finally:
        if d._process is not None:
            d.stop()


def test_not_started(dialog):
    assert dialog._process is None

    with pytest.raises(RuntimeError):
        dialog.stop()

    with pytest.raises(RuntimeError):
        dialog.poll()

    with pytest.raises(RuntimeError):
        dialog.wait()

    with pytest.raises(RuntimeError):
        dialog.result()


@pytest.mark.skipif(IS_LINUX, reason="Not possible to run in Linux CI")
def test_start(dialog):
    dialog.start()

    end = time.time() + 5
    while time.time() <= end:
        assert not dialog.poll()


@pytest.mark.skipif(IS_LINUX, reason="Not possible to run in Linux CI")
def test_stop(dialog):
    dialog.start()
    dialog.stop()

    with pytest.raises(RuntimeError) as err:
        dialog.result()

    assert str(err.value) == "Stopped by execution"

    # Second stop() should not raise
    dialog.stop()
