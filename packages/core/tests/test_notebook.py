# import pytest
from RPA.core import notebook
from RPA.Tables import Table
from mock import MagicMock
import pytest
import sys


@pytest.fixture
def ipython_mock():
    ipython_mock = MagicMock()
    ipython_mock.__spec__ = object()
    sys.modules["IPython"] = ipython_mock
    sys.modules["IPython.display"] = MagicMock()

    return ipython_mock


link_basic = "https://www.google.fi"
link_long = "https://www.google.com/search?tbm=isch&sxsrf=ALeKk02_OGiFL5hWwtZGIUoo0-15K7uoDg%3A1595496361599&source=hp&biw=1605&bih=870&ei=qVcZX--gIuvGrgTh_LjwCw&q=cat+pictures&oq=cat+pictures&gs_lcp=CgNpbWcQAzICCAAyBAgAEB4yBAgAEB4yBAgAEB4yBAgAEB4yBAgAEB4yBAgAEB4yBAgAEB4yBAgAEB4yBAgAEB46BAgjECc6BQgAELEDUKIhWOswYOkxaABwAHgAgAFeiAGGCJIBAjEymAEAoAEBqgELZ3dzLXdpei1pbWc&sclient=img&ved=0ahUKEwivmfyOh-PqAhVro4sKHWE-Dr4Q4dUDCAc&uact=5"
link_long_expected = link_long[:75] + ".."
imagename = "test.png"
table_empty = Table()
table_one = Table({"one": 1, "two": 2})
table_one_expected = "<tr><th>one</th><th>two</th></tr><tr><td>1</td><td>2</td></tr>"

prints = (
    (dict(text="my test"), "my test<br>"),
    (dict(link=link_basic), f"<a href='{link_basic}'>{link_basic}</a><br>"),
    (dict(link=link_long), f"<a href='{link_long}'>{link_long_expected}</a><br>"),
    (dict(image=imagename), f"<img src='{imagename}'><br>"),
    (dict(table=table_empty), "<table></table><br>"),
    (dict(table=table_one), f"<table>{table_one_expected}</table><br>"),
    (dict(xyz=""), False),
    (dict(), False),
)


@pytest.mark.parametrize("obj,result", prints)
def test_notebook_print(obj, result):
    funcname = "test_notebook_print"
    out = notebook.notebook_print(**obj)
    if result:
        assert out == f"**KW** {funcname}: {result}"
    else:
        assert out is None


def test_notebook_print_with_ipython(ipython_mock):
    out = notebook.notebook_print(text="my test")
    assert out is None
