import importlib
import logging
import os
import platform
import time
from typing import Any
from pathlib import Path

from SeleniumLibrary import SeleniumLibrary
from SeleniumLibrary.base import keyword
from SeleniumLibrary.keywords import BrowserManagementKeywords
from selenium.common.exceptions import WebDriverException

from RPA.core import locators, webdriver


class BrowserNotFoundError(Exception):
    """Raised when browser can't be initialized."""


class Browser(SeleniumLibrary):
    """RPA Framework library for Browser operations.

    Extends functionality of SeleniumLibrary, for more information see
    https://robotframework.org/SeleniumLibrary/SeleniumLibrary.html
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    AUTOMATIC_BROWSER_SELECTION = "AUTO"

    AVAILABLE_OPTIONS = {
        "chrome": "ChromeOptions",
        "firefox": "FirefoxOptions",
        # "safari": "WebKitGTKOptions",
        # "ie": "IeOptions",
    }

    def __init__(self, *args, **kwargs) -> None:
        self.logger = logging.getLogger(__name__)

        self.using_testability = False
        if "use_testability" in args:
            self.using_testability = True
            args = filter(lambda x: x != "use_testability", args)
        if "plugins" in kwargs.keys() and "SeleniumTestability" in kwargs["plugins"]:
            # SeleniumTestability already included as plugin
            self.using_testability = True
        elif self.using_testability and "plugins" in kwargs.keys():
            # Adding SeleniumTestability as SeleniumLibrary plugin
            kwargs["plugins"] += ",SeleniumTestability"
        elif self.using_testability:
            # Setting SeleniumTestability as SeleniumLibrary plugin
            kwargs["plugins"] = "SeleniumTestability"

        locators_path = kwargs.pop("locators_path", locators.DEFAULT_DATABASE)

        SeleniumLibrary.__init__(self, *args, **kwargs)
        self.drivers = []
        self.locators = locators.LocatorsDatabase(locators_path)
        self._element_finder.register("alias", self._find_by_alias, persist=True)

    def _find_by_alias(self, parent, criteria, tag, constraints):
        """Custom 'alias' locator that uses locators database."""
        del constraints

        if not Path(self.locators.path).exists():
            self.logger.warning("File does not exist: %s", self.locators.path)

        self.locators.load()
        if self.locators.error:
            error_msg, error_args = self.locators.error
            raise ValueError(error_msg % error_args)

        entry = self.locators.find_by_name(criteria)
        if not entry:
            raise ValueError(f"Unknown locator alias: {criteria}")

        if entry["type"] != "browser":
            raise ValueError(f"Not a browser locator: {criteria}")

        locator = "{prefix}:{criteria}".format(
            prefix=entry["strategy"], criteria=entry["value"]
        )

        self.logger.info("%s is an alias for %s", criteria, locator)
        return self._element_finder.find(locator, tag, parent)

    def get_preferable_browser_order(self) -> list:
        """Return a list of RPA Framework preferred browsers by OS."""
        return webdriver.DRIVER_PREFERENCE.get(
            platform.system(), webdriver.DRIVER_PREFERENCE["default"]
        )

    @keyword
    def open_available_browser(
        self,
        url: str,
        use_profile: bool = False,
        headless: bool = False,
        maximized: bool = False,
        browser_selection: Any = AUTOMATIC_BROWSER_SELECTION,
    ) -> int:
        """Opens the first available browser in the system in preferred order, or the
        given browser (``browser_selection``).

        ``url`` URL to open

        ``use_profile`` set browser profile, default ``False``

        ``headless`` run in headless mode, default ``False``

        ``maximized`` run window maximized, default ``False``

        ``browser_selection`` browser name, default ``AUTOMATIC_BROWSER_SELECTION``

        Returns an index of the webdriver session.

        === Process of opening a browser ===

        1. Get the order of browsers

        2. Loop the list of preferred browsers

            a. Set the webdriver options for the browser

            b. Create the webdriver using existing installation

            c. (If step b. failed) Download and install webdriver, try again

            d. (If step c. failed) Try starting webdriver in headless mode

        3. Open the URL

        Raises ``BrowserNotFoundError`` if unable to open the browser.

        For information about Safari webdriver setup, see
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
            if index is not None:
                selected_browser = (browser, 1)
                break

            self.logger.info("Could not init webdriver using method 1. ")

            # Second try: Install driver (if there is a manager for driver)
            self.logger.info("Initializing webdriver with downloaded driver (method 2)")
            index = self.create_rpa_webdriver(browser, options, download=True)
            if index is not None:
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
                if index is not None:
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
    ) -> Any:
        """Create a webdriver instance for the given browser.

        The driver will be downloaded if it does not exist when ``download`` is True.

        ``browser`` name of the browser

        ``options`` options for webdriver

        ``download`` if the driver should be download, default ``False``

        Returns an index of the webdriver session, ``None`` if webdriver
        was not initialized.
        """
        self.logger.debug("Driver options for create_rpa_webdriver: %s", options)
        executable = webdriver.executable(browser, download)

        try:
            browser = browser.lower().capitalize()
            browser_management = BrowserManagementKeywords(self)
            if executable:
                index = browser_management.create_webdriver(
                    browser, **options, executable_path=executable
                )
            else:
                index = browser_management.create_webdriver(browser, **options)

            return index
        except WebDriverException as err:
            self.logger.info("Could not open driver: %s", err)

        return None

    def get_browser_order(self, browser_selection: Any) -> list:
        """Get a list of browsers that will be used for open browser
        keywords. Will be one or many.

        ``browser_selection`` ``AUTOMATIC_BROWSER_SELECTION`` will be OS-specific list,
            or one named browser, eg. "Chrome"
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

    def set_driver_options(
        self,
        browser: str,
        use_profile: bool = False,
        headless: bool = False,
        maximized: bool = False,
    ) -> dict:
        """Set options for the given browser.

        Supported at the moment:

            - ChromeOptions
            - FirefoxOptions
            - IeOptions

        ``browser`` to set options for

        ``use_profile`` if a browser user profile is used, default ``False``

        ``headless`` if headless mode should be set, default ``False``

        ``maximized`` if the browser should be run maximized, default ``False``
        """
        rpa_headless_mode = os.getenv("RPA_HEADLESS_MODE", None)
        browser_options = None
        driver_options = {}
        browser = browser.lower()

        if browser in self.AVAILABLE_OPTIONS.keys():
            module = importlib.import_module("selenium.webdriver")
            class_ = getattr(module, self.AVAILABLE_OPTIONS[browser])
            browser_options = class_()
        else:
            return driver_options

        if headless or bool(rpa_headless_mode):
            self.set_headless_options(browser, browser_options)

        if browser_options and maximized:
            self.logger.info("Setting maximized mode")
            browser_options.add_argument("--start-maximized")

        if browser_options and use_profile:
            self.set_user_profile(browser_options)

        self.logger.info(
            "Using driver %s: %s", browser_options, browser_options.to_capabilities()
        )
        if browser_options and browser != "chrome":
            driver_options["options"] = browser_options
        elif browser_options and browser == "chrome":
            self.set_default_options(browser_options)
            prefs = {"safebrowsing.enabled": "true"}
            browser_options.add_experimental_option(
                "excludeSwitches", ["enable-logging", "enable-automation"]
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

        ``url`` URL to open

        ``use_profile`` if a browser user profile is used, default ``False``

        ``headless`` if headless mode should be set, default ``False``

        ``maximized`` if the browser should be run maximized, default ``False``
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
        """Set default browser options

        ``options`` browser options
        """
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--remote-debugging-port=12922")
        options.add_argument("--no-sandbox")

    def set_headless_options(self, browser: str, options: dict) -> None:
        """Set headless mode for the browser, if possible.

        ``browser`` string name of the browser

        ``options`` browser options class instance
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
        """Set user profile configuration into browser options

        Requires environment variable ``RPA_CHROME_USER_PROFILE_DIR``
        to point into user profile directory.

        ``options`` dictionary of browser options
        """
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
        """Open Chrome browser in headless mode.

        ``url`` URL to open
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
        """Capture page and/or element screenshot.

        ``page`` capture a page screenshot, default ``True``

        ``locator`` if defined, take element screenshot, default ``None``

        ``filename_prefix`` prefix for screenshot files, default "screenshot"
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
        """Input text into locator after it has become visible.

        ``locator`` element locator

        ``text`` insert text to locator
        """
        self.wait_until_element_is_visible(locator)
        self.input_text(locator, text)

    @keyword
    def wait_and_click_button(self, locator: str) -> None:
        """Click button once it becomes visible.

        ``locator`` element locator
        """
        self.wait_until_element_is_visible(locator)
        self.click_button(locator)

    @property
    def location(self) -> str:
        """Return browser location."""
        return self.get_location()

    @keyword
    def click_element_if_visible(self, locator: str) -> None:
        """Click element if it is visible

        ``locator`` element locator
        """
        visible = self.is_element_visible(locator)
        if visible:
            self.click_element(locator)

    @keyword
    def is_element_enabled(self, locator: str) -> bool:
        """Is element enabled

        ``locator`` element locator
        """
        return self._run_should_keyword_and_return_status(
            self.element_should_be_enabled, locator
        )

    @keyword
    def is_element_visible(self, locator: str) -> bool:
        """Is element visible

        ``locator`` element locator
        """
        return self._run_should_keyword_and_return_status(
            self.element_should_be_visible, locator
        )

    @keyword
    def is_element_disabled(self, locator: str) -> bool:
        """Is element disabled

        ``locator`` element locator
        """
        return self._run_should_keyword_and_return_status(
            self.element_should_be_disabled, locator
        )

    @keyword
    def is_element_focused(self, locator: str) -> bool:
        """Is element focused

        ``locator`` element locator
        """
        return self._run_should_keyword_and_return_status(
            self.element_should_be_focused, locator
        )

    @keyword
    def is_element_attribute_equal_to(
        self, locator: str, attribute: str, expected: str
    ) -> bool:
        """Is element attribute equal to expected value

        ``locator`` element locator

        ``attribute`` element attribute to check for

        ``expected`` is attribute value equal to this
        """
        return self._run_should_keyword_and_return_status(
            self.element_attribute_value_should_be, locator, attribute, expected
        )

    @keyword
    def is_alert_present(self, text: str = None, action: str = "ACCEPT") -> bool:
        """Is alert box present, which can be identified with text
        and action can also be done which by default is ACCEPT.

        Other possible actions are DISMISS and LEAVE.

        ``text`` check if alert text is matching to this, if `None`
        will check if alert is present at all

        ``action`` possible action if alert is present
        """
        return self._run_should_keyword_and_return_status(
            self.alert_should_be_present, text, action
        )

    @keyword
    def is_checkbox_selected(self, locator: str) -> bool:
        """Is checkbox selected

        ``locator`` element locator
        """
        return self._run_should_keyword_and_return_status(
            self.checkbox_should_be_selected, locator
        )

    @keyword
    def does_frame_contain(self, locator: str, text: str) -> bool:
        """Does frame contain expected text

        ``locator`` locator of the frame to check

        ``text`` does frame contain this text
        """
        return self._run_should_keyword_and_return_status(
            self.frame_should_contain, locator, text
        )

    @keyword
    def does_element_contain(
        self, locator: str, expected: str, ignore_case: bool = False
    ) -> bool:
        """Does element contain expected text

        ``locator`` element locator

        ``expected`` expected element text

        ``ignore_case`` should check be case insensitive, default `False`
        """
        return self._run_should_keyword_and_return_status(
            self.element_should_contain,
            locator=locator,
            expected=expected,
            ignore_case=ignore_case,
        )

    @keyword
    def is_element_text(
        self, locator: str, expected: str, ignore_case: bool = False
    ) -> bool:
        """Is element text expected

        ``locator`` element locator

        ``expected`` expected element text

        ``ignore_case`` should check be case insensitive, default `False`
        """
        return self._run_should_keyword_and_return_status(
            self.element_text_should_be,
            locator=locator,
            expected=expected,
            ignore_case=ignore_case,
        )

    @keyword
    def is_list_selection(self, locator: str, *expected: str) -> bool:
        """Is list selected with expected values

        ``locator`` element locator

        ``expected`` expected selected options
        """
        return self._run_should_keyword_and_return_status(
            self.list_selection_should_be, locator, *expected
        )

    @keyword
    def is_list_selected(self, locator: str) -> bool:
        """Is any option selected in the

        ``locator`` element locator
        """
        self.logger.info("Will return if anything is selected on the list")
        return not self._run_should_keyword_and_return_status(
            self.list_should_have_no_selections, locator
        )

    @keyword
    def is_location(self, url: str) -> bool:
        """Is current URL expected url

        ``url`` expected current URL
        """
        return self._run_should_keyword_and_return_status(self.location_should_be, url)

    @keyword
    def does_location_contain(self, expected: str) -> bool:
        """Does current URL contain expected

        ``expected`` URL should contain this
        """
        return self._run_should_keyword_and_return_status(
            self.location_should_contain, expected
        )

    @keyword
    def does_page_contain(self, text: str) -> bool:
        """Does page contain expected text

        ``text`` page should contain this
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain, text
        )

    @keyword
    def does_page_contain_button(self, locator: str) -> bool:
        """Does page contain expected button

        ``locator`` element locator
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_button, locator
        )

    @keyword
    def does_page_contain_checkbox(self, locator: str) -> bool:
        """Does page contain expected checkbox

        ``locator`` element locator
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_checkbox, locator
        )

    @keyword
    def does_page_contain_element(self, locator: str, count: int = None) -> bool:
        """Does page contain expected element

        ``locator`` element locator

        ``count`` how many times element is expected to appear on page
        by default one or more
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_element, locator=locator, limit=count
        )

    @keyword
    def does_page_contain_image(self, locator: str) -> bool:
        """Does page contain expected image

        ``locator`` element locator
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_image, locator
        )

    @keyword
    def does_page_contain_link(self, locator: str) -> bool:
        """Does page contain expected link

        ``locator`` element locator
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_link, locator
        )

    @keyword
    def does_page_contain_list(self, locator: str) -> bool:
        """Does page contain expected list

        ``locator`` element locator
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_list, locator
        )

    @keyword
    def does_page_contain_radio_button(self, locator: str) -> bool:
        """Does page contain expected radio button

        ``locator`` element locator
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_radio_button, locator
        )

    @keyword
    def does_page_contain_textfield(self, locator: str) -> bool:
        """Does page contain expected textfield

        ``locator`` element locator
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_textfield, locator
        )

    @keyword
    def is_radio_button_set_to(self, group_name: str, value: str) -> bool:
        """Is radio button group set to expected value

        ``group_name`` radio button group name

        ``value`` expected value
        """
        return self._run_should_keyword_and_return_status(
            self.radio_button_should_be_set_to, group_name, value
        )

    @keyword
    def is_radio_button_selected(self, group_name: str) -> bool:
        """Is any radio button selected in the button group

        ``group_name`` radio button group name
        """
        self.logger.info(
            "Will return if anything is selected on the radio button group"
        )
        return not self._run_should_keyword_and_return_status(
            self.radio_button_should_not_be_selected, group_name
        )

    @keyword
    def does_table_cell_contain(
        self, locator: str, row: int, column: int, expected: str
    ) -> bool:
        """Does table cell contain expected text

        ``locator`` element locator for the table

        ``row`` row index starting from 1 (beginning) or -1 (from the end)

        ``column`` column index starting from 1 (beginning) or -1 (from the end)

        ``expected`` expected text in table row
        """
        return self._run_should_keyword_and_return_status(
            self.table_cell_should_contain, locator, row, column, expected
        )

    @keyword
    def does_table_column_contain(
        self, locator: str, column: int, expected: str
    ) -> bool:
        """Does table column contain expected text

        ``locator`` element locator for the table

        ``column`` column index starting from 1 (beginning) or -1 (from the end)

        ``expected`` expected text in table column
        """
        return self._run_should_keyword_and_return_status(
            self.table_column_should_contain, locator, column, expected
        )

    @keyword
    def does_table_row_contain(self, locator: str, row: int, expected: str) -> bool:
        """Does table row contain expected text

        ``locator`` element locator for the table

        ``row`` row index starting from 1 (beginning) or -1 (from the end)

        ``expected`` expected text in table row
        """
        return self._run_should_keyword_and_return_status(
            self.table_row_should_contain, locator, row, expected
        )

    @keyword
    def does_table_footer_contain(self, locator: str, expected: str) -> bool:
        """Does table footer contain expected text

        ``locator`` element locator for the table

        ``expected`` expected text in table footer
        """
        return self._run_should_keyword_and_return_status(
            self.table_footer_should_contain, locator, expected
        )

    @keyword
    def does_table_header_contain(self, locator: str, expected: str) -> bool:
        """Does table header contain expected text

        ``locator`` element locator for the table

        ``expected`` expected text in table header
        """
        return self._run_should_keyword_and_return_status(
            self.table_header_should_contain, locator, expected
        )

    @keyword
    def does_table_contain(self, locator: str, expected: str) -> bool:
        """Does table contain expected text

        ``locator`` element locator

        ``expected`` expected text in table
        """
        return self._run_should_keyword_and_return_status(
            self.table_should_contain, locator, expected
        )

    @keyword
    def is_textarea_value(self, locator: str, expected: str) -> bool:
        """Is textarea matching expected value

        ``locator`` element locator

        ``expected`` expected textarea value
        """
        return self._run_should_keyword_and_return_status(
            self.textarea_value_should_be, locator, expected
        )

    @keyword
    def does_textarea_contain(self, locator: str, expected: str) -> bool:
        """Does textarea contain expected text

        ``locator`` element locator

        ``expected`` expected text in textarea
        """
        return self._run_should_keyword_and_return_status(
            self.textarea_should_contain, locator, expected
        )

    @keyword
    def does_textfield_contain(self, locator: str, expected: str) -> bool:
        """Does textfield contain expected text

        ``locator`` element locator

        ``expected`` expected text in textfield
        """
        return self._run_should_keyword_and_return_status(
            self.textfield_should_contain, locator, expected
        )

    @keyword
    def is_textfield_value(self, locator: str, expected: str) -> bool:
        """Is textfield value expected

        ``locator`` element locator

        ``expected`` expected textfield value
        """
        return self._run_should_keyword_and_return_status(
            self.textfield_value_should_be, locator, expected
        )

    @keyword
    def is_title(self, title: str) -> bool:
        """Is page title expected

        ``title`` expected title value
        """
        return self._run_should_keyword_and_return_status(self.title_should_be, title)

    def _run_should_keyword_and_return_status(self, runnable_keyword, *args, **kwargs):
        try:
            runnable_keyword(*args, **kwargs)
            return True
        except AssertionError:
            return False

    @keyword
    def get_element_status(self, locator: str) -> dict:
        """Return dictionary containing element status of:

            - visible
            - enabled
            - disabled
            - focused

        ``locator`` element locator
        """
        status_object = dict()
        status_object["visible"] = self.is_element_visible(locator)
        status_object["enabled"] = self.is_element_enabled(locator)
        status_object["disabled"] = self.is_element_disabled(locator)
        status_object["focused"] = self.is_element_focused(locator)
        return status_object

    @keyword
    def get_testability_status(self) -> bool:
        """Get SeleniumTestability plugin status"""
        return self.using_testability
