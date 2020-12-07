try:
    from Browser import Browser  # noqa: F401 # pylint: disable=unused-import
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "Please install robotframework-browser following these instructions"
        "https://rpaframework.org/libraries/browser_playwright/index.html#install-instructions"
    ) from None
