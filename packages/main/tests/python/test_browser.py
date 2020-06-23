from unittest import TestCase


class TestBrowserFunctionality(TestCase):
    def test_import(self):
        from RPA.Browser import Browser

        Browser()
