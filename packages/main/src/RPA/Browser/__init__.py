import logging

from RPA.Browser.Selenium import Browser as Selenium


class Browser(Selenium):
    def __init__(self, *args, **kwargs):
        logging.warning(
            "This is a deprecated import that will be removed in favor of RPA.Browser.Selenium"
        )
        super().__init__(*args, **kwargs)
