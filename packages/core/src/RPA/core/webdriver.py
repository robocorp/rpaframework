import contextlib
import functools
import logging
import os
import platform
import stat
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

from packaging import version as version_parser
from selenium import webdriver
from selenium.webdriver.common.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager as _ChromeDriverManager
from webdriver_manager.core.download_manager import DownloadManager
from webdriver_manager.core.driver_cache import (
    DriverCacheManager as _DriverCacheManager,
)
from webdriver_manager.core.logger import log
from webdriver_manager.core.manager import DriverManager
from webdriver_manager.core.os_manager import ChromeType, OperationSystemManager
from webdriver_manager.drivers.chrome import ChromeDriver as _ChromeDriver
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import (
    EdgeChromiumDriverManager,
    IEDriverManager as _IEDriverManager,
)
from webdriver_manager.opera import OperaDriverManager

from RPA.core.robocorp import robocorp_home


# FIXME(cmin764; 6 Sep 2023): Remove this once the following issue is solved:
#  https://github.com/SergeyPirogov/webdriver_manager/issues/618
class DriverCacheManager(_DriverCacheManager):
    """Fixes caching when retrieving an existing already downloaded webdriver."""

    # pylint: disable=unused-private-member
    def __get_metadata_key(self, *args, **kwargs) -> str:
        # pylint: disable=super-with-arguments
        get_metadata_key = functools.partial(
            super(DriverCacheManager, self)._DriverCacheManager__get_metadata_key,
            *args,
            **kwargs,
        )
        return get_metadata_key() or get_metadata_key()


class ChromeDriver(_ChromeDriver):
    """Custom class which correctly obtains the chromedriver download URL."""

    def __init__(self, *args, versions_url: str, **kwargs):
        super().__init__(*args, **kwargs)

        self._versions_url = versions_url
        self._resolve_version = False

    def _get_resolved_version(self, determined_browser_version: Optional[str]) -> str:
        if determined_browser_version:
            # Resolution works with the first 3 atoms of the version, so exclude the
            #  4th one in case it exists.
            determined_browser_version = ".".join(
                determined_browser_version.split(".")[:3]
            )

        latest_release_url = (
            self._latest_release_url
            if (
                self._driver_version_to_download == "latest"
                or determined_browser_version is None
            )
            else f"{self._latest_release_url}_{determined_browser_version}"
        )
        resp = self._http_client.get(url=latest_release_url)
        return resp.text.rstrip()

    def get_driver_version_to_download(self) -> str:
        if self._resolve_version:
            return self.get_latest_release_version(resolve_version=True)

        return super().get_driver_version_to_download()

    # pylint: disable=arguments-differ
    def get_latest_release_version(self, resolve_version: bool = False) -> str:
        # This is activated for any chromedriver version.
        determined_browser_version = self.get_browser_version_from_os()
        if determined_browser_version and not resolve_version:
            parts = version_parser.parse(determined_browser_version).release
            if len(parts) == 4:
                # Got a fully downloadable version that MAY be available, but we are
                #  not sure until we don't try it.
                log(
                    f"Get {determined_browser_version} {self._name} version for"
                    f" {self._browser_type}"
                )
                return determined_browser_version

        log(
            f"Get LATEST {self._name} version for {self._browser_type} based on"
            f" {determined_browser_version}"
        )
        return self._get_resolved_version(determined_browser_version)

    def _resolve_modern_url(
        self, version: Dict, *, driver_platform: str
    ) -> Optional[str]:
        downloads = version["downloads"]["chromedriver"]
        for dld in downloads:
            # There's also a chance for platform mismatch.
            if dld["platform"] == driver_platform:
                # Ensure the caching key and driver path matches the exact resolved
                #  version.
                self._driver_version_to_download = version["version"]
                return dld["url"]

        return None

    # pylint: disable=arguments-renamed
    def get_url_for_version_and_platform(
        self, browser_version: str, driver_platform: str
    ) -> str:
        # This is activated for chromedriver 115 or higher only.
        parse_version = lambda ver: version_parser.parse(ver).release  # noqa: E731
        parse_floating_version = lambda ver: parse_version(ver)[:3]  # noqa: E731
        parsed_floating_version = parse_floating_version(browser_version)
        resolve_modern_url = functools.partial(
            self._resolve_modern_url, driver_platform=driver_platform
        )

        response = self._http_client.get(self._versions_url)
        data = response.json()
        versions = data["versions"]

        candidates = []
        for version in versions:
            if version["version"] == browser_version:  # exact match
                url = resolve_modern_url(version)
                if url:
                    return url
            elif parsed_floating_version == parse_floating_version(version["version"]):
                candidates.append(version)

        # No exact version found, let's return the latest from the matching candidates.
        if candidates:
            latest = max(
                candidates, key=lambda candidate: parse_version(candidate["version"])
            )
            url = resolve_modern_url(latest)
            if url:
                return url

        raise Exception(f"No such driver version {browser_version} for {platform}")

    # pylint: disable=arguments-differ
    def get_driver_download_url(self, os_type: str, resolve: bool = False) -> str:
        if resolve:
            # This time we want a resolved version based on the previously parsed
            #  non-existing one on the server.
            self._resolve_version = True  # force resolve
            self._driver_version_to_download = None  # ensures resolving

        return super().get_driver_download_url(os_type)


