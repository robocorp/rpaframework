import sys

try:
    from Browser import (
        Browser as Playwright,
    )  # noqa: F401 # pylint: disable=unused-import
except (ModuleNotFoundError, ImportError):
    sys.tracebacklimit = 0
    raise ModuleNotFoundError(
        "Please install robotframework-browser following these instructions\n"
        "https://rpaframework.org/libraries/browser_playwright/index.html#install-instructions"  # noqa: E501
    ) from None
