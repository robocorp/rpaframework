import logging
from RPA.Browser.Selenium import Selenium

try:
    from RPA.Browser.Playwright import Playwright
except ModuleNotFoundError:
    pass


class Browser(Selenium):
    __doc__ = Selenium.__doc__

    def __init__(self, *args, **kwargs):
        logging.warning(
            "This is a deprecated import that will "
            "be removed in favor of RPA.Browser.Selenium"
        )
        super().__init__(*args, **kwargs)
