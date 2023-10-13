import pytest


class TestOutlook:
    """Gathers `RPA.Outlook.Application` tests."""

    @pytest.fixture
    def Application(self):
        from RPA.Outlook.Application import Application

        return Application

    @pytest.fixture
    def app(self, Application):
        return Application()

    @pytest.fixture
    def custom_app(self, Application):
        class CustomApplication(Application):
            """Some test docstring."""

        return CustomApplication()

    @pytest.fixture
    def custom_app_no_docs(self, Application):
        class CustomApplication(Application):
            pass

        return CustomApplication()

    def test_import(self, app):
        assert app.__doc__.startswith("`Outlook.Application`")

    def test_custom_import(self, custom_app):
        assert custom_app.__doc__.startswith("Some test docstring.")

    def test_custom_import_no_docs(self, custom_app_no_docs):
        assert custom_app_no_docs.__doc__.startswith("`Outlook.Application`")
