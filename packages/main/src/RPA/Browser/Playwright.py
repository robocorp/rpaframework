import functools
from typing import Union

try:
    from Browser import Browser
except (ModuleNotFoundError, ImportError) as exc:
    raise ModuleNotFoundError(
        "Please install the `robotframework-browser` package by following these "
        "instructions: https://rpaframework.org/libraries/browser_playwright/"
        "index.html#install-instructions"
    ) from exc

from Browser.keywords import PlaywrightState

from RPA.Browser.common import AUTO, get_headless_state


class RobocorpPlaywrightState(PlaywrightState):
    @functools.wraps(PlaywrightState.open_browser)
    def open_browser(self, *args, headless: Union[bool, str] = AUTO, **kwargs):
        headless = get_headless_state(headless)
        super().open_browser(*args, headless=headless, **kwargs)


class Playwright(Browser):
    @functools.wraps(Browser.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._playwright_state = RobocorpPlaywrightState(self)
        library_components = [self._playwright_state]
        self.add_library_components(library_components)
