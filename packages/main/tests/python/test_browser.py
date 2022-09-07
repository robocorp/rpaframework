import urllib.parse

import pytest
from selenium.webdriver import ChromeOptions

from RPA.Browser.Selenium import Selenium, ensure_scheme

from . import RESOURCES_DIR, temp_filename


@pytest.fixture
def library():
    lib = Selenium()
    yield lib
    lib.close_all_browsers()


def get_chrome_options():
    """Returns `ChromeOptions` with custom arguments and capabilities."""
    options = ChromeOptions()
    options.add_argument("--headless")
    options.set_capability("acceptInsecureCerts", True)
    return options


class TestSelenium:
    """`RPA.Browser.Selenium` library tests."""

    def test_print_to_pdf(self, library):
        testfile = RESOURCES_DIR / "browser_docs.html"
        library.open_available_browser(f"file://{testfile}", headless=True)
        with temp_filename(suffix=".pdf") as tmp_file:
            library.print_to_pdf(tmp_file)
            with open(tmp_file, "rb") as stream:
                data = stream.read()
            assert b"selenium" in data

    @pytest.mark.xfail(reason="Firefox not available")
    def test_print_to_pdf_exception_on_non_supported_driver(self, library):
        testfile = RESOURCES_DIR / "browser_docs.html"
        library.open_available_browser(
            f"file://{testfile}", browser_selection="firefox", headless=True
        )
        err_msg = "PDF printing works only with Chrome/Chromium"
        with pytest.raises(NotImplementedError, match=err_msg):
            library.print_to_pdf(output_path=None)

    @pytest.mark.parametrize(
        "options",
        [
            {
                "arguments": ["--headless"],
                "capabilities": {"acceptInsecureCerts": True},
            },
            {"arguments": "--headless", "capabilities": "acceptInsecureCerts:True"},
            "add_argument('--headless');set_capability('acceptInsecureCerts', True)",
            get_chrome_options(),
        ],
    )
    def test_options_normalization(self, library, options):
        options_obj = library.normalize_options(options, browser="Chrome")
        assert options_obj.headless
        assert options_obj.accept_insecure_certs

    def test_unrecognized_option(self, library):
        options = {"argument": "--headless"}
        with pytest.raises(TypeError):
            library.normalize_options(options, browser="Chrome")

    def test_custom_options(self, library):
        path = "path/to/chrome"
        options = {"binary_location": path}
        options_obj = library.normalize_options(options, browser="Chrome")
        assert options_obj.binary_location == path


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
