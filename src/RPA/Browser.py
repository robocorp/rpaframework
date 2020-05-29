import importlib
import logging
import os
import platform
import re
import stat
import subprocess

# import selenium
import tempfile
import time
from typing import Any
from pathlib import Path

from SeleniumLibrary import SeleniumLibrary
from SeleniumLibrary.base import keyword
from selenium.common.exceptions import WebDriverException

from webdrivermanager import AVAILABLE_DRIVERS


class BrowserNotFoundError(Exception):
    """Raised when browser can't be initialized."""


class Browser(SeleniumLibrary):
    """RPA Framework library for Browser operations.

    Extends functionality of SeleniumLibrary.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    AUTOMATIC_BROWSER_SELECTION = "AUTO"

    AVAILABLE_OPTIONS = {
        "chrome": "ChromeOptions",
        # "firefox": "FirefoxOptions",
        # "safari": "WebKitGTKOptions",
        # "ie": "IeOptions",
    }

    CHROMEDRIVER_VERSIONS = {
        "81": "81.0.4044.69",
        "80": "80.0.3987.106",
        "79": "79.0.3945.36",
    }
    CHROME_VERSION_PATTERN = r"(\d+)(\.\d+\.\d+.\d+)"

    def __init__(self, *args, **kwargs) -> None:
        self.logger = logging.getLogger(__name__)
        SeleniumLibrary.__init__(self, *args, **kwargs)
        self.drivers = []

    def get_preferable_browser_order(self) -> list:
        """Returns list of RPA Framework preferred browsers by OS.

        :return: browser list
        """
        preferable_browser_order = ["Chrome"]
        if platform.system() == "Windows":
            preferable_browser_order.extend(["Firefox", "Edge", "IE", "Opera"])
        elif platform.system() == "Linux":
            preferable_browser_order.extend(["Firefox", "Opera"])
        elif platform.system() == "Darwin":
            preferable_browser_order.extend(["Safari", "Firefox", "Opera"])
        else:
            preferable_browser_order.extend(["Firefox"])
        return preferable_browser_order

    @keyword
    def open_available_browser(
        self,
        url: str,
        use_profile: bool = False,
        headless: bool = False,
        maximized: bool = False,
        browser_selection: Any = AUTOMATIC_BROWSER_SELECTION,
    ) -> int:
        """Open available browser

        Keywords opens the first available browser it can find from the
        system in preferred order or given browser (`browser_selection`)

        Steps:

        1. Get order of browsers
        2. Loop list of preferred of browsers

            a. Set webdriver options for browser
            b. Create webdriver using existing installaiton
            c. (If step b. failed) Download and install webdriver, try again
            d. (If step c. failed) Try starting webdriver in headless mode

        3. Open url

        If unable to open browser raises `BrowserNotFoundError`.

        Details on `Safari webdriver setup`_.

        :param url: address to open
        :param use_profile: set browser profile, defaults to False
        :param headless: run in headless mode, defaults to False
        :param maximized: run window maximized, defaults to False
        :param browser_selection: browser name, defaults to AUTOMATIC_BROWSER_SELECTION
        :return: index of the webdriver session

        .. _Safari webdriver setup:
            https://developer.apple.com/documentation/webkit/testing_with_webdriver_in_safari
        """
        index = -1
        preferable_browser_order = self.get_browser_order(browser_selection)
        selected_browser = None

        self.logger.info(
            "Open Available Browser preferable browser selection order is: %s",
            ", ".join(preferable_browser_order),
        )
        for browser in preferable_browser_order:
            options = self.set_driver_options(
                browser, use_profile=use_profile, headless=headless, maximized=maximized
            )

            # First try: Without any actions
            self.logger.info("Initializing webdriver with default options (method 1)")
            index = self.create_rpa_webdriver(browser, options)
            if index is not False:
                selected_browser = (browser, 1)
                break

            self.logger.info("Could not init webdriver using method 1. ")

            # Second try: Install driver (if there is a manager for driver)
            self.logger.info("Initializing webdriver with downloaded driver (method 2)")
            index = self.create_rpa_webdriver(browser, options, download=True)
            if index is not False:
                selected_browser = (browser, 2)
                break

            self.logger.info("Could not init webdriver using method 2.")

            # Third try: Headless
            if headless is False:
                options = self.set_driver_options(
                    browser,
                    use_profile=use_profile,
                    headless=True,
                    maximized=maximized,
                )
                self.logger.info("Initializing webdriver in headless mode (method 3)")
                index = self.create_rpa_webdriver(browser, options, download=True)
                if index is not False:
                    selected_browser = (browser, 3)
                    break

        if selected_browser:
            self.logger.info(
                "Selected browser (method: %s) is: %s, index: %d",
                selected_browser[1],
                selected_browser[0],
                index,
            )
            self.go_to(url)
            return index
        else:
            self.logger.error(
                "Unable to initialize webdriver (%s)",
                ", ".join(preferable_browser_order),
            )
            raise BrowserNotFoundError

    def create_rpa_webdriver(
        self, browser: str, options: dict, download: bool = False
    ) -> int:
        """Create webdriver instance for given browser.

        Driver will be downloaded if it does not exist when `download` is True.

        :param browser: name of the browser
        :param options: options for webdriver
        :param download: True if driver should be download, defaults to False
        :return: index of the webdriver session, False if webdriver was not initialized
        """
        executable = False
        self.logger.debug("Driver options for create_rpa_webdriver: %s", options)
        executable = self.webdriver_init(browser, download)
        try:
            browser = browser.lower().capitalize()
            if executable:
                index = self.create_webdriver(
                    browser, **options, executable_path=executable
                )
            else:
                index = self.create_webdriver(browser, **options)
            return index
        except WebDriverException as err:
            self.logger.info("Could not open driver: %s", err)
            return False
        return False

    def get_browser_order(self, browser_selection: Any) -> list:
        """Get list of browser that will be used for open browser
        keywords. Will be one or many.

        :param browser_selection: "AUTO" will be OS specfic list,
            or one named browser, eg. "Chrome"
        :return: list of browsers
        """
        if browser_selection == self.AUTOMATIC_BROWSER_SELECTION:
            preferable_browser_order = self.get_preferable_browser_order()
        else:
            preferable_browser_order = (
                browser_selection
                if isinstance(browser_selection, list)
                else [browser_selection]
            )
        return preferable_browser_order

    def detect_chrome_version(self) -> str:
        """Detect Chrome browser version (if possible) on different
        platforms using different commands for each platform.

        Returns corresponding chromedriver version if possible.

        Supported Chrome major versions are 81, 80 and 79.

        :return: chromedriver version number or None
        """
        # pylint: disable=line-too-long
        OS_CMDS = {
            "Windows": [
                r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version',  # noqa
                r'reg query "HKEY_CURRENT_USER\Software\Chromium\BLBeacon" /v version',  # noqa
            ],
            "Linux": [
                "chromium --version",
                "chromium-browser --version",
                "google-chrome --version",
            ],
            "Darwin": [
                r"/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version",  # noqa
                r"/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version",  # noqa
                r"/Applications/Chromium.app/Contents/MacOS/Chromium --version",
            ],
        }
        CMDS = OS_CMDS[platform.system()]
        for cmd in CMDS:
            output = self._run_command_return_output(cmd)
            if output:
                version = re.search(self.CHROME_VERSION_PATTERN, output)
                if version:
                    major = version.group(1)
                    detailed = version.group(0)
                    self.logger.info("Detected Chrome major version is: %s", detailed)
                    return (
                        self.CHROMEDRIVER_VERSIONS[major]
                        if (major in self.CHROMEDRIVER_VERSIONS.keys())
                        else None
                    )
        return None

    def _run_command_return_output(self, command: str) -> str:
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
            )
            output, _ = process.communicate()
            return str(output).strip()
        except FileNotFoundError:
            self.logger.debug('Command "%s" not found', command)
            return None

    def get_installed_chromedriver_version(self, driver_executable_path: str) -> str:
        """Returns full version number for stable chromedriver.

        Stable version is defined internally based on the major version
        of the chromedriver.

        :param driver_executable_path: path to chromedriver
        :return: full version number for stable chromedriver or None
        """
        output = self._run_command_return_output(driver_executable_path)
        if output:
            version = re.search(self.CHROME_VERSION_PATTERN, output)
            if version:
                major = version.group(1)
                detailed = version.group(0)
                self.logger.info("Detected chromedriver major version is: %s", detailed)
                return (
                    self.CHROMEDRIVER_VERSIONS[major]
                    if (major in self.CHROMEDRIVER_VERSIONS.keys())
                    else None
                )
        return None

    def download_driver(
        self, dm_class: str, download_dir: str, version: str = None
    ) -> None:
        """ Download driver to given directory. By default downloads
        latest version for given webdriver type, but this can be
        overridden by giving ``version`` parameter.

        :param dm_class: driver manager class
        :param download_dir: directory to download driver into
        :param version: None by default (gets latest version)
        """
        self.logger.info("Downloading driver into: %s", str(download_dir))
        dm = dm_class(download_root=download_dir, link_path=download_dir)
        try:
            dm_result = None
            if version:
                dm_result = dm.download_and_install(version)
            else:
                dm_result = dm.download_and_install()
            if platform.system() == "Darwin" and dm_result:
                self._set_executable_permissions(dm_result[0])
            self.logger.debug(
                "%s downloaded into %s", dm.get_driver_filename(), str(download_dir)
            )
        except RuntimeError:
            pass

    def _set_executable_permissions(self, chromedriver_filepath: str = None) -> None:
        if chromedriver_filepath:
            self.logger.debug(
                "Set Executable Permissions for file: %s", chromedriver_filepath
            )
            st = os.stat(chromedriver_filepath)
            os.chmod(
                chromedriver_filepath,
                st.st_mode | stat.S_IXOTH | stat.S_IXGRP | stat.S_IEXEC,
            )

    def _set_driver_paths(self, dm_class: str, download: bool) -> Any:
        driver_executable_path = None

        dm = dm_class()
        driver_executable = dm.get_driver_filename()
        default_executable_path = Path(dm.link_path) / driver_executable

        tempdir = os.getenv("TEMPDIR") or tempfile.gettempdir()
        driver_tempdir = Path(tempdir) / "drivers"
        temp_executable_path = Path(driver_tempdir) / driver_executable

        if temp_executable_path.exists() or download:
            driver_executable_path = temp_executable_path
        else:
            driver_executable_path = default_executable_path
        return driver_executable_path, driver_tempdir

    def _check_chrome_and_driver_versions(
        self, driver_ex_path: str, browser_version: str
    ) -> bool:
        download_driver = False
        chromedriver_version = self.get_installed_chromedriver_version(
            str(driver_ex_path / " --version")
        )
        if chromedriver_version is False:
            self.logger.info("Could not detect chromedriver version.")
            download_driver = True
        elif chromedriver_version != browser_version:
            self.logger.info("Chrome and chromedriver versions are different.")
            download_driver = True
        return download_driver

    def webdriver_init(self, browser: str, download: bool = False) -> str:
        """Webdriver initialization with default driver
        paths or with downloaded drivers.

        :param browser: use drivers for this browser
        :param download: if True drivers are downloaded, not if False
        :return: path to driver or `None`
        """
        browser = browser.lower()
        self.logger.debug(
            "Webdriver initialization for browser: '%s'. Download set to: %s",
            browser,
            download,
        )
        if browser == "chrome":
            browser_version = self.detect_chrome_version()
        else:
            browser_version = None
        dm_class = (
            AVAILABLE_DRIVERS[browser] if browser in AVAILABLE_DRIVERS.keys() else None
        )
        if dm_class:
            self.logger.debug("Driver manager class: %s", dm_class)
            driver_ex_path, driver_tempdir = self._set_driver_paths(dm_class, download)
            if download:
                if not driver_ex_path.exists():
                    self.download_driver(dm_class, driver_tempdir, browser_version)
                else:
                    if browser == "chrome":
                        force_download = self._check_chrome_and_driver_versions(
                            driver_ex_path, browser_version
                        )
                        if force_download:
                            self.download_driver(
                                dm_class, driver_tempdir, browser_version
                            )
                    else:
                        self.logger.info(
                            "Driver download skipped, because it already "
                            "existed at %s",
                            driver_ex_path,
                        )
            else:
                self.logger.info("Using already existing driver at: %s", driver_ex_path)

            return r"%s" % str(driver_ex_path)
        else:
            return None

    def set_driver_options(
        self,
        browser: str,
        use_profile: bool = False,
        headless: bool = False,
        maximized: bool = False,
    ) -> dict:
        """Set options for given browser

        Supported at the moment:
            - ChromeOptions
            - FirefoxOptions
            - IeOptions

        :param browser
        :param use_profile: if browser user profile is used, defaults to False
        :param headless: if headless mode should be set, defaults to False
        :param maximized: if browser should be run maximized, defaults to False
        :return: driver options or empty dictionary
        """
        browser_options = None
        driver_options = {}
        browser = browser.lower()
        browser_option_class = (
            self.AVAILABLE_OPTIONS[browser]
            if browser in self.AVAILABLE_OPTIONS.keys()
            else None
        )
        if browser_option_class is None:
            return driver_options

        if browser in self.AVAILABLE_OPTIONS.keys():
            module = importlib.import_module("selenium.webdriver")
            class_ = getattr(module, browser_option_class)
            browser_options = class_()

        if headless:
            self.set_headless_options(browser, browser_options)

        if browser_options and maximized:
            self.logger.info("Setting maximized mode")
            browser_options.add_argument("--start-maximized")

        if browser_options and use_profile:
            self.set_user_profile(browser_options)

        if browser_options and browser != "chrome":
            driver_options["options"] = browser_options
        elif browser_options and browser == "chrome":
            self.set_default_options(browser_options)
            prefs = {"safebrowsing.enabled": "true"}
            browser_options.add_experimental_option(
                "excludeSwitches", ["enable-logging"]
            )
            browser_options.add_experimental_option("prefs", prefs)
            if self.logger.isEnabledFor(logging.DEBUG):
                driver_options["service_log_path"] = "chromedriver.log"
                driver_options["service_args"] = ["--verbose"]
            driver_options["chrome_options"] = browser_options

        return driver_options

    @keyword
    def open_chrome_browser(
        self,
        url: str,
        use_profile: bool = False,
        headless: bool = False,
        maximized: bool = False,
    ) -> int:
        """Open Chrome browser.

        :param url: address to open
        :param use_profile: if browser user profile is used, defaults to False
        :param headless: if headless mode should be set, defaults to False
        :param maximized: if browser should be run maximized, defaults to False
        """
        # webdrivermanager
        # https://stackoverflow.com/questions/41084124/chrome-options-in-robot-framework
        index = self.open_available_browser(
            url,
            use_profile=use_profile,
            headless=headless,
            maximized=maximized,
            browser_selection="Chrome",
        )
        return index

    def set_default_options(self, options: dict) -> None:
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--remote-debugging-port=12922")
        options.add_argument("--no-sandbox")

    def set_headless_options(self, browser: str, options: dict) -> None:
        """Set headless mode if possible for the browser

        :param browser: string name of the browser
        :param options: browser options class instance
        """
        if browser.lower() == "safari":
            self.logger.info(
                "Safari does not support headless mode. "
                "https://github.com/SeleniumHQ/selenium/issues/5985"
            )
            return
        if options:
            self.logger.info("Setting headless mode")
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-dev-shm-usage")

    def set_user_profile(self, options: dict) -> None:
        user_profile_dir = os.getenv("RPA_CHROME_USER_PROFILE_DIR", None)
        if user_profile_dir is None:
            self.logger.warning(
                'environment variable "RPA_CHROME_USER_PROFILE_DIR" '
                "has not been set, cannot set user profile"
            )
            return
        options.add_argument(f"--user-data-dir='{user_profile_dir}'")
        options.add_argument("--enable-local-sync-backend")
        options.add_argument(f"--local-sync-backend-dir='{user_profile_dir}'")

    @keyword
    def open_headless_chrome_browser(self, url: str) -> int:
        """Open Chrome browser in headless mode

        :param url: address to open
        """
        index = self.open_chrome_browser(url, headless=True)
        return index

    @keyword
    def screenshot(
        self,
        page: bool = True,
        locator: str = None,
        filename_prefix: str = "screenshot",
    ) -> None:
        """Capture page and/or element screenshot

        :param page: capture page screenshot, defaults to True
        :param locator: if defined take element screenshot, defaults to None
        :param filename_prefix: prefix for screenshot files, default to 'screenshot'
        """
        if page:
            filename = os.path.join(
                os.curdir, f"{filename_prefix}-{int(time.time())}-page.png"
            )
            capture_location = self.capture_page_screenshot(filename)
            self.logger.info(
                "Page screenshot saved to %s", Path(capture_location).resolve()
            )
        if locator:
            filename = os.path.join(
                os.curdir, f"{filename_prefix}-{int(time.time())}-element.png"
            )
            capture_location = self.capture_element_screenshot(
                locator, filename=filename
            )
            self.logger.info(
                "Element screenshot saved to %s", Path(capture_location).resolve()
            )

    @keyword
    def input_text_when_element_is_visible(self, locator: str, text: str) -> None:
        """Input text into locator after it has become visible

        :param locator: selector
        :param text: insert text to locator
        """
        self.wait_until_element_is_visible(locator)
        self.input_text(locator, text)

    @keyword
    def wait_and_click_button(self, locator: str) -> None:
        """Click button once it becomes visible

        :param locator: [description]
        """
        self.wait_until_element_is_visible(locator)
        self.click_button(locator)

    @property
    def location(self) -> str:
        """Return browser location

        :return: url of the page browser is in
        """
        return self.get_location()
