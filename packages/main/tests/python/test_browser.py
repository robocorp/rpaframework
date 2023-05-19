import re
import urllib.parse

import pytest
from selenium.webdriver import ChromeOptions

from RPA.Browser.Selenium import Selenium, ensure_scheme

from . import RESOURCES_DIR, temp_filename


CHROMIUM_HEADLESS = "--headless=new"


@pytest.fixture
def library():
    lib = Selenium()
    yield lib
    lib.close_all_browsers()


def get_chrome_options():
    """Returns `ChromeOptions` with custom arguments and capabilities."""
    options = ChromeOptions()
    options.add_argument(CHROMIUM_HEADLESS)
    options.set_capability("acceptInsecureCerts", True)
    return options


class TestSelenium:
    """`RPA.Browser.Selenium` library tests."""

    def test_print_to_pdf(self, library):
        testfile = RESOURCES_DIR / "browser_docs.html"
        library.open_available_browser(
            f"file://{testfile}", headless=True, browser_selection="Chrome"
        )
        with temp_filename(suffix=".pdf") as tmp_file:
            library.print_to_pdf(tmp_file)
            with open(tmp_file, "rb") as stream:
                data = stream.read()
            assert b"selenium" in data

    @pytest.mark.xfail(reason="Firefox not available")
    def test_print_to_pdf_exception_on_non_supported_driver(self, library):
        testfile = RESOURCES_DIR / "browser_docs.html"
        library.open_available_browser(
            f"file://{testfile}", browser_selection="Firefox", headless=True
        )
        err_expr = re.compile(r"PDF printing works only with Chromium-based browsers")
        with pytest.raises(NotImplementedError, match=err_expr):
            library.print_to_pdf()

    @pytest.mark.parametrize(
        "options",
        [
            {
                "arguments": [CHROMIUM_HEADLESS],
                "capabilities": {"acceptInsecureCerts": True},
            },
            {
                "arguments": CHROMIUM_HEADLESS,
                "capabilities": "acceptInsecureCerts:True",
            },
            f"add_argument('{CHROMIUM_HEADLESS}');set_capability('acceptInsecureCerts', True)",
            get_chrome_options(),
        ],
    )
    def test_options_normalization(self, library, options):
        options_obj = library.normalize_options(options, browser="Chrome")
        args = options_obj.to_capabilities()["goog:chromeOptions"]["args"]
        assert options_obj.accept_insecure_certs
        assert CHROMIUM_HEADLESS in args

    def test_unrecognized_option(self, library):
        options = {"argument": CHROMIUM_HEADLESS}  # expecting "arguments" instead
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
