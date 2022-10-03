from RPA.recognition import utils


def test_clamp():
    assert utils.clamp(1, 50, 100) == 50
    assert utils.clamp(1, 1, 100) == 1
    assert utils.clamp(1, 100, 100) == 100
    assert utils.clamp(1, -2, 100) == 1
    assert utils.clamp(0, 1, 0) == 0
    assert utils.clamp(1, 99, 100) == 99
    assert utils.clamp(1, 110, 100) == 100


def test_log2lin():
    assert utils.log2lin(1, 1, 100) == 1
    assert utils.log2lin(1, 100, 100) == 100
    assert int(utils.log2lin(1, 50, 100)) == 85
    assert int(utils.log2lin(1, 80, 100)) == 95