class ChromeDriverManager(_ChromeDriverManager):
    """Custom Chrome webdriver manager which correctly downloads the chromedriver."""

    def __init__(
        self,
        driver_version: Optional[str] = None,
        name: str = "chromedriver",
        url: str = "https://chromedriver.storage.googleapis.com",
        latest_release_url: str = (
            "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
        ),
        chrome_type: str = ChromeType.GOOGLE,
        download_manager: Optional[DownloadManager] = None,
        cache_manager: Optional[DriverCacheManager] = None,
        os_system_manager: Optional[OperationSystemManager] = None,
        versions_url: str = (
            "https://googlechromelabs.github.io/chrome-for-testing/"
            "known-good-versions-with-downloads.json"
        ),
    ):
        super().__init__(
            driver_version=driver_version,
            name=name,
            url=url,
            latest_release_url=latest_release_url,
            chrome_type=chrome_type,
            download_manager=download_manager,
            cache_manager=cache_manager,
            os_system_manager=os_system_manager,
        )

        # Replace the upstream webdriver helper class with our custom auto-resolving
        #  behavior.
        self.driver = ChromeDriver(
            name=name,
            driver_version=driver_version,
            url=url,
            latest_release_url=latest_release_url,
            chrome_type=chrome_type,
            http_client=self.http_client,
            os_system_manager=os_system_manager,
            versions_url=versions_url,
        )

    def _get_driver_binary_path(self, driver: ChromeDriver) -> str:
        """Resolve the webdriver version if is not available for download."""
        try:
            return super()._get_driver_binary_path(driver)
        except ValueError:  # parsed version isn't found, let's try to resolve it
            os_type = self.get_os_type()
            resolved_url = driver.get_driver_download_url(os_type, resolve=True)
            file = self._download_manager.download_file(resolved_url)
            binary_path = self._cache_manager.save_file_to_cache(driver, file)
            return binary_path


class IEDriverManager(_IEDriverManager):
    """Custom driver manager class for IE webdriver. (running Edge in IE mode)"""

    # Forcefully download the 32bit version of the webdriver no matter the architecture
    #  of the Windows system since it is known that the 64bit version is limited and
    #  also creates issues, like freezing browser automation with Selenium sometimes.
    # https://www.selenium.dev/documentation/webdriver/browsers/internet_explorer/
    FORCE_32BIT = not os.getenv("RPA_ALLOW_64BIT_IE")

    def get_os_type(self) -> str:
        return "Win32" if self.FORCE_32BIT else super().get_os_type()


LOGGER = logging.getLogger(__name__)

