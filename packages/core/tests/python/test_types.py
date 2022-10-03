import pytest
from collections import OrderedDict
from RPA.core import types


dicts = (
    (dict(), True),
    (dict(key="value"), True),
    (OrderedDict(), True),
    (OrderedDict(key="value"), True),
    (list(), False),
    (list("value"), False),
    (object(), False),
)


@pytest.mark.parametrize("obj,result", dicts)
def test_is_dict_like(obj, result):
    assert types.is_dict_like(obj) == result
