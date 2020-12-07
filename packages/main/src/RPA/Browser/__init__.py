import logging

try:
    from RPA.Browser.Playwright import Browser as Playwright
except (ImportError, ModuleNotFoundError):
    pass
from RPA.Browser.Selenium import Browser as Selenium


class Browser(Selenium):
    __doc__ = Selenium.__doc__

    def __init__(self, *args, **kwargs):
        logging.warning(
            "This is a deprecated import that will "
            "be removed in favor of RPA.Browser.Selenium"
        )
        super().__init__(*args, **kwargs)
