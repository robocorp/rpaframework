import urllib.parse
import pytest

from RPA.Browser.Selenium import Selenium, ensure_scheme

from . import RESOURCES_DIR, temp_filename


@pytest.fixture()
def library():
    lib = Selenium()
    yield lib
    lib.close_all_browsers()


@pytest.mark.skip()
class TestBrowserFunctionality:
    def test_print_to_pdf(self, library):
        testfile = RESOURCES_DIR / "browser_docs.html"
        library.open_available_browser(f"file://{testfile}", headless=True)
        with temp_filename() as tmp_file:
            library.print_to_pdf(tmp_file)
            # TODO: get the text without PDF library dependency
            # text = PDF().get_text_from_pdf(tmp_file)

            # assert "Please explicitly use either RPA.Browser.Selenium" in text[1]

    def test_print_to_pdf_different_from_start_page(self, library):
        startpage = RESOURCES_DIR / "alert.html"
        testfile = RESOURCES_DIR / "browser_docs.html"
        library.open_available_browser(f"file://{startpage}", headless=True)
        with temp_filename() as tmp_file:
            library.go_to(f"file://{testfile}")
            library.print_to_pdf(output_path=tmp_file)
            # TODO: get the text without PDF library dependency
            # text = PDF().get_text_from_pdf(tmp_file)

            # assert "Please explicitly use either RPA.Browser.Selenium" in text[1]

    def test_print_to_pdf_exception_on_non_supported_driver(self, library):
        testfile = RESOURCES_DIR / "browser_docs.html"
        library.open_available_browser(
            f"file://{testfile}", browser_selection="firefox", headless=True
        )

        expected = "PDF printing works only with Chrome/Chromium"

        with pytest.raises(NotImplementedError) as err:
            library.print_to_pdf(output_path=None)

        assert str(err.value) == expected


@pytest.mark.parametrize(
    "url,default,scheme",
    [
        ("https://www.google.com", "https", "https"),
        ("http://www.google.com", "https", "http"),
        ("www.google.com", "https", "https"),
        ("about:config", "https", "about"),
        ("www.google.com", None, ""),
    ],
)
def test_ensure_scheme(url, default, scheme):
    result = ensure_scheme(url, default)
    parsed = urllib.parse.urlsplit(result)
    assert parsed.scheme == scheme
