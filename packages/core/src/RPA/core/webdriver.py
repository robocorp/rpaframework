import contextlib
import logging
import os
import platform
import stat
from pathlib import Path
from typing import Dict, List, Optional

import requests
from packaging import version
from requests import Response
from selenium import webdriver
from selenium.webdriver.common.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.download_manager import WDMDownloadManager
from webdriver_manager.core.http import WDMHttpClient
from webdriver_manager.core.manager import DriverManager
from webdriver_manager.core.utils import os_name as get_os_name
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager, IEDriverManager
from webdriver_manager.opera import OperaDriverManager

from RPA.core.robocorp import robocorp_home


LOGGER = logging.getLogger(__name__)

DRIVER_ROOT = robocorp_home() / "webdrivers"
AVAILABLE_DRIVERS = {
    # Driver names taken from `webdrivermanager` and adapted to `webdriver_manager`.
    "chrome": ChromeDriverManager,
    "firefox": GeckoDriverManager,
    "gecko": GeckoDriverManager,
    "mozilla": GeckoDriverManager,
    # NOTE: Selenium 4 dropped support for Opera.
    #  (https://github.com/SeleniumHQ/selenium/issues/10835)
    "opera": OperaDriverManager,
    # NOTE: In Selenium 4 `Edge` is the same with `ChromiumEdge`.
    "edge": EdgeChromiumDriverManager,
    "chromiumedge": EdgeChromiumDriverManager,
    # NOTE: IE is discontinued and not supported/encouraged anymore.
    "ie": IEDriverManager,
}
_DRIVER_PREFERENCE = {
    "Windows": ["Chrome", "Firefox", "ChromiumEdge"],
    "Linux": ["Chrome", "Firefox", "ChromiumEdge"],
    "Darwin": ["Chrome", "Firefox", "ChromiumEdge", "Safari"],
    "default": ["Chrome", "Firefox"],
}


def _get_browser_order_from_env() -> Optional[List[str]]:
    browsers: str = os.getenv("RPA_SELENIUM_BROWSER_ORDER", "")
    if browsers:
        return [browser.strip() for browser in browsers.split(sep=",")]

    return None  # meaning there's no env var to control the order


def get_browser_order() -> List[str]:
    """Get a list of preferred browsers based on the environment variable
    `RPA_SELENIUM_BROWSER_ORDER` if set.

    The OS dictates the order if no such env var is set.
    """
    browsers: Optional[List[str]] = _get_browser_order_from_env()
    if browsers:
        return browsers

    return _DRIVER_PREFERENCE.get(platform.system(), _DRIVER_PREFERENCE["default"])


def _set_driver_preference() -> Dict[str, List[str]]:
    pref = _DRIVER_PREFERENCE.copy()
    browsers: Optional[List[str]] = _get_browser_order_from_env()
    if browsers:
        for op_sys in pref:
            pref[op_sys] = browsers
    return pref


# FIXME(cmin764): This constant is deprecated and is planned for removal in the next
#  major upgrade. (use `get_browser_order` function instead)
DRIVER_PREFERENCE = _set_driver_preference()


class Downloader(WDMHttpClient):

    """Custom downloader which disables download progress reporting."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver = None

    def _fix_mac_arm_url(self, url) -> str:
        if "m1" not in self.driver.get_os_type():
            return url

        # FIXME(cmin764): Remove this when the issue below gets closed
        #  https://github.com/SergeyPirogov/webdriver_manager/issues/446
        browser_version = self.driver.get_version()
        if version.parse(browser_version) >= version.parse("106.0.5249.61"):
            url = url.replace("mac64_m1", "mac_arm64")
        return url

    def get(self, url, **kwargs) -> Response:
        url = self._fix_mac_arm_url(url)
        resp = requests.get(url=url, verify=self._ssl_verify, stream=True, **kwargs)
        self.validate_response(resp)
        return resp


@contextlib.contextmanager
def suppress_logging():
    """Suppress webdriver-manager logging."""
    wdm_log = "WDM_LOG"
    original_value = os.getenv(wdm_log, "")
    try:
        os.environ[wdm_log] = str(logging.NOTSET)
        yield
    finally:
        os.environ[wdm_log] = original_value


def start(browser: str, service: Optional[Service] = None, **options) -> WebDriver:
    """Start a webdriver with the given options."""
    browser = browser.strip()
    webdriver_factory = getattr(webdriver, browser, None)
    if not webdriver_factory:
        raise ValueError(f"Unsupported browser: {browser}")

    # NOTE: It is recommended to pass a `service` rather than deprecated `options`.
    driver = webdriver_factory(service=service, **options)
    return driver


def _to_manager(browser: str, root: Path = DRIVER_ROOT) -> DriverManager:
    browser = browser.strip()
    manager_factory = AVAILABLE_DRIVERS.get(browser.lower())
    if not manager_factory:
        raise ValueError(
            f"Unsupported browser {browser!r}! (choose from: {list(AVAILABLE_DRIVERS)})"
        )

    downloader = Downloader()
    download_manager = WDMDownloadManager(downloader)
    manager = manager_factory(path=str(root), download_manager=download_manager)
    downloader.driver = manager.driver
    return manager


def _set_executable(path: str) -> None:
    st = os.stat(path)
    os.chmod(
        path,
        st.st_mode | stat.S_IXOTH | stat.S_IXGRP | stat.S_IEXEC,
    )


def download(browser: str, root: Path = DRIVER_ROOT) -> Optional[str]:
    """Download a webdriver binary for the given browser and return the path to it."""
    manager = _to_manager(browser, root)
    driver = manager.driver
    resolved_os = getattr(driver, "os_type", driver.get_os_type())
    os_name = get_os_name()
    if os_name.lower() not in resolved_os.lower():
        LOGGER.warning(
            "Attempting to download incompatible driver for OS %r on OS %r! Skip",
            resolved_os,
            os_name,
        )
        return None  # incompatible driver download attempt

    with suppress_logging():
        path: str = manager.install()
    if platform.system() != "Windows":
        _set_executable(path)
    LOGGER.debug("Downloaded webdriver to: %s", path)
    return path
