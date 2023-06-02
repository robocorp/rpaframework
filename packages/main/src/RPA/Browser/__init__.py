import logging

from RPA.Browser.Selenium import Selenium as _Selenium


class Browser(_Selenium):  # pylint: disable=missing-class-docstring
    __doc__ = _Selenium.__doc__

    def __init__(self, *args, **kwargs):
        logging.warning(
            "This is a deprecated import that will "
            "be removed in favor of RPA.Browser.Selenium"
        )
        super().__init__(*args, **kwargs)
