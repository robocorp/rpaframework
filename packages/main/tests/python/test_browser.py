import os
import tempfile
from pathlib import Path
from unittest import TestCase

import pytest

from RPA.Browser.Selenium import Selenium
from RPA.PDF import PDF

from . import RESOURCE_DIR, temp_filename


selenium_lib = Selenium()


class TestBrowserFunctionality(TestCase):
    def test_print_to_pdf(self):
        testfile = RESOURCE_DIR / "browser_docs.html"
        selenium_lib.open_available_browser(f"file://{testfile}", headless=True)
        with temp_filename() as tmp_file:
            selenium_lib.print_to_pdf(output_path=tmp_file)
            text = PDF().get_text_from_pdf(tmp_file)

            assert "Please explicitly use either RPA.Browser.Selenium" in text[1]

    def test_print_to_pdf_different_from_start_page(self):
        startpage = RESOURCE_DIR / "alert.html"
        testfile = RESOURCE_DIR / "browser_docs.html"
        selenium_lib.open_available_browser(f"file://{startpage}", headless=True)
        with temp_filename() as tmp_file:
            selenium_lib.print_to_pdf(source=f"file://{testfile}", output_path=tmp_file)
            text = PDF().get_text_from_pdf(tmp_file)

            assert "Please explicitly use either RPA.Browser.Selenium" in text[1]

    def test_print_to_pdf_exception_on_non_supported_driver(self):
        testfile = RESOURCE_DIR / "browser_docs.html"
        selenium_lib.open_available_browser(
            f"file://{testfile}", browser_selection="firefox", headless=True
        )

        expected = "PDF printing works only with Chrome/Chromium"

        with pytest.raises(NotImplementedError) as err:
            selenium_lib.print_to_pdf(output_path=None)

        assert str(err.value) == expected
