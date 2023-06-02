import functools

try:
    from Browser import Browser
except (ModuleNotFoundError, ImportError) as exc:
    raise ModuleNotFoundError(
        "Please install the `robotframework-browser` package by following these "
        "instructions: https://rpaframework.org/libraries/browser_playwright/"
        "index.html#install-instructions"
    ) from exc
from Browser.keywords import PlaywrightState

from RPA.Browser.common import auto_headless


class RobocorpPlaywrightState(PlaywrightState):
    """Automatic headless detection is supported when opening a new browser."""

    __doc__ = f"{PlaywrightState.__doc__}\n{__doc__}"

    open_browser = auto_headless(PlaywrightState.open_browser)
    new_browser = auto_headless(PlaywrightState.new_browser)
    new_persistent_context = auto_headless(PlaywrightState.new_persistent_context)


# pylint: disable=missing-class-docstring
class Playwright(Browser):
    """Automatic headless detection is supported when opening a new browser."""

    __doc__ = f"{Browser.__doc__}\n{__doc__}"

    @functools.wraps(Browser.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._playwright_state = RobocorpPlaywrightState(self)
        library_components = [self._playwright_state]
        self.add_library_components(library_components)