DRIVER_ROOT = robocorp_home() / "webdrivers"
DRIVER_ROOT.mkdir(parents=True, exist_ok=True)
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
# Control Room decides from where the webdrivers should be downloaded, but the user
#  can opt out from using our own trusted internal source and default to
#  `webdriver-manager`'s implicit locations.
_USE_EXTERNAL_WEBDRIVERS = bool(os.getenv("RPA_EXTERNAL_WEBDRIVERS"))
_SOURCE_BASE = os.getenv(
    "RC_WEBDRIVER_SOURCE", "https://downloads.robocorp.com/ext/webdrivers/"
)
_join_base = functools.partial(urljoin, _SOURCE_BASE)
_DRIVER_SOURCES = {
    "chrome": {
        "url": _join_base("chrome/v1"),
        "latest_release_url": _join_base("chrome/v1/LATEST_RELEASE"),
        "versions_url": _join_base("chrome/v2/known-good-versions-with-downloads.json"),
    },
    "firefox": {
        "url": _join_base("firefox/download"),
        "latest_release_url": _join_base("firefox/releases/latest"),
        "mozila_release_tag": _join_base("firefox/releases/tags/{0}"),
    },
    "edge": {
        "url": _join_base("edge"),
        "latest_release_url": _join_base("edge/LATEST_RELEASE"),
    },
    "ie": {
        "url": _join_base("ie/download"),
        "latest_release_url": _join_base("ie/releases"),
        "ie_release_tag": _join_base("ie/releases/tags/selenium-{0}"),
    },
}
_DRIVER_SOURCES["gecko"] = _DRIVER_SOURCES["mozilla"] = _DRIVER_SOURCES["firefox"]
_DRIVER_SOURCES["chromiumedge"] = _DRIVER_SOURCES["edge"]
# Available `WebDriver` classes in Selenium which also support automatic webdriver
#  download with `webdriver-manager`.
SUPPORTED_BROWSERS = dict(
    {name: name.capitalize() for name in AVAILABLE_DRIVERS},
    **{"chromiumedge": "ChromiumEdge"},
)
_DRIVER_PREFERENCE = {
    "Windows": ["Chrome", "Firefox", "Edge"],
    "Linux": ["Chrome", "Firefox", "Edge"],
    "Darwin": ["Chrome", "Firefox", "Edge", "Safari"],
    "default": ["Chrome", "Firefox"],
}

_OPS_MANAGER = OperationSystemManager()


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
        raise ValueError(f"Unsupported Selenium browser: {browser}")

    # NOTE: It is recommended to pass a `service` rather than deprecated `options`.
    driver = webdriver_factory(service=service, **options)
    return driver


def _is_chromium() -> bool:
    """Detects if Chromium is used instead of Chrome no matter the platform."""
    is_browser = lambda browser_type: bool(  # noqa: E731
        _OPS_MANAGER.get_browser_version_from_os(browser_type)
    )
    return not is_browser(ChromeType.GOOGLE) and is_browser(ChromeType.CHROMIUM)


def _to_manager(browser: str, *, root: Path) -> DriverManager:
    browser = browser.strip()
    browser_lower = browser.lower()
    manager_factory = AVAILABLE_DRIVERS.get(browser_lower)
    if not manager_factory:
        raise ValueError(
            f"Unsupported browser {browser!r} for webdriver download!"
            f" (choose from: {', '.join(SUPPORTED_BROWSERS.values())})"
        )

    if manager_factory == ChromeDriverManager and _is_chromium():
        manager_factory = functools.partial(
            manager_factory, chrome_type=ChromeType.CHROMIUM
        )
    if not _USE_EXTERNAL_WEBDRIVERS:
        url_kwargs = _DRIVER_SOURCES.get(browser_lower)
        if url_kwargs:
            manager_factory = functools.partial(manager_factory, **url_kwargs)
        else:
            LOGGER.warning("Can't set an internal webdriver source for %r!", browser)

    cache_manager = DriverCacheManager(root_dir=str(root))
    manager = manager_factory(cache_manager=cache_manager)
    driver = manager.driver
    cache = getattr(functools, "cache", functools.lru_cache(maxsize=None))
    driver.get_latest_release_version = cache(driver.get_latest_release_version)
    return manager


def _set_executable(path: str) -> None:
    st = os.stat(path)
    os.chmod(
        path,
        st.st_mode | stat.S_IXOTH | stat.S_IXGRP | stat.S_IEXEC,
    )


def download(browser: str, root: Path = DRIVER_ROOT) -> str:
    """Download a webdriver binary for the given browser and return the path to it."""
    manager = _to_manager(browser, root=root)
    with suppress_logging():
        path: str = manager.install()
    if platform.system() != "Windows":
        _set_executable(path)
    LOGGER.info("Downloaded webdriver to: %s", path)
    return path
