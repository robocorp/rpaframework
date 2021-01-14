import os
import tempfile
from pathlib import Path
from unittest import TestCase

import pytest

from RPA.PDF import PDF
from . import RESOURCE_DIR


class TestBrowserFunctionality(TestCase):
    def test_imports(self):
        from RPA.Browser import Browser
        from RPA.Browser.Selenium import Selenium

        Browser()
        Selenium()

    def test_print_to_pdf(self):
        from RPA.Browser.Selenium import Selenium

        selenium_lib = Selenium()

        testfile = RESOURCE_DIR / "browser_docs.html"
        selenium_lib.open_available_browser(f"file://{testfile}", headless=True)
        with tempfile.NamedTemporaryFile() as tmp_file:
            selenium_lib.print_to_pdf(output_path=tmp_file.name)
            text = PDF().get_text_from_pdf(tmp_file.name)

            assert "Please explicitly use either RPA.Browser.Selenium" in text[1]

    def test_print_to_pdf_different_from_start_page(self):
        from RPA.Browser.Selenium import Selenium

        selenium_lib = Selenium()

        startpage = RESOURCE_DIR / "alert.html"
        testfile = RESOURCE_DIR / "browser_docs.html"
        selenium_lib.open_available_browser(f"file://{startpage}", headless=True)
        with tempfile.NamedTemporaryFile() as tmp_file:
            selenium_lib.print_to_pdf(
                source=f"file://{testfile}", output_path=tmp_file.name
            )
            text = PDF().get_text_from_pdf(tmp_file.name)

            assert "Please explicitly use either RPA.Browser.Selenium" in text[1]
