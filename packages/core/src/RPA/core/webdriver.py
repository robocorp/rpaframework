import contextlib
import functools
import logging
import os
import platform
import requests
import stat
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

from packaging import version as version_parser
from selenium import webdriver
from selenium.webdriver.common.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager as _ChromeDriverManager
from webdriver_manager.core.download_manager import DownloadManager
from webdriver_manager.core.driver_cache import (
    DriverCacheManager as _DriverCacheManager,
)
from webdriver_manager.core.file_manager import FileManager
from webdriver_manager.core.logger import log
from webdriver_manager.core.manager import DriverManager
from webdriver_manager.core.os_manager import (
    ChromeType,
    OSType,
    OperationSystemManager as _OperationSystemManager,
    PATTERN as _PATTERN,
)
from webdriver_manager.core.utils import (
    linux_browser_apps_to_cmd,
    read_version_from_cmd,
    windows_browser_apps_to_cmd,
)
from webdriver_manager.drivers.chrome import ChromeDriver as _ChromeDriver
from webdriver_manager.drivers.ie import IEDriver as _IEDriver
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import (
    EdgeChromiumDriverManager,
    IEDriverManager as _IEDriverManager,
)
from webdriver_manager.opera import OperaDriverManager

from RPA.core.robocorp import robocorp_home


class UnknownDriverError(Exception):
    """Exception raised for unknown drivers."""

class BrowserType:
    """Constants for the browser types. (expands the internal one)"""

    MSIE = "msie"
    FIREFOX = "firefox"


PATTERN = _PATTERN.copy()
PATTERN[BrowserType.MSIE] = r"\d+\.\d+\.\d+\.\d+"


class OperationSystemManager(_OperationSystemManager):
    """Custom manager for browser version retrieval which works with explicit paths."""

    @staticmethod
    def _get_browser_version(browser_type: str, paths: List[str]) -> Optional[str]:
        common_cmds = {
            OSType.LINUX: linux_browser_apps_to_cmd(*paths),
            OSType.MAC: f"{paths[0]} --version",
            OSType.WIN: windows_browser_apps_to_cmd(
                *(
                    f"(Get-Item -Path '{path}').VersionInfo.FileVersion"
                    for path in paths
                )
            ),
        }
        cmd_mapping = {
            ChromeType.GOOGLE: common_cmds,
            ChromeType.CHROMIUM: common_cmds,
            ChromeType.MSEDGE: common_cmds,
            BrowserType.FIREFOX: common_cmds,
            BrowserType.MSIE: common_cmds,
        }
        try:
            cmd_mapping = cmd_mapping[browser_type][
                OperationSystemManager.get_os_name()
            ]
            pattern = PATTERN[browser_type]
            version = read_version_from_cmd(cmd_mapping, pattern)
            return version
        # pylint: disable=broad-except
        except Exception as exc:
            LOGGER.warning(
                "Can't read %r browser version due to: %s", browser_type, exc
            )
            return None

    def get_browser_version_from_os(
        self, browser_type: Optional[str] = None
    ) -> Optional[str]:
        if browser_type != BrowserType.MSIE:
            return super().get_browser_version_from_os(browser_type)

        # Add support for IE version retrieval from OS.
        # FIXME(cmin764, 15 Sep 2023): Remove this after fixing the issue below:
        #  https://github.com/SergeyPirogov/webdriver_manager/issues/625
        program_files = os.getenv("PROGRAMFILES", r"C:\Program Files")
        paths = [
            rf"{program_files}\Internet Explorer\iexplore.exe",
            rf"{program_files} (x86)\Internet Explorer\iexplore.exe",
        ]
        return self._get_browser_version(BrowserType.MSIE, paths=paths)

    def get_browser_version(
        self, browser_type: str, path: Optional[str] = None
    ) -> Optional[str]:
        if path:
            return self._get_browser_version(browser_type, paths=[path])

        return self.get_browser_version_from_os(browser_type)


