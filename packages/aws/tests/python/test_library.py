from RPA.Cloud.AWS import AWS


def test_init():
    lib = AWS()
    assert lib
