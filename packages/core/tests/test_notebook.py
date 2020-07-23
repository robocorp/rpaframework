# import pytest
from RPA.core import notebook
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
el_class = "rpafw-notebook"

expected_text = f"<span class='{el_class}-text'>my test</span><br>"
expected_link = f"<a class='{el_class}-link' href='{link_basic}'>{link_basic}</a><br>"
expected_long_link = (
    f"<a class='{el_class}-link' href='{link_long}'>{link_long_expected}</a><br>"
)
expected_image = f"<img class='{el_class}-image' src='{imagename}'><br>"

prints = (
    (dict(text="my test"), expected_text),
    (dict(link=link_basic), expected_link),
    (dict(link=link_long), expected_long_link),
    (dict(image=imagename), expected_image),
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