class DriverCacheManager(_DriverCacheManager):
    """Fixes caching when retrieving an existing already downloaded webdriver."""

    def __init__(self, *args, file_manager: Optional[FileManager] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._os_system_manager = OperationSystemManager()
        self._file_manager = file_manager or FileManager(self._os_system_manager)


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
        if determined_browser_version:
            parsed_version = version_parser.parse(determined_browser_version)
            non_solveable = parsed_version.major >= 115
            solve_needed = resolve_version or len(parsed_version.release) < 4
            if non_solveable or not solve_needed:
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
        parse_version = lambda ver: version_parser.parse(ver).release  # noqa: E731, pylint: disable=unnecessary-lambda-assignment
        parse_floating_version = lambda ver: parse_version(ver)[:3]  # noqa: E731, pylint: disable=unnecessary-lambda-assignment
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

        raise UnknownDriverError(f"No such driver version {browser_version} for {platform}")

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


class IEDriver(_IEDriver):
    """Custom IE driver class that handles discontinued IE driver gracefully."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow fallback version to be configured via environment variable for future-proofing
        # Default to 3.141.59 which is the latest IEDriverServer version that includes the driver
        # (newer Selenium versions don't include IEDriverServer as IE is discontinued)
        self._fallback_version = os.getenv("RPA_IE_DRIVER_VERSION", "3.141.59")

    def _is_internal_source(self, url: Optional[str]) -> bool:
        """Check if URL is from internal Robocorp source."""
        if not url:
            return False
        parsed = urlparse(url)
        host = parsed.hostname or ""
        # Check if host is exactly robocorp.com or downloads.robocorp.com, or a subdomain of robocorp.com
        return (
            host == "robocorp.com"
            or host == "downloads.robocorp.com"
            or host.endswith(".robocorp.com")
        )

    def _is_valid_version(self, version: str) -> bool:
        """Check if version string looks like a valid version."""
        if not version:
            return False
        version_lower = version.lower()
        if version_lower == "nightly" or version_lower.startswith("nightly"):
            return False
        # Check if it looks like a version (contains digits and dots/dashes)
        has_digits = any(char.isdigit() for char in version)
        has_separators = "." in version or "-" in version
        is_numeric = version.replace(".", "").replace("-", "").isdigit()
        return has_digits and (has_separators or is_numeric)

    def _normalize_version(self, tag: str) -> str:
        """Normalize version tag by removing common prefixes."""
        return tag.replace("selenium-", "").replace("v", "").strip()

    def _verify_release_has_ie_driver(self, version: str) -> bool:
        """Verify that a release has IEDriverServer by checking assets."""
        ie_release_tag = getattr(self, "_ie_release_tag", None)
        if not ie_release_tag or "{0}" not in ie_release_tag:
            return False
        try:
            release_tag_url = ie_release_tag.format(version)
            release_resp = self._http_client.get(url=release_tag_url, headers=self.auth_header)
            if release_resp.status_code == 200:
                release_assets = release_resp.json().get("assets", [])
                return any("IEDriverServer" in asset.get("name", "") for asset in release_assets)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        return False

    def _process_release_list(self, releases_data: List[Dict]) -> Optional[str]:
        """Process a list of releases and return the first valid version."""
        for release in releases_data:
            if not isinstance(release, dict):
                continue
            tag = release.get("tag_name") or release.get("version") or release.get("name", "")
            version = self._normalize_version(tag)
            if not self._is_valid_version(version):
                continue
            # Verify this release actually has IEDriverServer by checking assets
            if self._verify_release_has_ie_driver(version):
                log(f"Found available IE driver version from internal source: {version}")
                return version
            # If we can't verify, assume it might have it and return it
            log(f"Found potential IE driver version from internal source: {version} (could not verify assets)")
            return version
        return None

    def _process_single_release(self, releases_data: Dict) -> Optional[str]:
        """Process a single release object and return version if valid."""
        tag = releases_data.get("tag_name") or releases_data.get("version") or releases_data.get("name", "")
        version = self._normalize_version(tag)
        if self._is_valid_version(version):
            log(f"Found available IE driver version from internal source: {version}")
            return version
        return None

    def _query_internal_source_versions(self, latest_release_url: str) -> Optional[str]:
        """Query internal source for available IE driver versions."""
        try:
            log(f"Querying internal source for available IE driver versions: {latest_release_url}")
            resp = self._http_client.get(url=latest_release_url, headers=self.auth_header)
            if resp.status_code != 200:
                return None
            releases_data = resp.json()
            if isinstance(releases_data, list) and releases_data:
                return self._process_release_list(releases_data)
            if isinstance(releases_data, dict):
                return self._process_single_release(releases_data)
        except Exception as query_exc:  # pylint: disable=broad-exception-caught
            log(f"Failed to query internal source for versions: {query_exc}. Using fallback version.")
        return None

    def _handle_stop_iteration(self) -> str:
        """Handle StopIteration exception by querying internal sources or using fallback."""
        latest_release_url = getattr(self, "_latest_release_url", None)
        if self._is_internal_source(latest_release_url):
            version = self._query_internal_source_versions(latest_release_url)
            if version:
                return version
        # Fall back to configured version
        log(
            f"IEDriverServer release not found in Selenium GitHub releases. "
            f"Falling back to version {self._fallback_version}. "
            "Note: Internet Explorer is discontinued and not supported anymore. "
            "You can override the fallback version by setting RPA_IE_DRIVER_VERSION."
        )
        return self._fallback_version

    def _handle_common_errors(self, exc: Exception) -> str:
        """Handle common errors from webdriver-manager."""
        log(
            f"Error while getting IE driver version ({type(exc).__name__}): {exc}. "
            f"Attempting fallback version {self._fallback_version}."
        )
        return self._fallback_version

    def _handle_unexpected_error(self, exc: Exception) -> str:
        """Handle unexpected errors from webdriver-manager."""
        log(
            f"Unexpected error while getting IE driver version: {exc}. "
            f"Attempting fallback version {self._fallback_version}."
        )
        return self._fallback_version

    def get_latest_release_version(self) -> str:
        """Return the latest IEDriverServer release version with fallback handling.

        This method wraps the original webdriver-manager method to handle cases where
        the IE driver is no longer available in Selenium's GitHub releases. It tries
        the original method first, and if it fails with StopIteration (indicating no
        matching release was found), it falls back to a known working version.

        The fallback version can be configured via the RPA_IE_DRIVER_VERSION environment
        variable if the default version becomes unavailable in the future.

        Returns:
            The latest available IEDriverServer version string.
        """
        try:
            # Try the original method first - this works if using internal sources
            # or if webdriver-manager is updated to handle IE properly
            return super().get_latest_release_version()
        except StopIteration:
            return self._handle_stop_iteration()
        except (ValueError, KeyError, ConnectionError, TimeoutError) as exc:
            return self._handle_common_errors(exc)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return self._handle_unexpected_error(exc)

    def _query_internal_release_api(self, version: str, os_type: str) -> Optional[str]:
        """Query internal release API for download URL."""
        ie_release_tag = getattr(self, "_ie_release_tag", None)
        if not ie_release_tag or "{0}" not in ie_release_tag:
            return None
        try:
            release_url = ie_release_tag.format(version)
            log(f"Querying internal source release URL: {release_url}")
            resp = self._http_client.get(url=release_url, headers=self.auth_header)
            if resp.status_code != 200:
                return None
            release_data = resp.json()
            assets = release_data.get("assets", [])
            driver_name = getattr(self, "_name", "IEDriverServer")
            name_prefix = f"{driver_name}_{os_type}_{version}"
            for asset in assets:
                asset_name = asset.get("name", "")
                if asset_name.startswith(name_prefix):
                    download_url = asset.get("browser_download_url") or asset.get("url")
                    if download_url:
                        log(f"Found internal source download URL: {download_url}")
                        return download_url
        except Exception as query_exc:  # pylint: disable=broad-exception-caught
            log(f"Failed to query internal source API: {query_exc}. Trying direct URL construction.")
        return None

    def _construct_internal_download_url(self, version: str, os_type: str) -> Optional[str]:
        """Construct download URL for internal source using direct format."""
        base_url = getattr(self, "_url", None)
        if not base_url:
            return None
        driver_name = getattr(self, "_name", "IEDriverServer")
        # Internal source URL format: /ie/download/selenium-{version}/IEDriverServer_{os_type}_{version}.zip
        download_url = f"{base_url.rstrip('/')}/selenium-{version}/{driver_name}_{os_type}_{version}.zip"
        log(f"Using constructed internal source URL: {download_url}")
        return download_url

    def _get_internal_source_url(self, os_type: str) -> Optional[str]:
        """Get download URL from internal source."""
        version = self.get_driver_version_to_download()
        # Try querying the release API first
        url = self._query_internal_release_api(version, os_type)
        if url:
            return url
        # Fallback to direct URL construction
        return self._construct_internal_download_url(version, os_type)

    def get_driver_download_url(self, os_type: str) -> str:
        """Get the download URL for the IE driver with fallback handling.

        This method wraps the original to handle cases where the driver asset is not
        found in GitHub releases. It checks if using internal sources first, and if so,
        queries the internal API. Otherwise, it tries the original GitHub API method.

        Args:
            os_type: The operating system type (e.g., 'Win32').

        Returns:
            The download URL for the IE driver.

        Raises:
            UnknownDriverError: If the driver cannot be found and no fallback is available.
        """
        # Check if we're using internal sources first
        latest_release_url = getattr(self, "_latest_release_url", None)
        if self._is_internal_source(latest_release_url):
            url = self._get_internal_source_url(os_type)
            if url:
                return url

        # Try the original GitHub API method (for external sources)
        try:
            return super().get_driver_download_url(os_type)
        except (IndexError, StopIteration) as exc:
            # Driver asset not found in GitHub releases (external sources only)
            version = self.get_driver_version_to_download()
            log(
                f"IEDriverServer asset not found for version {version} and OS {os_type}. "
                "This is expected as Internet Explorer is discontinued."
            )
            raise UnknownDriverError(
                f"IEDriverServer version {version} is not available for {os_type}. "
                "Internet Explorer is discontinued and driver downloads from Selenium "
                "GitHub releases are no longer available. "
                "Consider using Microsoft Edge in IE mode or set RPA_EXTERNAL_WEBDRIVERS=false "
                "to use internal Robocorp sources if available."
            ) from exc
        except (ValueError, KeyError, ConnectionError, TimeoutError) as exc:
            # Handle common errors from webdriver-manager
            version = getattr(self, "_driver_version_to_download", "unknown")
            log(
                f"Error while getting IE driver download URL ({type(exc).__name__}): {exc}. "
                f"Version: {version}, OS: {os_type}."
            )
            raise UnknownDriverError(
                f"Failed to get IE driver download URL: {exc}"
            ) from exc
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Catch-all for any other unexpected errors
            version = getattr(self, "_driver_version_to_download", "unknown")
            log(
                f"Unexpected error while getting IE driver download URL: {exc}. "
                f"Version: {version}, OS: {os_type}."
            )
            raise UnknownDriverError(
                f"Unexpected error while getting IE driver download URL: {exc}"
            ) from exc


class IEDriverManager(_IEDriverManager):
    """Custom driver manager class for IE webdriver. (running Edge in IE mode)"""

    # Forcefully download the 32bit version of the webdriver no matter the architecture
    #  of the Windows system since it is known that the 64bit version is limited and
    #  also creates issues, like freezing browser automation with Selenium sometimes.
    # https://www.selenium.dev/documentation/webdriver/browsers/internet_explorer/
    FORCE_32BIT = not os.getenv("RPA_ALLOW_64BIT_IE")

    def __init__(self, *args, **kwargs):
        # Extract parameters that might be needed for IEDriver before passing to parent
        os_system_manager = kwargs.get("os_system_manager")
        ie_release_tag = kwargs.get("ie_release_tag")
        super().__init__(*args, **kwargs)
        # Replace the upstream webdriver helper class with our custom IE driver
        # that handles discontinued IE driver gracefully
        # Copy attributes from the existing driver created by parent class
        original_driver = self.driver
        self.driver = IEDriver(
            name=getattr(original_driver, "_name", "IEDriverServer"),
            driver_version=getattr(original_driver, "_driver_version_to_download", None),
            url=getattr(original_driver, "_url", None),
            latest_release_url=getattr(original_driver, "_latest_release_url", None),
            ie_release_tag=ie_release_tag or getattr(original_driver, "_ie_release_tag", None),
            http_client=self.http_client,
            os_system_manager=os_system_manager or getattr(original_driver, "_os_system_manager", None),
        )

    def get_os_type(self) -> str:
        return "Win32" if self.FORCE_32BIT else super().get_os_type()

    def _get_driver_binary_path(self, driver: IEDriver) -> str:
        """Resolve the webdriver binary path, handling 404 errors for internal sources."""
        try:
            return super()._get_driver_binary_path(driver)
        except ValueError as exc:
            # Handle 404 errors when using internal sources - try alternative URL formats
            error_msg = str(exc)
            if "404" in error_msg or "no such driver by url" in error_msg.lower():
                # Check if we're using internal sources
                latest_release_url = getattr(driver, "_latest_release_url", None)
                if latest_release_url and ("robocorp.com" in latest_release_url or "downloads.robocorp.com" in latest_release_url):
                    version = driver.get_driver_version_to_download()
                    # If version is "nightly" or invalid, use fallback version
                    if not version or version.lower() == "nightly" or version.lower().startswith("nightly"):
                        # pylint: disable=protected-access
                        fallback_version = driver._fallback_version
                        log(f"Invalid version '{version}' detected, using fallback version {fallback_version}")
                        # Force the driver to use the fallback version
                        driver._driver_version_to_download = fallback_version
                        version = fallback_version

                    os_type = self.get_os_type()
                    base_url = getattr(driver, "_url", None)
                    if base_url:
                        driver_name = getattr(driver, "_name", "IEDriverServer")
                        # Try alternative URL formats
                        # Internal source format: /ie/download/selenium-{version}/IEDriverServer_{os_type}_{version}.zip
                        alternative_formats = [
                            f"{base_url.rstrip('/')}/selenium-{version}/{driver_name}_{os_type}_{version}.zip",
                            f"{base_url.rstrip('/')}/{version}/{driver_name}_{os_type}_{version}.zip",
                            f"{base_url.rstrip('/')}/{driver_name}_{os_type}_{version}.zip",  # Direct
                            f"{base_url.rstrip('/')}/{driver_name}_{os_type}.zip",  # Without version
                        ]
                        for alt_url in alternative_formats:
                            try:
                                log(f"Trying alternative URL format: {alt_url}")
                                file = self._download_manager.download_file(alt_url)
                                binary_path = self._cache_manager.save_file_to_cache(driver, file)
                                return binary_path
                            except (ValueError, Exception):  # pylint: disable=broad-exception-caught
                                continue  # Try next format
                    # If all formats fail, raise the original error with helpful message
                    raise UnknownDriverError(
                        f"IEDriverServer version {version} is not available for {os_type} from internal source. "
                        "Internet Explorer is discontinued. The driver may not be available in the internal source. "
                        "Consider using Microsoft Edge in IE mode instead."
                    ) from exc
            # Re-raise if not a 404 error or not using internal sources
            raise


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
    wdm_log_level = "WDM_LOG_LEVEL"
    old_wdm_log = os.getenv(wdm_log, "")
    old_wdm_log_level = os.getenv(wdm_log_level, "")
    try:
        os.environ[wdm_log] = str(logging.NOTSET)
        os.environ[wdm_log_level] = "0"
        yield
    finally:
        os.environ[wdm_log] = old_wdm_log
        os.environ[wdm_log_level] = old_wdm_log_level


def start(browser: str, service: Optional[Service] = None, **options) -> WebDriver:
    """Start a webdriver with the given options."""
    browser = browser.strip()
    webdriver_factory = getattr(webdriver, browser, None)
    if not webdriver_factory:
        raise ValueError(f"Unsupported Selenium browser: {browser}")

    # NOTE: It is recommended to pass a `service` rather than deprecated `options`.
    driver = webdriver_factory(service=service, **options)
    return driver


@functools.lru_cache(maxsize=1)
def _is_chromium() -> bool:
    """Detects if Chromium is used instead of Chrome no matter the platform."""
    is_browser = lambda browser_type: bool(  # noqa: E731, pylint: disable=unnecessary-lambda-assignment
        _OPS_MANAGER.get_browser_version_from_os(browser_type)
    )
    with suppress_logging():
        return not is_browser(ChromeType.GOOGLE) and is_browser(ChromeType.CHROMIUM)


def _get_browser_lower(browser: str) -> str:
    browser = browser.strip()
    browser_lower = browser.lower()
    if browser_lower not in AVAILABLE_DRIVERS:
        raise ValueError(
            f"Unsupported browser {browser!r} for webdriver download!"
            f" (choose from: {', '.join(SUPPORTED_BROWSERS.values())})"
        )

    return browser_lower


def _to_manager(browser: str, *, root: Path) -> DriverManager:
    browser_lower = _get_browser_lower(browser)
    manager_factory = AVAILABLE_DRIVERS[browser_lower]
    if manager_factory == ChromeDriverManager and _is_chromium():
        manager_factory = functools.partial(
            manager_factory, chrome_type=ChromeType.CHROMIUM
        )
    if not _USE_EXTERNAL_WEBDRIVERS:
        url_kwargs = _DRIVER_SOURCES.get(browser_lower)
        if url_kwargs and browser_lower != "edge":  # Skip Robocorp sources for Edge
            manager_factory = functools.partial(manager_factory, **url_kwargs)
        elif url_kwargs and browser_lower == "edge":
            LOGGER.warning("Skipping internal Edge webdriver source due to server issues")
        else:
            LOGGER.warning("Can't set an internal webdriver source for %r!", browser)

    cache_manager = DriverCacheManager(root_dir=str(root))
    manager = manager_factory(
        cache_manager=cache_manager, os_system_manager=_OPS_MANAGER
    )
    # Cache the method (works for all browsers including IE which now uses custom IEDriver class)
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
    # Workaround for MS Edge webdrivers
    if browser.lower() == "edge":
        # Patch HTTP requests to redirect azureedge.net to microsoft.com
        original_get = requests.get

        def patched_get(url, **kwargs):
            # Securely check if this is specifically the failing azureedge.net domain
            parsed = urlparse(url)
            if parsed.netloc == "msedgedriver.azureedge.net":
                # Replace only the hostname part to avoid security issues
                url = url.replace("://msedgedriver.azureedge.net", "://msedgedriver.microsoft.com")
            return original_get(url, **kwargs)

        requests.get = patched_get

        # Also try to suppress webdriver-manager logging
        logging.getLogger("webdriver_manager").setLevel(logging.ERROR)

    with suppress_logging():
        manager = _to_manager(browser, root=root)
        path: str = manager.install()

    # Restore original requests.get for Edge if it was patched
    if browser.lower() == "edge":
        try:
            requests.get = original_get
        except NameError:
            pass  # Variable wasn't set if not edge

    if platform.system() != "Windows":
        _set_executable(path)
    LOGGER.info("Downloaded webdriver to: %s", path)
    return path


def get_browser_version(browser: str, path: Optional[str] = None) -> Optional[str]:
    """Returns the detected browser version from OS in the absence of a given `path`."""
    browser_lower = _get_browser_lower(browser)
    chrome_type = ChromeType.CHROMIUM if _is_chromium() else ChromeType.GOOGLE
    browser_types = {
        # NOTE(cmin764, 12 Sep 2023): There's no upstream support on getting the
        #  automatically detected browser version from the OS for IE, Safari and Opera.
        #  But we introduce one here for IE only.
        "chrome": chrome_type,
        "firefox": BrowserType.FIREFOX,
        "gecko": BrowserType.FIREFOX,
        "mozilla": BrowserType.FIREFOX,
        "edge": ChromeType.MSEDGE,
        "chromiumedge": ChromeType.MSEDGE,
        "ie": BrowserType.MSIE,
    }
    browser_type = browser_types.get(browser_lower)
    if not browser_type:
        LOGGER.warning("Can't determine browser version for %r!", browser)
        return None

    return _OPS_MANAGER.get_browser_version(browser_type, path=path)
