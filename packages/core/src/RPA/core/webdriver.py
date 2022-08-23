import logging
import os
import platform
import stat
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.manager import DriverManager
from webdriver_manager.core.utils import os_name as get_os_name
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager, IEDriverManager
from webdriver_manager.opera import OperaDriverManager

from RPA.core.robocorp import robocorp_home


LOGGER = logging.getLogger(__name__)

DRIVER_ROOT = robocorp_home() / "webdrivers"
DRIVER_PREFERENCE = {
    "Windows": ["Chrome", "Firefox", "Edge", "Ie", "Opera"],
    "Linux": ["Chrome", "Firefox", "Opera"],
    "Darwin": ["Chrome", "Safari", "Firefox", "Opera"],
    "default": ["Chrome", "Firefox"],
}
AVAILABLE_DRIVERS = {
    # Driver names taken from `webdrivermanager` and adapted to `webdriver_manager`.
    "chrome": ChromeDriverManager,
    "firefox": GeckoDriverManager,
    "gecko": GeckoDriverManager,
    "mozilla": GeckoDriverManager,
    "opera": OperaDriverManager,
    # NOTE: There's no specific `EdgeDriverManager` with this manager and the very same
    #  `EdgeService` works for both.
    "edge": EdgeChromiumDriverManager,
    "chromiumedge": EdgeChromiumDriverManager,
    "ie": IEDriverManager,
}


def start(browser: str, service: Optional[Service] = None, **options):
    """Start a webdriver with the given options."""
    browser = browser.strip()
    webdriver_factory = getattr(webdriver, browser, None)
    if not webdriver_factory:
        raise ValueError(f"Unsupported browser: {browser}")

    # NOTE: Is recommended to pass a `service` rather than deprecated `options`.
    driver = webdriver_factory(service=service, **options)
    return driver


def _to_manager(browser: str, root: Path = DRIVER_ROOT) -> DriverManager:
    browser = browser.strip()
    manager_factory = AVAILABLE_DRIVERS.get(browser.lower())
    if not manager_factory:
        raise ValueError(f"Unsupported browser: {browser}")

    manager = manager_factory(path=str(root))
    return manager


def _set_executable(path: str) -> None:
    st = os.stat(path)
    os.chmod(
        path,
        st.st_mode | stat.S_IXOTH | stat.S_IXGRP | stat.S_IEXEC,
    )


def download(browser: str, root: Path = DRIVER_ROOT) -> Optional[Path]:
    """Download a webdriver binary for the given browser and return the path to it."""
    manager = _to_manager(browser, root)
    driver = manager.driver
    os_type = getattr(driver, "os_type", driver.get_os_type())
    if get_os_name() not in os_type:
        return None  # incompatible driver download attempt

    path: str = manager.install()
    if platform.system() != "Windows":
        _set_executable(path)
    LOGGER.debug("Downloaded webdriver to: %s", path)
    return path
