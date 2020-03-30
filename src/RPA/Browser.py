import importlib
import logging
import os
import platform
import time
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

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        SeleniumLibrary.__init__(self, *args, **kwargs)
        self.drivers = []
        self.logger.debug(f"seleniumlibrary drivers {self.drivers}")

    def get_preferable_browser_order(self):
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
        url,
        use_profile=False,
        headless=False,
        maximized=False,
        browser_selection=AUTOMATIC_BROWSER_SELECTION,
    ):
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

        :param url: address to open
        :param use_profile: set browser profile, defaults to False
        :param headless: run in headless mode, defaults to False
        :param maximized: run window maximized, defaults to False
        :param browser_selection: browser name, defaults to AUTOMATIC_BROWSER_SELECTION
        """  # noqa: E501
        # https://developer.apple.com/documentation/webkit/testing_with_webdriver_in_safari
        index = -1
        preferable_browser_order = self.get_browser_order(browser_selection)
        selected_browser = None

        for browser in preferable_browser_order:
            self.logger.info(f"webdriver init check: {browser}")
            options = self.set_driver_options(
                browser, use_profile=use_profile, headless=headless, maximized=maximized
            )

            # First try: Without any actions
            index = self._create_rpa_webdriver(browser, options)
            if index is not False:
                selected_browser = (browser, 1)
                break

            # Second try: Install driver (if there is a manager for driver)
            index = self._create_rpa_webdriver(browser, options, download=True)
            if index is not False:
                selected_browser = (browser, 2)
                break

            # Third try: Headless
            if headless is False:
                options = self.set_driver_options(
                    browser,
                    use_profile=use_profile,
                    headless=True,
                    maximized=maximized,
                )
                index = self._create_rpa_webdriver(browser, options, download=True)
                if index is not False:
                    selected_browser = (browser, 3)
                    break

        if selected_browser:
            self.logger.debug(f"method {selected_browser[1]}")
            self.logger.debug(options)
            self.logger.info(
                f"Selected browser is: {selected_browser[0]}, index: {index}"
            )
            self.go_to(url)
        else:
            self.logger.error(
                f"Unable to initialize webdriver "
                f"({', '.join(preferable_browser_order)})"
            )
            raise BrowserNotFoundError

    def _create_rpa_webdriver(self, browser, driver_options, download=False):
        index = -1
        executable = False
        self.logger.debug(f"Got: {driver_options}")
        if download:
            executable = self.download_driver_if_exists(browser)
        try:
            if executable:
                index = self.create_webdriver(
                    browser, executable_path=executable, **driver_options
                )
            else:
                index = self.create_webdriver(browser, **driver_options)
            return index
        except WebDriverException as err:
            self.logger.debug(f"Could not open driver: {err}")
            return False

    def get_browser_order(self, browser_selection):
        """Get list of browser that will be used for open browser
        keywords. Will be one or many.

        :param browser_selection: "AUTO" will be OS specfic list,
            or one named browser, eg. "Chrome"
        :return: list of browsers
        """
        if browser_selection == self.AUTOMATIC_BROWSER_SELECTION:
            preferable_browser_order = self.get_preferable_browser_order()
        else:
            preferable_browser_order = [browser_selection]
        return preferable_browser_order

    def download_driver_if_exists(self, browser):
        """Download driver for a browser if that exists

        :param browser: download drivers for this browser
        :return: path to driver or `None`
        """
        driver_manager = None
        driver_manager_class = (
            AVAILABLE_DRIVERS[browser.lower()]
            if browser.lower() in AVAILABLE_DRIVERS.keys()
            else None
        )
        if driver_manager_class:
            self.logger.debug(f"Driver manager class: {driver_manager_class}")
            dir_to_use = Path().cwd() / "temp"
            driver_manager = driver_manager_class(
                download_root=dir_to_use, link_path=dir_to_use
            )
            driver_path = driver_manager.link_path
            driver_executable = driver_manager.get_driver_filename()
            driver_executable_path = Path(driver_path) / driver_executable

            if driver_executable_path.exists() is False:
                self.logger.info(f"Downloading and installing: {driver_executable}")
                driver_manager.download_and_install()
            else:
                self.logger.debug(f"Driver {driver_executable} already exists")

            self.logger.debug(
                f"Chromedriver installed into: {str(driver_executable_path)}"
            )
            return r"%s" % str(driver_executable_path)
        else:
            return None

    def set_driver_options(
        self, browser, use_profile=False, headless=False, maximized=False,
    ):
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
        browser_option_class = (
            self.AVAILABLE_OPTIONS[browser.lower()]
            if browser.lower() in self.AVAILABLE_OPTIONS.keys()
            else None
        )
        if browser_option_class is None:
            return driver_options

        if browser.lower() in self.AVAILABLE_OPTIONS.keys():
            module = importlib.import_module(f"selenium.webdriver")
            class_ = getattr(module, browser_option_class)
            browser_options = class_()
            self.logger.debug(type(browser_options))
            # self.set_default_options(browser_options)

        if browser_options and browser.lower() == "chrome":
            self.set_default_options(browser_options)
            prefs = {"safebrowsing.enabled": "true", "enable-logging": "true"}
            browser_options.add_experimental_option("prefs", prefs)
            if self.logger.isEnabledFor(logging.DEBUG):
                driver_options["service_log_path"] = "chromedriver.log"
                driver_options["service_args"] = ["--verbose"]

        if headless:
            self.set_headless_options(browser, browser_options)

        if browser_options and maximized:
            self.logger.info("Setting maximized mode")
            browser_options.add_argument("--start-maximized")

        if browser_options and use_profile:
            self.set_user_profile(browser_options)

        if browser_options:
            driver_options["options"] = browser_options

        return driver_options

    @keyword
    def open_chrome_browser(
        self, url, use_profile=False, headless=False, maximized=False
    ):
        """Open Chrome browser.

        :param url: address to open
        :param use_profile: [description], defaults to True
        :param headless: [description], defaults to False
        """
        # webdrivermanager
        # https://stackoverflow.com/questions/41084124/chrome-options-in-robot-framework
        self.open_available_browser(
            url,
            use_profile=use_profile,
            headless=headless,
            maximized=maximized,
            browser_selection="Chrome",
        )

    def set_default_options(self, options):
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--remote-debugging-port=12922")
        options.add_argument("--no-sandbox")

    def set_headless_options(self, browser, options):
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

    def set_user_profile(self, options):
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
    def open_headless_chrome_browser(self, url):
        """Open Chrome browser in headless mode

        :param url: address to open
        """
        self.open_chrome_browser(url, headless=True)

    @keyword
    def screenshot(self, page=True, locator=None, filename_prefix="screenshot"):
        """Capture page and/or element screenshot

        :param page: capture page screenshot, defaults to True
        :param locator: if defined take element screenshot, defaults to None
        :param filename_prefix: prefix for screenshot files, default to 'screenshot'
        """
        if page:
            filename = os.path.join(
                os.curdir, f"{filename_prefix}-%s-page.png" % int(time.time())
            )
            capture_location = self.capture_page_screenshot(filename)
            self.logger.info(
                "Page screenshot saved to %s", Path(capture_location).resolve()
            )
        if locator:
            filename = os.path.join(
                os.curdir, f"{filename_prefix}-%s-element.png" % int(time.time())
            )
            capture_location = self.capture_element_screenshot(
                locator, filename=filename
            )
            self.logger.info(
                "Element screenshot saved to %s", Path(capture_location).resolve()
            )

    @keyword
    def input_text_when_element_is_visible(self, locator, text):
        """Input text into locator after it has become visible

        :param locator: selector
        :param text: insert text to locator
        """
        self.wait_until_element_is_visible(locator)
        self.input_text(locator, text)

    @keyword
    def wait_and_click_button(self, locator):
        """Click button once it becomes visible

        :param locator: [description]
        """
        self.wait_until_element_is_visible(locator)
        self.click_button(locator)

    @property
    def location(self):
        """Return browser location

        :return: url of the page browser is in
        """
        return self.get_location()
