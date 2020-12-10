from unittest import TestCase


class TestBrowserFunctionality(TestCase):
    def test_imports(self):
        from RPA.Browser import Browser
        from RPA.Browser.Selenium import Selenium

        Browser()
        Selenium()
