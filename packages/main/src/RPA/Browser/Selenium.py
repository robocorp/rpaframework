# pylint: disable=too-many-lines
from argparse import Action
import atexit
import base64
import importlib
import json
import logging
import os
import platform
import time
import traceback
import urllib.parse
from collections import OrderedDict
from contextlib import contextmanager
from functools import partial
from itertools import product
from typing import Any, Optional, List, Union, timedelta
from pathlib import Path
import webbrowser

import robot
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from SeleniumLibrary import SeleniumLibrary, EMBED
from SeleniumLibrary.base import keyword
from SeleniumLibrary.errors import ElementNotFound
from SeleniumLibrary.keywords import (
    BrowserManagementKeywords,
    ScreenshotKeywords,
    AlertKeywords,
)
from selenium.webdriver import ChromeOptions, FirefoxProfile

from RPA.core import webdriver, notebook
from RPA.core.locators import LocatorsDatabase, BrowserLocator


def html_table(header, rows):
    """Create HTML table that can be used for logging."""
    output = '<div class="doc"><table>'
    output += "<tr>" + "".join(f"<th>{name}</th>" for name in header) + "</tr>"
    for row in rows:
        output += "<tr>" + "".join(f"<td>{name}</td>" for name in row) + "</tr>"
    output += "</table></div>"
    return output


@contextmanager
def suppress_logging():
    """Suppress webdrivermanager warnings and errors in scope."""
    logger = logging.getLogger("webdrivermanager.misc")
    logger_warning, logger_error = logger.warning, logger.error

    try:
        logger.warning = logger.error = logger.info
        yield
    finally:
        logger.warning, logger.error = logger_warning, logger_error


def ensure_scheme(url: str, default: Optional[str]) -> str:
    """Ensures that a URL has a scheme, such as `http` or `https`"""
    if default is None:
        return url

    parts = list(urllib.parse.urlsplit(url))
    if not parts[0]:
        parts[0] = str(default)
        url = urllib.parse.urlunsplit(parts)

    return url


class BrowserNotFoundError(ValueError):
    """Raised when browser can't be initialized."""


class BrowserManagementKeywordsOverride(BrowserManagementKeywords):
    """Overriden keywords for browser management."""

    def __init__(self, ctx):
        super().__init__(ctx)
        self._default_scheme = "https"

    @keyword
    def set_default_url_scheme(self, scheme: Optional[str]) -> None:
        """Sets the default `scheme` used for URLs without a defined
        value, such as `http` or `https`.

        The feature is disabled if the value is set to `None`.
        """
        self._default_scheme = scheme

    @keyword
    def go_to(self, url: str) -> None:
        """Navigates the current browser window to the provided `url`.

        **Example**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Navigate to URL
                Go To    www.google.com

        :param url: URL to open
        """
        url = ensure_scheme(url, self._default_scheme)
        super().go_to(url)

        go_to.__doc__ = BrowserManagementKeywords.go_to.__doc__

    @keyword
    def open_browser(
        self,
        url: Optional[str] = None,
        browser: str = "firefox",
        alias: Optional[str] = None,
        remote_url: Union[bool, str] = False,
        desired_capabilities: Union[dict, None, str] = None,
        ff_profile_dir: Union[FirefoxProfile, str, None] = None,
        options: Any = None,
        service_log_path: Optional[str] = None,
        executable_path: Optional[str] = None,
    ) -> str:
        """Opens a new browser instance to the optional ``url``.

        The ``browser`` argument specifies which browser to use. The
        supported browsers are listed in the table below. The browser names
        are case-insensitive and some browsers have multiple supported names.

        +--------------------------+--------------------------+
        |      Browser             |          Name(s)         |
        +==========================+==========================+
        | Firefox                  | firefox, ff              |
        +--------------------------+--------------------------+
        | Google Chrome            | googlechrome, chrome, gc |
        +--------------------------+--------------------------+
        | Headless Firefox         | headlessfirefox          |
        +--------------------------+--------------------------+
        | Headless Chrome          | headlesschrome           |
        +--------------------------+--------------------------+
        | Internet Explorer        | internetexplorer, ie     |
        +--------------------------+--------------------------+
        | Edge                     | edge                     |
        +--------------------------+--------------------------+
        | Safari                   | safari                   |
        +--------------------------+--------------------------+
        | Opera                    | opera                    |
        +--------------------------+--------------------------+
        | Android                  | android                  |
        +--------------------------+--------------------------+
        | Iphone                   | iphone                   |
        +--------------------------+--------------------------+
        | PhantomJS                | phantomjs                |
        +--------------------------+--------------------------+
        | HTMLUnit                 | htmlunit                 |
        +--------------------------+--------------------------+
        | HTMLUnit with Javascript | htmlunitwithjs           |
        +--------------------------+--------------------------+

        To be able to actually use one of these browsers, you need to have
        a matching Selenium browser driver available. See the `project documentation`_
        for more details. Headless Firefox and
        Headless Chrome are new additions in SeleniumLibrary 3.1.0
        and require Selenium 3.8.0 or newer.

        .. _project documentation`: https://github.com/robotframework/SeleniumLibrary#browser-drivers

        After opening the browser, it is possible to use optional
        ``url`` to navigate the browser to the desired address.

        Optional ``alias`` is an alias given for this browser instance and
        it can be used for switching between browsers. When same ``alias``
        is given with two `Open Browser` keywords, the first keyword will
        open a new browser, but the second one will switch to the already
        opened browser and will not open a new browser. The ``alias``
        definition overrules ``browser`` definition. When same ``alias``
        is used but a different ``browser`` is defined, then switch to
        a browser with same alias is done and new browser is not opened.
        An alternative approach for switching is using an index returned
        by this keyword. These indices start from 1, are incremented when new
        browsers are opened, and reset back to 1 when `Close All Browsers`
        is called. See `Switch Browser` for more information and examples.

        Optional ``remote_url`` is the URL for a `Selenium Grid`_.

        .. _Selenium Grid: https://github.com/SeleniumHQ/selenium/wiki/Grid2

        Optional ``desired_capabilities`` can be used to configure, for example,
        logging preferences for a browser or a browser and operating system
        when using `Sauce Labs`_. Desired capabilities can
        be given either as a Python dictionary or as a string in the format
        ``key1:value1,key2:value2``. `Selenium documentation`_ lists possible
        capabilities that can be enabled.

        .. _Sauce Labs: http://saucelabs.com
        .. _Selenium documentation: https://github.com/SeleniumHQ/selenium/wiki/DesiredCapabilities

        Optional ``ff_profile_dir`` is the path to the Firefox profile
        directory if you wish to overwrite the default profile Selenium
        uses. Notice that prior to SeleniumLibrary 3.0, the library
        contained its own profile that was used by default. The
        ``ff_profile_dir`` can also be an instance of the
        selenium.webdriver.FirefoxProfile_.
        As a third option, it is possible to use `FirefoxProfile` methods
        and attributes to define the profile using methods and attributes
        in the same way as with ``options`` argument. Example: It is possible
        to use FirefoxProfile `set_preference` to define different
        profile settings. See ``options`` argument documentation in below
        how to handle backslash escaping.

        .. _selenium.webdriver.FirefoxProfile: https://seleniumhq.github.io/selenium/docs/api/py/webdriver_firefox/selenium.webdriver.firefox.firefox_profile.html

        Optional ``options`` argument allows defining browser specific
        Selenium options. Example for Chrome, the ``options`` argument
        allows defining the following `methods and attributes`_
        and for Firefox these `methods and attributes`_
        are available. Please note that not all browsers, supported by the
        SeleniumLibrary, have Selenium options available. Therefore please
        consult the Selenium documentation which browsers do support
        the Selenium options. If ``browser`` argument is `android` then
        `Chrome options`_
        is used. Selenium options are also supported, when ``remote_url``
        argument is used.

        .. _methods and attributes: https://seleniumhq.github.io/selenium/docs/api/py/webdriver_chrome/selenium.webdriver.chrome.options.html#selenium.webdriver.chrome.options.Options
        .. _methods and attributes: https://seleniumhq.github.io/selenium/docs/api/py/webdriver_firefox/selenium.webdriver.firefox.options.html?highlight=firefox#selenium.webdriver.firefox.options.Options
        .. _Chrome options: https://seleniumhq.github.io/selenium/docs/api/py/webdriver_chrome/selenium.webdriver.chrome.options.html#selenium.webdriver.chrome.options.Options

        The SeleniumLibrary ``options`` argument accepts Selenium
        options in two different formats: as a string and as Python object
        which is an instance of the Selenium options class.

        The string format allows defining Selenium options methods
        or attributes and their arguments in Robot Framework test data.
        The method and attributes names are case and space sensitive and
        must match to the Selenium options methods and attributes names.
        When defining a method, it must be defined in a similar way as in
        python: method name, opening parenthesis, zero to many arguments
        and closing parenthesis. If there is a need to define multiple
        arguments for a single method, arguments must be separated with
        comma, just like in Python. Example: `add_argument("--headless")`
        or `add_experimental_option("key", "value")`. Attributes are
        defined in a similar way as in Python: attribute name, equal sign,
        and attribute value. Example, `headless=True`. Multiple methods
        and attributes must be separated by a semicolon. Example:
        `add_argument("--headless");add_argument("--start-maximized")`.

        Arguments allow defining Python data types and arguments are
        evaluated by using Python `ast.literal_eval`_.
        Strings must be quoted with single or double quotes, example "value"
        or 'value'. It is also possible to define other Python builtin
        data types, example `True` or `None`, by not using quotes
        around the arguments.

        .. _ast.literal_eval: https://docs.python.org/3/library/ast.html#ast.literal_eval

        The string format is space friendly. Usually, spaces do not alter
        the defining methods or attributes. There are two exceptions.
        In some Robot Framework test data formats, two or more spaces are
        considered as cell separator and instead of defining a single
        argument, two or more arguments may be defined. Spaces in string
        arguments are not removed and are left as is. Example
        `add_argument ( "--headless" )` is same as
        `add_argument("--headless")`. But `add_argument(" --headless ")` is
        not same same as `add_argument ( "--headless" )`, because
        spaces inside of quotes are not removed. Please note that if
        options string contains backslash, example a Windows OS path,
        the backslash needs escaping both in Robot Framework data and
        in Python side. This means single backslash must be writen using
        four backslash characters. Example, Windows path:
        "C:\\path\\to\\profile" must be written as
        "C:\\\\\\\\path\\\\\\to\\\\\\\\profile". Another way to write
        backslash is use Python `raw strings`_
        and example write: r"C:\\\\path\\\\to\\\\profile".

        .. _raw strings: https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals

        As last format, ``options`` argument also supports receiving
        the Selenium options as Python class instance. In this case, the
        instance is used as-is and the SeleniumLibrary will not convert
        the instance to other formats.
        For example, if the following code return value is saved to
        `${options}` variable in the Robot Framework data:
        | options = webdriver.ChromeOptions()
        | options.add_argument('--disable-dev-shm-usage')
        | return options

        Then the `${options}` variable can be used as an argument to
        ``options``.

        Example the ``options`` argument can be used to launch Chomium-based
        applications which utilize the `Chromium Embedded Framework`_
        . To lauch Chomium-based application, use ``options`` to define
        `binary_location` attribute and use `add_argument` method to define
        `remote-debugging-port` port for the application. Once the browser
        is opened, the test can interact with the embedded web-content of
        the system under test.

        .. _Chromium Embedded Framework: https://bitbucket.org/chromiumembedded/cef/wiki/UsingChromeDriver

        Optional ``service_log_path`` argument defines the name of the
        file where to write the browser driver logs. If the
        ``service_log_path``  argument contain a  marker ``{index}``, it
        will be automatically replaced with unique running
        index preventing files to be overwritten. Indices start's from 1,
        and how they are represented can be customized using Python's
        `format string syntax`_.

        .. _format string syntax: https://docs.python.org/3/library/string.html#format-string-syntax

        Optional ``executable_path`` argument defines the path to the driver
        executable, example to a chromedriver or a geckodriver. If not defined
        it is assumed the executable is in the `$PATH`_.

        .. _$PATH: [https://en.wikipedia.org/wiki/PATH_(variable)

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Open Multiple Browsers
                [Documentation]    The following keyword demonstrates how
                ...    Selenium handles opening multiple browsers

                # Each of the following Open Browser calls opens up
                # a new browser instnce
                Open Browser    http://example.com    Chrome
                Open Browser    http://example.com    Firefox    alias=Firefox
                Open Browser
                ...    http://example.com
                ...    Edge
                ...    remote_url=http://127.0.0.1:4444/wd/hub
                Open Browser    about:blank
                Open Browser    browser=Chrome

                # Each of the following Open Browser calls opens up a new browser instance
                # (on top of the above calls) and the index is captured for each broswer
                ${1_index} =    Open Browser    http://example.com    Chrome    alias=Chrome    # Opens new browser because alias is new.
                ${2_index} =    Open Browser    http://example.com    Firefox   # Opens new browser because alias is not defined.
                ${3_index} =    Open Browser    http://example.com    Chrome    alias=Chrome    # Switches to the browser with Chrome alias.
                ${4_index} =    Open Browser    http://example.com    Chrome    alias=${1_index}    # Switches to the browser with Chrome alias.

                # Compare each of the open browsers to check that returned indexes match
                Should Be Equal    ${1_index}    ${3_index}
                Should Be Equal    ${1_index}    ${4_index}
                Should Be Equal    ${2_index}    ${2}

                # Examples when using `Chrome options`_ method
                Open Browser
                ...    http://example.com
                ...    Chrome
                ...    options=add_argument("--disable-popup-blocking"); add_argument("--ignore-certificate-errors")    # Sting format.
                ${options} =    Get Options    # Selenium options instance.
                Open Browser
                ...    http://example.com
                ...    Chrome
                ...    options=${options}
                Open Browser
                ...    None
                ...    Chrome
                ...    options=binary_location="/path/to/binary";add_argument("remote-debugging-port=port")    # Start Chomium-based application.
                Open Browser
                ...    None
                ...    Chrome
                ...    options=binary_location=r"C:\\\\path\\\\to\\\\binary"    # Windows OS path escaping.

                .. _Chrome options: https://seleniumhq.github.io/selenium/docs/api/py/webdriver_chrome/selenium.webdriver.chrome.options.html#selenium.webdriver.chrome.options.Options

                # Examples for FirefoxProfile
                Open Browser
                ...    http://example.com
                ...    Firefox
                ...    ff_profile_dir=/path/to/profile    # Using profile from disk.
                Open Browser
                ...    http://example.com
                ...    Firefox
                ...    ff_profile_dir=${FirefoxProfile_instance}    # Using instance of FirefoxProfile.
                Open Browser
                ...    http://example.com
                ...    Firefox
                ...    ff_profile_dir=set_preference("key", "value");set_preference("other", "setting")    # Defining profile using FirefoxProfile mehtods.

        If the provided configuration options are not enough, it is possible
        to use `Create Webdriver` to customize browser initialization even
        more.

        Applying ``desired_capabilities`` argument also for local browser is
        new in SeleniumLibrary 3.1.

        Using ``alias`` to decide, is the new browser opened is new
        in SeleniumLibrary 4.0. The ``options`` and ``service_log_path``
        are new in SeleniumLibrary 4.0. Support for ``ff_profile_dir``
        accepting an instance of the `selenium.webdriver.FirefoxProfile`
        and support defining FirefoxProfile with methods and
        attributes are new in SeleniumLibrary 4.0.

        Making ``url`` optional is new in SeleniumLibrary 4.1.

        The ``executable_path`` argument is new in SeleniumLibrary 4.2.

        :param url: desired address
        :param browser: specifies which browser to use, default is "firefox"
        :param alias: alias given for this browser instance and
         it can be used for switching between browsers
        :param remote_url: the URL for a `Selenium Grid`, default is `False`
        :param desired_capabilities: used to configure additional capabilities
        :param ff_profile_dir: path to the Firefox profile
         directory if you wish to overwrite the default profile Selenium
         uses
        :param options: allows defining browser specific Selenium options
        :param service_log_path: defines the name of the file where to write the
         browser driver logs
        :param executable_path: defines the path to the driver executable
        """

        url = ensure_scheme(url, self._default_scheme)
        return super().open_browser(
            url=url,
            browser=browser,
            alias=alias,
            remote_url=remote_url,
            desired_capabilities=desired_capabilities,
            ff_profile_dir=ff_profile_dir,
            options=options,
            service_log_path=service_log_path,
            executable_path=executable_path,
        )

        open_browser.__doc__ = BrowserManagementKeywords.open_browser.__doc__

    @keyword
    def add_cookie(
        self,
        name: str,
        value: str,
        path: Optional[str] = None,
        domain: Optional[str] = None,
        secure: Optional[bool] = None,
        expiry: Optional[str] = None,
    ):
        """Adds a cookie to your current session.

        `name` and `value` are required, `path`, `domain`, `secure` and `expiry` are optional.
        `expiry` supports the same formats as the `DateTime`_ library or an epoch timestamp.

        .. _DateTime: http://robotframework.org/robotframework/latest/libraries/DateTime.html

        Prior to SeleniumLibrary 3.0 setting expiry did not work.

        **Example**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Make Cookie Monster Happy
                Add Cookie    foo    bar
                Add Cookie    foo    bar    domain=example.com
                Add Cookie    foo    bar    expiry=2027-09-28 16:21:35    # Expiry as timestamp.
                Add Cookie    foo    bar    expiry=1822137695    # Expiry as epoch seconds.

        :param name: cookie name
        :param value: cookie value, acceptable cookie values can be found `here`_
        :param path: where the cookie will be stored
        :param domain: domain the cookie is visable to
        :param secure: whether the cookie is a secure cookie (`True`) or not (`False`)
        :param expiry: when the cookie expires

        .. _here: https://www.w3.org/TR/webdriver1/#cookies
        """  # noqa: E501

        super().add_cookie(
            name, value, path=path, domain=domain, secure=secure, expiry=expiry
        )

    @keyword
    def add_location_strategy(
        self,
        strategy_name: str,
        strategy_keyword: str,
        persist: bool = False,
    ):
        """Adds a custom location strategy.

        See Custom locators for information on how to create and use custom strategies.
         `Remove Location Strategy` can be used to remove a registered strategy.

        Location strategies are automatically removed after leaving the current scope by default.
         Setting persist to a true value (see Boolean arguments) will cause the location strategy
         to stay registered throughout the life of the test.

        **Example**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            New Persistent Location Strategy
                Add Location Strategy
                ...    extJs
                ...    return window.document.getElementById((Ext.ComponentQuery.query(arguments[0])[0]).getId());
                ...    bool=${TRUE}

        :param strategy_name: name the strategy will be referred to in later keywords
        :param strategy_keyword: strategy (logic) necessary to identify the
         text or property for that locator
        :param persist: determines if the new strategy will persist through all tests
         (`True`) or only the current scope (`False`), default is `False`
        """  # noqa: E501

        super().add_location_strategy(
            strategy_name, strategy_keyword=strategy_keyword, persist=persist
        )

    @keyword
    def alert_should_be_present(
        self,
        text: str,
        action: str = ACCEPT,
        timeout: Optional[Union[timedelta, None]] = None,
    ):
        """Verifies that an alert is present and by default, accepts it.

        Fails if no alert is present. If `text` is a non-empty string, then it is used to verify alert's message. The alert is accepted by default, but that behavior can be controlled by using the `action` argument same way as with Handle Alert.

        `timeout` specifies how long to wait for the alert to appear. If it is not given, the global default timeout is used instead.

        `action` and `timeout` arguments are new in SeleniumLibrary 3.0. In earlier versions, the alert was always accepted and a timeout was hardcoded to one second.

        **Example**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for Alert
                Alert Should Be Present    Are you sure?    action=ACCEPT    timeout=30s

        :param text: alert message text
        :param action: additional alert actions can be found
         in the ``Handle Alert`` keyword, defaults to `ACCEPT`
        :param timeout: how long to wait for the alert to appear
        """

        super().alert_should_be_present(text, action=action, timeout=timeout)

    @keyword
    def alert_should_not_be_present(
        self,
        action: str = ACCEPT,
        timeout: Optional[Union[timedelta, None]] = None,
    ):
        """Verifies that no alert is present.

        If the alert actually exists, the `action` argument determines how it should
         be handled. By default, the alert is accepted, but it can be also dismissed
          or left open the same way as with the ``Handle Alert`` keyword.

        `timeout` specifies how long to wait for the alert to appear. By default, is
         not waited for the alert at all, but a custom time can be given if alert
         may be delayed. See the _time format_ section for information about
         the syntax.

        New in SeleniumLibrary 3.0.

        **Example**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Hopefully No Alert Appears
                Alert Should Be Present    action=DISMISS    timeout=30s

        :param action: additional alert actions can be found
         in the ``Handle Alert`` keyword, defaults to `ACCEPT`
        :param timeout: how long to wait for the alert to appear
        """

        super().alert_should_not_be_present(action=action, timeout=timeout)

    @keyword
    def assign_id_to_element(
        self,
        locator: Union[WebElement, str] = None,
        id: str = None,
    ):

        """Assigns a temporary id to the element specified by locator.

        This is mainly useful if the locator is complicated and/or slow XPath
        expression and it is needed multiple times. Identifier expires when the
        page is reloaded.

        See the Locating elements section for details about the locator syntax.

        **Example**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Give This Element An ID
                Assign ID to Element
                ...    //ul[@class='example' and ./li[contains(., 'Stuff')]]
                ...    my id
                # This verifies that the newly assigned ID is found on the page
                Page Should Contain Element    my id

        :param locator: element locator
        :param id: temporary id to the element specified by locator
        """

        super().assign_id_to_element(locator, id)

    @keyword
    def capture_element_screenshot(
        self,
        locator: Union[WebElement, None, str],
        filename: str = DEFAULT_FILENAME_ELEMENT,
    ) -> str:
        """Captures a screenshot from the element identified by ``locator`` and embeds it into log file.

        See `Capture Page Screenshot` for details about ``filename`` argument.
        See the `Locating elements` section for details about the locator
        syntax.

        An absolute path to the created element screenshot is returned.

        Support for capturing the screenshot from an element has limited support
        among browser vendors. Please check the browser vendor driver documentation
        does the browser support capturing a screenshot from an element.

        New in SeleniumLibrary 3.3. Support for EMBED is new in SeleniumLibrary 4.2.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Capture Screenshot With Default Filename
                    Capture Element Screenshot    id:image_id

                *** Keyword ***
                Capture Screenshot With Custom Filename
                    Capture Element Screenshot    id:image_id    ${OUTPUTDIR}/id_image_id-1.png

                *** Keyword ***
                Capture Screenshot And Embed In Logs
                    Capture Element Screenshot    id:image_id    EMBED

        :param locator: element locator
        :param filename: specifies the name of the file to write the screenshot into
        :return: absolute path to the created element screenshot
        """

        super().capture_element_screenshot(locator, filename)

    @keyword
    def capture_page_screenshot(self, filename: str = DEFAULT_FILENAME_PAGE) -> str:
        """Takes a screenshot of the current page and embeds it into a log file.

        ``filename`` argument specifies the name of the file to write the
        screenshot into. The directory where screenshots are saved can be
        set when `importing` the library or by using the `Set Screenshot
        Directory` keyword. If the directory is not configured, screenshots
        are saved to the same directory where Robot Framework's log file is
        written.

        If ``filename`` equals to EMBED (case insensitive), then screenshot
        is embedded as Base64 image to the log.html. In this case file is not
        created in the filesystem.

        Starting from SeleniumLibrary 1.8, if ``filename`` contains marker
        ``{index}``, it will be automatically replaced with an unique running
        index, preventing files to be overwritten. Indices start from 1,
        and how they are represented can be customized using Python's
        [https://docs.python.org/3/library/string.html#format-string-syntax|
        format string syntax].

        An absolute path to the created screenshot file is returned or if
        ``filename``  equals to EMBED, word `EMBED` is returned.

        Support for EMBED is new in SeleniumLibrary 4.2

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Taking Multiple Screenshots and Confirming They Exist
                    Capture Page Screenshot
                    File Should Exist          ${OUTPUTDIR}/selenium-screenshot-1.png
                    ${path} =                  Capture Page Screenshot
                    File Should Exist          ${OUTPUTDIR}/selenium-screenshot-2.png
                    File Should Exist          ${path}
                    Capture Page Screenshot    custom_name.png
                    File Should Exist          ${OUTPUTDIR}/custom_name.png
                    Capture Page Screenshot    custom_with_index_{index}.png
                    File Should Exist          ${OUTPUTDIR}/custom_with_index_1.png
                    Capture Page Screenshot    formatted_index_{index:03}.png
                    File Should Exist          ${OUTPUTDIR}/formatted_index_001.png
                    Capture Page Screenshot    EMBED
                    File Should Not Exist      EMBED

        :param filename: specifies the name of the file to write the screenshot into
        :return: absolute path to the created screenshot file
        """

        super().capture_page_screenshot(filename)

    @keyword
    def Checkbox_Should_Be_Selected(self, locator: Union[WebElement, str]):
        """Verifies checkbox ``locator`` is selected/checked.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Verify Checkbox Is Checked
                    Checkbox Should Be Selected
                    ...    id=checkbox_locator

        :param locator: element locator
        """

        super().checkbox_should_be_selected(locator)

    @keyword
    def checkbox_should_not_be_selected(self, locator: Union[WebElement, str]):
        """Verifies checkbox ``locator`` is not selected/checked.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Verify Checkbox Is Blank
                    Checkbox Should Not Be Selected
                    ...    id=checkbox_locator

        :param locator: element locator
        """

        super().checkbox_should_not_be_selected(locator)

    @keyword
    def choose_file(self, locator: Union[WebElement, str], file_path: str):
        """Inputs the ``file_path`` into the file input field ``locator``.

        This keyword is most often used to input files into upload forms.
        The keyword does not check ``file_path`` is the file or folder
        available on the machine where tests are executed. If the ``file_path``
        points at a file and when using Selenium Grid, Selenium will
        [https://seleniumhq.github.io/selenium/docs/api/py/webdriver_remote/selenium.webdriver.remote.command.html?highlight=upload#selenium.webdriver.remote.command.Command.UPLOAD_FILE|magically],
        transfer the file from the machine where the tests are executed
        to the Selenium Grid node where the browser is running.
        Then Selenium will send the file path, from the nodes file
        system, to the browser.

        That ``file_path`` is not checked, is new in SeleniumLibrary 4.0.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Upload File To Form
                    Choose File    my_upload_field    ${CURDIR}/trades.csv

        :param locator: element locator
        :param file_path: path to the file to be uploaded
        """

        super().choose_file(locator, file_path)

    @keyword
    def clear_element_text(self, locator: Union[WebElement, str]):
        """Clears the value of the text-input-element identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Delete All Of The Current Text
                    Clear Element Text    id:text_field
        """

        super().clear_element_text(locator)

    @keyword
    def click_button(
        self, locator: Union[WebElement, str], modifier: Union[bool, str] = False
    ):
        """Clicks the button identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax. When using the default locator strategy, buttons are
        searched using ``id``, ``name``, and ``value``.

        See the `Click Element` keyword for details about the
        ``modifier`` argument.

        The ``modifier`` argument is new in SeleniumLibrary 3.3

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Click The Selected Button
                    Click Button    id:button_locator

                *** Keyword ***
                Shift Click The Selected Button
                    Click Button    id:button_locator    modifier=SHIFT

        :param locator: element locator
        :param modifier: used to pass Selenium Keys when clicking the button
        """

        super().click_button(locator, modifier=modifier)

    @keyword
    def click_element(
        self,
        locator: Union[WebElement, str],
        modifier: Union[bool, str] = False,
        action_chain: bool = False,
    ):
        """Click the element identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        The ``modifier`` argument can be used to pass
        [https://seleniumhq.github.io/selenium/docs/api/py/webdriver/selenium.webdriver.common.keys.html#selenium.webdriver.common.keys.Keys|Selenium Keys]
        when clicking the element. The `+` can be used as a separator
        for different Selenium Keys. The `CTRL` is internally translated to
        the `CONTROL` key. The ``modifier`` is space and case insensitive, example
        "alt" and " aLt " are supported formats to
        [https://seleniumhq.github.io/selenium/docs/api/py/webdriver/selenium.webdriver.common.keys.html#selenium.webdriver.common.keys.Keys.ALT|ALT key]
        . If ``modifier`` does not match to Selenium Keys, keyword fails.

        If ``action_chain`` argument is true, see `Boolean arguments` for more
        details on how to set boolean argument, then keyword uses ActionChain
        based click instead of the <web_element>.click() function. If both
        ``action_chain`` and ``modifier`` are defined, the click will be
        performed using ``modifier`` and ``action_chain`` will be ignored.

        The ``modifier`` argument is new in SeleniumLibrary 3.2
        The ``action_chain`` argument is new in SeleniumLibrary 4.1

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Would click element without any modifiers
                    Click Element    id:button

                *** Keyword ***
                Would click element with CTLR key pressed down
                    Click Element    id:button    CTRL

                *** Keyword ***
                Would click element with CTLR and ALT keys pressed down
                    Click Element    id:button    CTRL+ALT

                *** Keyword ***
                Clicks the button using Selenium ActionChains
                    Click Element    id:button    action_chain=True

        :param locator: element locator
        :param modifier: used to pass Selenium Keys when clicking the element
        :param action_chain: if `True` uses ActionChain click instead of
         <web_element>.Click, defaults to `False`
        """

        super().click_element(locator, modifier=modifier, action_chain=action_chain)

    @keyword
    def click_element_at_coordinates(
        self, locator: Union[WebElement, str], xoffset: int, yoffset: int
    ):
        """Click the element ``locator`` at ``xoffset/yoffset``.

        The Cursor is moved and the center of the element and x/y coordinates are
        calculated from that point.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Click Offset From Element
                    Click Element At Coordinates
                    ...    id:element_locator
                    ...    xoffset=158
                    ...    yoffset=473

        :param locator: element locator
        :param xoffset: left and right offset from the center of the element
        :param yoffset: up and down offset from the center of the element
        """

        super().click_element_at_coordinates(locator, xoffset, yoffset)

    @keyword
    def click_image(
        self, locator: Union[WebElement, str], modifier: Union[bool, str] = False
    ):
        """Clicks an image identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax. When using the default locator strategy, images are searched
        using ``id``, ``name``, ``src`` and ``alt``.

        See the `Click Element` keyword for details about the
        ``modifier`` argument.

        The ``modifier`` argument is new in SeleniumLibrary 3.3

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Click The Selected Image
                    Click Image    id:image_locator

                *** Keyword ***
                Control Click The Selected Image
                    Click Image    id:image_locator    modifier=CTRL

        :param locator: element locator
        :param modifier: used to pass Selenium Keys when clicking the image
        """

        super().click_image(locator, modifier=modifier)

    @keyword
    def click_link(
        self, locator: Union[WebElement, str], modifier: Union[bool, str] = False
    ):
        """Clicks a link identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax. When using the default locator strategy, links are searched
        using ``id``, ``name``, ``href`` and the link text.

        See the `Click Element` keyword for details about the
        ``modifier`` argument.

        The ``modifier`` argument is new in SeleniumLibrary 3.3

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Click The Selected Link
                    Click Link    id:link_locator

                *** Keyword ***
                Control Click The Selected Link
                    Click Link    id:link_locator    modifier=CTRL

        :param locator: element locator
        :param modifier: used to pass Selenium Keys when clicking the link
        """

        super().click_link(locator, modifier=modifier)

    @keyword
    def close_all_browsers(self):
        """Closes all open browsers and resets the browser cache.

        After this keyword, new indexes returned from `Open Browser` keyword
        are reset to 1.

        This keyword should be used in test or suite teardown to make sure
        all browsers are closed.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                All Open Browsers Are Closed
                    Close All browsers
        """

        super().close_all_browsers()

    @keyword
    def close_browser(self):
        """Closes the current browser.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Close Just This Browser
                    Close Browser
        """

        super().close_browser()

    @keyword
    def close_window(self):
        """Closes currently opened and selected browser window/tab.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                And Now The Window Disappears
                    Close Window
        """

        super().close_window()

    @keyword
    def cover_element(self, locator: Union[WebElement, str]):
        """Will cover elements identified by ``locator`` with a blue div without breaking page layout.

        See the `Locating elements` section for details about the locator
        syntax.

        New in SeleniumLibrary 3.3.0

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Let's Maybe Hide This Container
                    Cover Element    css:div#container

        :param locator: element locator
        """

        super().cover_element(locator)

    @keyword
    def create_webdriver(
        self, driver_name: str, alias: Optional[str] = None, kwargs={}, **init_kwargs
    ) -> str:
        """Creates an instance of Selenium WebDriver.

        Like `Open Browser`, but allows passing arguments to the created
        WebDriver instance directly. This keyword should only be used if
        the functionality provided by `Open Browser` is not adequate.

        ``driver_name`` must be a WebDriver implementation name like Firefox,
        Chrome, Ie, Opera, Safari, PhantomJS, or Remote.

        The initialized WebDriver can be configured either with a Python
        dictionary ``kwargs`` or by using keyword arguments ``**init_kwargs``.
        These arguments are passed directly to WebDriver without any
        processing. See [https://seleniumhq.github.io/selenium/docs/api/py/api.html|
        Selenium API documentation] for details about the supported arguments.

        Returns the index of this browser instance which can be used later to
        switch back to it. Index starts from 1 and is reset back to it when
        `Close All Browsers` keyword is used. See `Switch Browser` for an
        example.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Create Firefox WebDriver using Proxies
                    ${proxy}=    Evaluate
                    ...    selenium.webdriver.Proxy()
                    ...    modules=selenium, selenium.webdriver
                    ${proxy.http_proxy}=    Set Variable    localhost:8888
                    Create Webdriver      Firefox           proxy=${proxy}

                *** Keyword ***
                Create PhantomJS WebDriver using Proxies
                    ${service args}=     Create List    --proxy=192.168.132.104:8888
                    Create Webdriver    PhantomJS        service_args=${service args}

        :param driver_name: must be a WebDriver implementation name
        :param alias: alias name for this WebDriver implementation
        :param kwargs: a Python dictionary ``kwargs``
        :param init_kwargs: keyword arguments
        :return: index of browser instance
        """

    @keyword
    def current_frame_should_contain(self, text: str, loglevel: str = "TRACE"):
        """Verifies that the current frame contains ``text``.

        See `Page Should Contain` for an explanation about the ``loglevel``
        argument.

        Prior to SeleniumLibrary 3.0 this keyword was named
        `Current Frame Contains`.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Is The Text On The Current Frame
                    Current Frame Should Contain
                    ...    Text I am looking for
                    ...    loglevel=WARN

        :param text: text the frame should contain
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().current_frame_should_contain(text, loglevel=loglevel)

    @keyword
    def current_frame_should_not_contain(self, text: str, loglevel: str = "TRACE"):
        """Verifies that the current frame does not contain ``text``.

        See `Page Should Contain` for an explanation about the ``loglevel``
        argument.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Text Should Not Be On The Current Frame
                    Current Frame Should Not Contain
                    ...    Text I am looking to avoid
                    ...    loglevel=NONE

        :param text: text the frame should not contain
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().current_frame_should_not_contain(text, loglevel=loglevel)

    @keyword
    def delete_all_cookies(self):
        """Deletes all cookies.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Removes All Cookies
                    Delete All Cookies
        """

        super().delete_all_cookies()

    @keyword
    def delete_cookie(self, name):
        """Deletes the cookie matching ``name``.

        If the cookie is not found, nothing happens.
        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Delete the Website Cookie
                    Delete Cookie    Google

        :param name: name of the cookie to be deleted
        """

        super().delete_cookie(name=name)

    @keyword
    def double_click_element(self, locator: Union[WebElement, str]):
        """Double clicks the element identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                The Element Must Be Clicked Twice In A Row
                    Double Click Element    id:element_locator

        :param locator: element locator
        """

        super().double_click_element(locator)

    @keyword
    def drag_and_drop(
        self, locator: Union[WebElement, str], target: Union[WebElement, str]
    ):
        """Drags the element identified by ``locator`` into the ``target`` element.

        The ``locator`` argument is the locator of the dragged element
        and the ``target`` is the locator of the target. See the
        `Locating elements` section for details about the locator syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Put This Over There
                    Drag And Drop    css:div#element    css:div.target

        :param locator: element locator
        :param target: location where the first argument ``locator`` will be dragged to
        """

        super().drag_and_drop(locator, target)

    @keyword
    def drag_and_drop_by_offset(
        self, locator: Union[WebElement, str], xoffset: int, yoffset: int
    ):
        """Drags the element identified with ``locator`` by ``xoffset/yoffset``.

        See the `Locating elements` section for details about the locator
        syntax.

        The element will be moved by ``xoffset`` and ``yoffset``, each of which
        is a negative or positive number specifying the offset.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Move myElem 50px right and 35px down
                    Drag And Drop By Offset
                    ...    myElem
                    ...    xoffset=50
                    ...    yoffset=-35

        :param locator: element locator
        :param xoffset: left and right offset from the center of the element
        :param yoffset: up and down offset from the center of the element
        """

        super().drag_and_drop_by_offset(locator, xoffset, yoffset)

    @keyword
    def element_attribute_value_should_be(
        self,
        locator: Union[WebElement, str],
        attribute: str,
        expected: Union[None, str],
        message: Optional[str] = None,
    ):
        """Verifies element identified by ``locator`` contains expected attribute value.

        See the `Locating elements` section for details about the locator
        syntax.

        New in SeleniumLibrary 3.2.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Is The Image Link What I Expect
                    Element Attribute Value Should Be
                    ...    locator=css:img
                    ...    attribute=href
                    ...    expected=value

        :param locator: element locator
        :param attribute: ``attribute`` from the element ``locator``
        :param expected: expected value of ``attribute`` from the element ``locator``
        :param message: used to override the default error message
        """

        super().element_attribute_value_should_be(
            locator, attribute, expected, message=message
        )

    @keyword
    def element_should_be_disabled(self, locator: Union[WebElement, str]):
        """Verifies that element identified by ``locator`` is disabled.

        This keyword considers also elements that are read-only to be
        disabled.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Is My Element Read Only Or Disabled
                    Element Should Be Disabled    id:element_locator

        :param locator: element locator
        """

        super().element_should_be_disabled(locator)

    @keyword
    def element_should_be_enabled(self, locator: Union[WebElement, str]):
        """Verifies that element identified by ``locator`` is enabled.

        This keyword considers also elements that are read-only to be
        disabled.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Is My Element Enabled
                    Element Should Be Enabled    id:element_locator

        :param locator: element locator
        """

        super().element_should_be_enabled(locator)

    @keyword
    def element_should_be_focused(self, locator: Union[WebElement, str]):
        """Verifies that element identified by ``locator`` is focused.

        See the `Locating elements` section for details about the locator
        syntax.

        New in SeleniumLibrary 3.0.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Is My Element In Focus
                    Element Should Be Focused    id:element_locator

        :param locator: element locator
        """

        super().element_should_be_focused(locator)

    @keyword
    def element_should_contain(
        self,
        locator: Union[WebElement, str],
        expected: Union[None, str],
        message: Optional[str] = None,
        ignore_case: bool = False,
    ):
        """Verifies that element ``locator`` contains text ``expected``.

        See the `Locating elements` section for details about the locator
        syntax.

        The ``message`` argument can be used to override the default error
        message.

        The ``ignore_case`` argument can be set to True to compare case
        insensitive, default is False. New in SeleniumLibrary 3.1.

        ``ignore_case`` argument is new in SeleniumLibrary 3.1.

        Use `Element Text Should Be` if you want to match the exact text,
        not a substring.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                I Expect The Element To Contain Some Text
                    Element Should Contain
                    ...    name=button23
                    ...    expected=robocorp
                    ...    message=This is not a Robocorp button?!?
                    ...    ignore_case=${TRUE}

        :param locator: element locator
        :param expected: text the `locator` should contain
        :param message: used to override the default error message
        :param ignore_case: set to `True` to compare case insensitive, default
         is `False`
        """

        super().element_should_contain(
            locator, expected, message=message, ignore_case=ignore_case
        )

    @keyword
    def element_should_not_be_visible(
        self, locator: Union[WebElement, str], message: Optional[str] = None
    ):
        """Verifies that the element identified by ``locator`` is NOT visible.

        Passes if the element does not exists. See `Element Should Be Visible`
        for more information about visibility and supported arguments.
        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Keep The Element Hidden From View
                    Element Should Not Be Visable
                    ...    id:element_locator
                    ...    message=I can see the element...

        :param locator: element locator
        :param message: used to override the default error message
        """

        super().element_should_not_be_visible(locator, message=message)

    @keyword
    def element_should_not_contain(
        self,
        locator: Union[WebElement, str],
        expected: Union[None, str],
        message: Optional[str] = None,
        ignore_case: bool = False,
    ):
        """Verifies that element ``locator`` does not contain text ``expected``.

        See the `Locating elements` section for details about the locator
        syntax.

        The ``message`` argument can be used to override the default error
        message.

        The ``ignore_case`` argument can be set to True to compare case
        insensitive, default is False.

        ``ignore_case`` argument new in SeleniumLibrary 3.1.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                I Expect The Element Not To Contain Some Text
                    Element Should Contain
                    ...    name=button23
                    ...    expected=manual tasks
                    ...    message=Why are we still doing things manually?!?
                    ...    ignore_case=${TRUE}

        :param locator: element locator
        :param expected: text the `locator` should not contain
        :param message: used to override the default error message
        :param ignore_case: set to `True` to compare case insensitive, default
         is `False`
        """

        super().element_should_not_contain(
            locator, expected, message=message, ignore_case=ignore_case
        )

    @keyword
    def element_text_should_be(
        self,
        locator: Union[WebElement, str],
        expected: Union[None, str],
        message: Optional[str] = None,
        ignore_case: bool = False,
    ):
        """Verifies that element ``locator`` contains exact the text ``expected``.

        See the `Locating elements` section for details about the locator
        syntax.

        The ``message`` argument can be used to override the default error
        message.

        The ``ignore_case`` argument can be set to True to compare case
        insensitive, default is False.

        ``ignore_case`` argument is new in SeleniumLibrary 3.1.

        Use `Element Should Contain` if a substring match is desired.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                I Expect The Element Text to Be Exactly The Expected
                    Element Should Contain
                    ...    name=text_field
                    ...    expected=robocorp builds great products
                    ...    message=Of course they do!
                    ...    ignore_case=${TRUE}

        :param locator: element locator
        :param expected: text the `locator` should be
        :param message: used to override the default error message
        :param ignore_case: set to `True` to compare case insensitive, default
         is `False`
        """

        super().element_text_should_be(
            locator, expected, message=message, ignore_case=ignore_case
        )

    @keyword
    def element_text_should_not_be(
        self,
        locator: Union[WebElement, str],
        not_expected: Union[None, str],
        message: Optional[str] = None,
        ignore_case: bool = False,
    ):
        """Verifies that element ``locator`` does not contain exact the text ``not_expected``.

        See the `Locating elements` section for details about the locator
        syntax.

        The ``message`` argument can be used to override the default error
        message.

        The ``ignore_case`` argument can be set to True to compare case
        insensitive, default is False.

        New in SeleniumLibrary 3.1.1

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                I Expect The Element Text to Not Be Exactly The Expected
                    Element Should Contain
                    ...    name=text_field
                    ...    expected=robocorp builds products
                    ...    message=They build robust products!
                    ...    ignore_case=${TRUE}

        :param locator: element locator
        :param not_expected: text the `locator` should not be
        :param message: used to override the default error message
        :param ignore_case: set to `True` to compare case insensitive, default
         is `False`
        """

        super().element_text_should_not_be(
            locator, not_expected, message=message, ignore_case=ignore_case
        )

    @keyword
    def execute_async_javascript(self, *code: Union[WebElement, str]) -> Any:
        """Executes asynchronous JavaScript code with possible arguments.

        Similar to `Execute Javascript` except that scripts executed with
        this keyword must explicitly signal they are finished by invoking the
        provided callback. This callback is always injected into the executed
        function as the last argument.

        Scripts must complete within the script timeout or this keyword will
        fail. See the `Timeout` section for more information.

        Starting from SeleniumLibrary 3.2 it is possible to provide JavaScript
        `arguments`_ as part of ``code`` argument. See `Execute Javascript` for
        more details.

        .. _arguments: https://seleniumhq.github.io/selenium/docs/api/py/webdriver_remote/selenium.webdriver.remote.webdriver.html#selenium.webdriver.remote.webdriver.WebDriver.execute_async_script

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Execute JavaScript With Callback
                    Execute Async JavaScript    var callback = arguments[arguments.length - 1]; window.setTimeout(callback, 2000);

                 *** Keyword ***
                Execute A JavaScript File With Callback
                    Execute Async JavaScript    ${CURDIR}/async_js_to_execute.js

                 *** Keyword ***
                Execute JavaScript With Callback And Check Result
                    ${result} =    Execute Async JavaScript
                    ...            var callback = arguments[arguments.length - 1];
                    ...            function answer(){callback("text");};
                    ...            window.setTimeout(answer, 2000);
                    Should Be Equal    ${result}    text

        :param code: the JavaScript and arguments to be executed
        :return: result of the javascript execution
        """

        super().execute_async_javascript(*code)

    @keyword
    def execute_javascript(self, *code: Union[WebElement, str]) -> Any:
        """Executes the given JavaScript code with possible arguments.

        ``code`` may be divided into multiple cells in the test data and
        ``code`` may contain multiple lines of code and arguments. In that case,
        the JavaScript code parts are concatenated together without adding
        spaces and optional arguments are separated from ``code``.

        If ``code`` is a path to an existing file, the JavaScript
        to execute will be read from that file. Forward slashes work as
        a path separator on all operating systems.

        The JavaScript executes in the context of the currently selected
        frame or window as the body of an anonymous function. Use ``window``
        to refer to the window of your application and ``document`` to refer
        to the document object of the current frame or window, e.g.
        ``document.getElementById('example')``.

        This keyword returns whatever the executed JavaScript code returns.
        Return values are converted to the appropriate Python types.

        Starting from SeleniumLibrary 3.2 it is possible to provide JavaScript
        `arguments`_ as part of ``code`` argument. The JavaScript code and
        arguments must be separated with `JAVASCRIPT` and `ARGUMENTS` markers
        and must be used exactly with this format. If the Javascript code is
        first, then the `JAVASCRIPT` marker is optional. The order of
        `JAVASCRIPT` and `ARGUMENTS` markers can be swapped, but if `ARGUMENTS`
        is the first marker, then `JAVASCRIPT` marker is mandatory. It is only
        allowed to use `JAVASCRIPT` and `ARGUMENTS` markers only one time in the
        ``code`` argument.

        .. _arguments: https://seleniumhq.github.io/selenium/docs/api/py/webdriver_remote/selenium.webdriver.remote.webdriver.html#selenium.webdriver.remote.webdriver.WebDriver.execute_script

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Executing Just JavaScript
                    Execute JavaScript    window.myFunc('arg1', 'arg2')

                *** Keyword ***
                Executing A JavaScript File
                    Execute JavaScript    ${CURDIR}/js_to_execute.js

                *** Keyword ***
                Executing JavaScript With Arguments
                    Execute JavaScript    alert(arguments[0]);    ARGUMENTS    123

                *** Keyword ***
                Executing JavaScript With Arguments Reverse Order
                    Execute JavaScript    ARGUMENTS    123    JAVASCRIPT    alert(arguments[0]);

        :param code: the JavaScript and arguments to be executed
        :return: result of the javascript execution
        """

        super().execute_javascript(*code)

    @keyword
    def frame_should_contain(
        self, locator: Union[WebElement, str], text: str, loglevel: str = "TRACE"
    ):
        """Verifies that frame identified by ``locator`` contains ``text``.

        See the `Locating elements` section for details about the locator
        syntax.

        See `Page Should Contain` for an explanation about the ``loglevel``
        argument.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Is The Text On The Current Frame
                    Frame Should Contain
                    ...    frame_locator
                    ...    Text I am looking for
                    ...    loglevel=WARN

        :param locator: element locator
        :param text: text the frame should contain
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().frame_should_contain(locator, text, loglevel=loglevel)

    @keyword
    def get_all_links(self) -> List[str]:
        """Returns a list containing ids of all links found in current page.

        If a link has no id, an empty string will be in the list instead.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Give Me A List Of All The Page Links
                    ${links)=    Get All Links

        :return: a list containing ids of all links found in current page
        """

        super().get_all_links()

    @keyword
    def get_browser_aliases(self) -> List[str]:
        """Returns aliases of all active browser that has an alias as NormalizedDict.
        The dictionary contains the aliases as keys and the index as value.
        This can be accessed as dictionary ``${aliases.key}`` or as list ``@{aliases}[0]``.

        See `Switch Browser` for more information and examples.

        New in SeleniumLibrary 4.0

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Capture Active Browsers Aliases
                    Open Browser    https://example.com    alias=BrowserA
                    Open Browser    https://example.com    alias=BrowserB
                    &{aliases}    Get Browser Aliases
                    # The dictionary of the returned Aliases
                    #  &{aliases} = { BrowserA=1|BrowserB=2 }
                    Log    ${aliases.BrowserA}    # logs ``1``
                    FOR    ${alias}    IN    @{aliases}
                        Log    ${alias}    # logs ``BrowserA`` and ``BrowserB``
                    END

        :return: aliases of all active browser that has an alias as NormalizedDict
        """

        super().get_browser_aliases()

    @keyword
    def get_browser_ids(self) -> List[str]:
        """Returns index of all active browser as list.

        See `Switch Browser` for more information and examples.

        New in SeleniumLibrary 4.0

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Capture Active Browsers IDs
                    @{browser_ids}=    Get Browser Ids
                    FOR    ${id}    IN    @{browser_ids}
                        @{window_titles}=    Get Window Titles    browser=${id}
                        Log    Browser ${id} has these windows: ${window_titles}
                    END

        :return: index of all active browser as list
        """

        super().get_browser_ids()

    @keyword
    def Get_Cookie(self, name: str) -> CookieInformation:
        """Returns information of cookie with ``name`` as an object.

        If no cookie is found with ``name``, keyword fails. The cookie object
        contains details about the cookie. Attributes available in the object
        are documented in the table below.

        +---------------+------------------------------------------------------------+
        |   Attribute   |               Explanation                                  |
        +===============+============================================================+
        | name          | The name of a cookie.                                      |
        +---------------+------------------------------------------------------------+
        | value         | Value of the cookie.                                       |
        +---------------+------------------------------------------------------------+
        | path          | Indicates a URL path, for example ``/``.                   |
        +---------------+------------------------------------------------------------+
        | domain        | The domain, the cookie is visible to.                      |
        +---------------+------------------------------------------------------------+
        | secure        | When true, the cookie is only used with HTTPS connections. |
        +---------------+------------------------------------------------------------+
        | httpOnly      | When true, the cookie is not accessible via JavaScript.    |
        +---------------+------------------------------------------------------------+
        | expiry        | Python datetime object indicating when the cookie expires. |
        +---------------+------------------------------------------------------------+
        | extra         | Possible attributes outside of the WebDriver specification |
        +---------------+------------------------------------------------------------+

        See the `WebDriver specification`_
        for details about the cookie information.
        Notice that ``expiry`` is specified as a `datetime object`_
        not as seconds since Unix Epoch like WebDriver natively does.

        .. _WebDriver specification: https://w3c.github.io/webdriver/#cookies

        .._datetime object: https://docs.python.org/3/library/datetime.html#datetime.datetime

        In some cases, example, when running a browser in the cloud, it is possible that
        the cookie contains other attributes than is defined in the
        `WebDriver specification`_.
        These other attributes are available in an ``extra`` attribute in the cookie
        object and it contains a dictionary of the other attributes. The ``extra``
        attribute is new in SeleniumLibrary 4.0.

        .. _WebDriver specification: https://w3c.github.io/webdriver/#cookies

        New in SeleniumLibrary 3.0.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Set and Retreive Cookie Values
                    Add Cookie    foo    bar
                    ${cookie}=    Get Cookie    foo
                    Should Be Equal    ${cookie.name}    foo
                    Should Be Equal    ${cookie.value}    bar
                    Should Be True    ${cookie.expiry.year} > 2017

        :param name: name of the cookie you are looking for
        :return: information of cookie with ``name`` as an object
        """

    @keyword
    def get_cookies(self, as_dict: bool = False) -> Union[str, dict]:
        """Returns all cookies of the current page.

        If ``as_dict`` argument evaluates as false, see `Boolean arguments`
        for more details, then cookie information is returned as
        a single string in format ``name1=value1; name2=value2; name3=value3``.
        When ``as_dict`` argument evaluates as true, cookie information
        is returned as Robot Framework dictionary format. The string format
        can be used, for example, for logging purposes or in headers when
        sending HTTP requests. The dictionary format is helpful when
        the result can be passed to requests library's Create Session
        keyword's optional cookies parameter.

        The `` as_dict`` argument is new in SeleniumLibrary 3.3

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Give Me Page Cookies As String
                    ${cookie_string}=    Get Cookies

                *** Keyword ***
                Give Me Page Cookies As Dict
                    ${cookie_dict}=    Get Cookies    as_dict=${TRUE}

        :param as_dict: if `True` returns cookies as a dictionary, if `False` returns
         cookies as a string, defaults to `False`
        :return: all cookies of the current page, returned as either string or dict
        """

        super().get_cookies(as_dict=as_dict)

    @keyword
    def get_element_attribute(
        self, locator: Union[WebElement, str], attribute: str
    ) -> str:
        """Returns the value of ``attribute`` from the element ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        Passing attribute name as part of the ``locator`` was removed
        in SeleniumLibrary 3.2. The explicit ``attribute`` argument
        should be used instead.
        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What Is The ID Attribute of H1
                    ${id}=    Get Element Attribute    css:h1    id

        :param locator: element locator
        :param attribute: value of ``attribute`` from the element ``locator``
        """

        super().get_element_attribute(locator, attribute)

    @keyword
    def get_element_count(self, locator: Union[WebElement, str]) -> int:
        """Returns the number of elements matching ``locator``.

        If you wish to assert the number of matching elements, use
        `Page Should Contain Element` with ``limit`` argument. Keyword will
        always return an integer.

        New in SeleniumLibrary 3.0.
        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                How Many Elements Are There
                    ${count} =    Get Element Count    name:div_name
                    Should Be True    ${count} > 2

        :param locator: element locator
        :return: number of elements matching ``locator``
        """

        super().get_element_count(locator)

    @keyword
    def get_element_size(self, locator: Union[WebElement, str]) -> Tuple[int, int]:
        """Returns width and height of the element identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        Both width and height are returned as integers.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                How Big Is This Container
                    ${width}    ${height} =    Get Element Size
                    ...    css:div#container

        :param locator: element locator
        :return: width and height of the element identified by ``locator``, as integers
        """

        super().get_element_size(locator)

    @keyword
    def get_horizontal_position(self, locator: Union[WebElement, str]) -> int:
        """Returns the horizontal position of the element identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        The position is returned in pixels off the left side of the page,
        as an integer.

        See also `Get Vertical Position`.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                How Far From The Left Side Is This Button
                ${h_distance}=    Get Horizontal Position
                ...    id:button_locator

        :param locator: element locator
        :return: pixels off the left side of the page, as an integer
        """

        super().get_horizontal_position(locator)

    @keyword
    def get_list_items(
        self, locator: Union[WebElement, str], values: bool = False
    ) -> List[str]:
        """Returns all labels or values of selection list ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        Returns visible labels by default, but values can be returned by
        setting the ``values`` argument to a true value (see `Boolean
        arguments`).

        Support to return values is new in SeleniumLibrary 3.0.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Get List Labels
                    ${labels} =    Get List Items    mylist

                *** Keyword ***
                Get List Values
                    ${values} =    Get List Items    css:#example select    values=True

        :param locator: element locator
        :param values: if `True` will return values instead of labels, default is `False`
        :return: all labels or values of selection list ``locator``
        """

        super().get_list_items(locator, values=values)

    @keyword
    def get_location(self) -> str:
        """Returns the current browser window URL.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What URL Am I On
                    ${url}=    Get Location

        :return: current browser window URL as string
        """

        super().get_location()

    @keyword
    def get_selected_list_label(self, locator: Union[WebElement, str]) -> str:
        """Returns the label of selected option from selection list ``locator``.

        If there are multiple selected options, the label of the first option
        is returned.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What is the label for this list
                    ${label}=    Get Selected List Label
                    ...    list_locator

        :param locator: element locator
        :return: the label of selected option from selection list ``locator``
        """

        super().get_selected_list_label(locator)

    @keyword
    def get_selected_list_labels(self, locator: Union[WebElement, str]) -> List[str]:
        """Returns labels of selected options from selection list ``locator``.

        Starting from SeleniumLibrary 3.0, returns an empty list if there
        are no selections. In earlier versions, this caused an error.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What are the labels for this list
                    ${labels}=    Get Selected List Labels
                    ...    list_locator

        :param locator: element locator
        :return: the labels of selected option from selection list ``locator`` as
         a list
        """

        super().get_selected_list_labels(locator)

    @keyword
    def get_selected_list_value(self, locator: Union[WebElement, str]) -> str:
        """Returns the value of selected option from selection list ``locator``.

        If there are multiple selected options, the value of the first option
        is returned.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What is the value for this list
                    ${value}=    Get Selected List Value
                    ...    list_locator

        :param locator: element locator
        :return: the value of selected option from selection list ``locator``
        """

        super().get_selected_list_value(locator)

    @keyword
    def get_selected_list_values(self, locator: Union[WebElement, str]) -> List[str]:
        """Returns values of selected options from selection list ``locator``.

        Starting from SeleniumLibrary 3.0, returns an empty list if there
        are no selections. In earlier versions, this caused an error.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What are the values for this list
                    ${values}=    Get Selected List Values
                    ...    list_locator

        :param locator: element locator
        :return: the values of selected option from selection list ``locator``
        """

        super().get_selected_list_values(locator)

    @keyword
    def get_selenium_implicit_wait(self) -> str:
        """Gets the implicit wait value used by Selenium.

        The value is returned as a human-readable string like ``1 second``.

        See the `Implicit wait` section above for more information.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What Is The Implicit Wait Used By Selenium
                    ${implicit_wait}=    Get Selenium Implicit Wait

        :return: the implicit wait value used by Selenium, returned as a string
        """

        super().get_selenium_implicit_wait()

    @keyword
    def get_selenium_speed(self) -> str:
        """Gets the delay that is waited after each Selenium command.

        The value is returned as a human-readable string like ``1 second``.

        See the `Selenium Speed` section above for more information.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                How Long Do I Wait After A Selenium Command
                    ${wait_time}=    Get Selenium Speed

        :return: delay that is waited after each Selenium command, returned as string
        """

        super().get_selenium_speed()

    @keyword
    def get_selenium_timeout(self) -> str:
        """Gets the timeout that is used by various keywords.

        The value is returned as a human-readable string like ``1 second``.

        See the `Timeout` section above for more information.
        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What Timeouts Do I Have Set
                    ${timeout}=    Get Selenium Timeout

        :return: the timeout that is used by various keywords, returned as string
        """

        super().get_selenium_timeout()

    @keyword
    def get_session_id(self) -> str:
        """Returns the currently active browser session id.

        New in SeleniumLibrary 3.2

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Get Browser Session ID
                    ${sesion_id}=    Get Session ID

        :return: active browser session id as a string
        """

        super().get_session_id()

    @keyword
    def get_source(self) -> str:
        """Returns the entire HTML source of the current page or frame.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Get HTML Source
                    ${html_source}=    Get Source

        :return: entire HTML source of the current page or frame
        """

        super().get_source()

    @keyword
    def get_table_cell(
        self,
        locator: Union[WebElement, None, str],
        row: int,
        column: int,
        loglevel: str = "TRACE",
    ) -> str:
        """Returns contents of a table cell.

        The table is located using the ``locator`` argument and its cell
        found using ``row`` and ``column``. See the `Locating elements`
        section for details about the locator syntax.

        Both row and column indexes start from 1, and header and footer
        rows are included in the count. It is possible to refer to rows
        and columns from the end by using negative indexes so that -1
        is the last row/column, -2 is the second last, and so on.

        All ``<th>`` and ``<td>`` elements anywhere in the table are
        considered to be cells.

        See `Page Should Contain` for an explanation about the ``loglevel``
        argument.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What Is The Value Of This Cell
                    Get Table Cell    table_locator    5    8

        :param locator: element locator
        :param row: row number to access (index starts from 1)
        :param column: column number to access (index starts from 1)
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        :raises ValueError: if row or column are zero values
        :raises AssertionError: if the table had less rows or columns than requested
        """

        super().get_table_cell(locator, row, column, loglevel=loglevel)

    @keyword
    def get_text(self, locator: Union[WebElement, str]) -> str:
        """Returns the text value of the element identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What Is The Text Value For This Element
                    ${text}=    Get Text    id:button_locator

        :param locator: element locator
        :return: text value of the element identified by ``locator`` as a string
        """

        super().get_text(locator)

    @keyword
    def get_title(self) -> str:
        """Returns the title of the current page.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Current Page Title
                    ${title}=    Get Title

        :return: title of the current page as string
        """

        super().get_title()

    @keyword
    def get_value(self, locator: Union[WebElement, str]) -> str:
        """Returns the value attribute of the element identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What Is The Value Attribute For This Element
                    ${value}=    Get Value    id:text_box

        :param locator: element locator
        :return: value attribute of the element identified by ``locator`` as a string
        """

        super().get_value(locator)

    @keyword
    def get_vertical_position(self, locator: Union[WebElement, str]) -> int:
        """Returns the vertical position of the element identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        The position is returned in pixels off the top of the page,
        as an integer.

        See also `Get Horizontal Position`.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                How Far From The Top Of The Screen Is This Element
                    ${v_distance}=    Get Vertical Position    id:textbox_locator

        :param locator: element locator
        :return: vertical position of the element identified by ``locator``
        """

        super().get_vertical_position(locator)

    @keyword
    def get_webelement(self, locator: Union[WebElement, str]) -> WebElement:
        """Returns the first WebElement matching the given ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Give Me The WebElement
                    ${webelement}=    Get WebElement    id:element34

        :param locator: element locator
        :return: first WebElement matching the given ``locator``
        """

        super().get_webelement(locator=locator)

    @keyword
    def get_webelements(self, locator: Union[WebElement, str]) -> List[WebElement]:
        """Returns a list of WebElement objects matching the ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        Starting from SeleniumLibrary 3.0, the keyword returns an empty
        list if there are no matching elements. In previous releases, the
        keyword failed in this case.
        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Give Me The WebElements
                    @{webelements}=    Get WebElements    id:element-common

        :param locator: element locator
        :return: list of WebElement objects matching the ``locator``
        """

        super().get_webelements(locator=locator)

    @keyword
    def get_window_handles(self, browser: str = "CURRENT") -> List[str]:
        """Returns all child window handles of the selected browser as a list.

        Can be used as a list of windows to exclude with `Select Window`.

        How to select the ``browser`` scope of this keyword, see `Get Locations`.

        Prior to SeleniumLibrary 3.0, this keyword was named `List Windows`.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What Are The Window Handles
                    ${window_handles}=    Get Window Handles    browserA

        :param browser: locator that identifies the Selenium WebDriver instance
        :return: all child window handles of the selected browser as a list
        """

        super().get_window_handles(browser)

    @keyword
    def get_window_identifiers(self, browser: str = "CURRENT") -> List:
        """Returns and logs id attributes of all windows of the selected browser.

        How to select the ``browser`` scope of this keyword, see `Get Locations`.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What Are The Window Identifiers
                    ${window_identifiers}=    Get Window Identifiers    browserB

        :param browser: locator that identifies the Selenium WebDriver instance
        :return: id attributes of all windows of the selected browser as a list
        """

        super().get_window_identifiers(browser)

    @keyword
    def get_window_names(self, browser: str = "CURRENT") -> List[str]:
        """Returns and logs names of all windows of the selected browser.

        How to select the ``browser`` scope of this keyword, see `Get Locations`.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What Are The Window Names
                    ${window_names}=    Get Window Names    browserC

        :param browser: locator that identifies the Selenium WebDriver instance
        :return: names of all windows of the selected browser as a list
        """

        super().get_window_names(browser)

    @keyword
    def get_window_position(self) -> Tuple[int, int]:
        """Returns current window position.

        The position is relative to the top left corner of the screen. Returned
        values are integers. See also `Set Window Position`.
        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Where Is The Window
                    ${x}    ${y}=    Get Window Position

        :return: the top left corner's x and y coordinate
         in relation to the top left corner of the screen as integers
        """

        super().get_window_position()

    @keyword
    def get_window_size(self, inner: bool = False) -> Tuple[float, float]:
        """Returns current window width and height as integers.

        See also `Set Window Size`.

        If ``inner`` parameter is set to True, keyword returns
        HTML DOM window.innerWidth and window.innerHeight properties.
        See `Boolean arguments` for more details on how to set boolean
        arguments. The ``inner`` is new in SeleniumLibrary 4.0.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What Is The Outer Window Size
                    ${width}    ${height}=    Get Window Size

                What is the Inner Window Size
                    ${width}    ${height}=    Get Window Size    True

        :param inner: get inner (`True`) or outer (`False`) window property, default is `False`
        :return: width and height of the window as floats
        """

        super().get_window_size(inner)

    @keyword
    def get_window_titles(self, browser: str = "CURRENT") -> List[str]:
        """Returns and logs titles of all windows of the selected browser.

        How to select the ``browser`` scope of this keyword, see `Get Locations`.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                What Are The Window Titles
                    ${window_titles}=    Get Window Titles    browserD

        :param browser: locator that identifies the Selenium WebDriver instance
        :return: titles of all windows of the selected browser as a list
        """

        super().get_window_titles(browser)

    @keyword
    def go_back(self):
        """Simulates the user clicking the back button on their browser.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Go To The Previous Page
                    Go Back
        """

        super().go_back()

    @keyword
    def handle_alert(self, action: str = ACCEPT, timeout: Optional[timedelta] = None):
        """Handles the current alert and returns its message.

        By default, the alert is accepted, but this can be controlled
        with the ``action`` argument that supports the following
        case-insensitive values:

        - ``ACCEPT``: Accept the alert i.e. press ``Ok``. Default.
        - ``DISMISS``: Dismiss the alert i.e. press ``Cancel``.
        - ``LEAVE``: Leave the alert open.

        The ``timeout`` argument specifies how long to wait for the alert
        to appear. If it is not given, the global default `timeout` is used
        instead.

        New in SeleniumLibrary 3.0.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Accept Alert
                    Handle Alert

                *** Keyword ***
                Dismiss Alert
                    Handle Alert    action=DISMISS

                *** Keyword ***
                Use Custom Timeout And Accept Alert
                    Handle Alert    timeout=10 s

                *** Keyword ***
                Use Custom Timeout And Dismiss Alert
                    Handle Alert    DISMISS           1 min

                *** Keyword ***
                Accept Alert And Get Its Message
                    ${message} =    Handle Alert

                *** Keyword ***
                Leave Alert Open And Get Its Message
                    ${message} =    Handle Alert      LEAVE

        :param action: how the alert should be handled, defaults to `ACCEPT`
        :param timeout: how long to wait for the alert to appear
        """

        super().handle_alert(action, timeout)

    @keyword
    def input_password(
        self, locator: Union[WebElement, str], password: str, clear: bool = True
    ):
        """Types the given password into the text field identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax. See `Input Text` for ``clear`` argument details.

        Difference compared to `Input Text` is that this keyword does not
        log the given password on the INFO level. Notice that if you use
        the keyword like

        | Input Password | password_field | password |

        the password is shown as a normal keyword argument. A way to avoid
        that is using variables like

        | Input Password | password_field | ${PASSWORD} |

        Please notice that Robot Framework logs all arguments using
        the TRACE level and tests must not be executed using level below
        DEBUG if the password should not be logged in any format.

        The `clear` argument is new in SeleniumLibrary 4.0. Hiding password
        logging from Selenium logs is new in SeleniumLibrary 4.2.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Input Password In Text Field
                    Input Password
                    ...    id=password_field
                    ...    password=my_secret_password

        :param locator: element locator
        :param password: password to type into the element locator
        :param clear: clear the text field before entering the password,
         defaults to `True`
        """

        super().input_password(locator, password, clear=clear)

    @keyword
    def input_text(
        self, locator: Union[WebElement, str], text: str, clear: bool = True
    ):
        """Types the given ``text`` into the text field identified by ``locator``.

        When ``clear`` is true, the input element is cleared before
        the text is typed into the element. When false, the previous text
        is not cleared from the element. Use `Input Password` if you
        do not want the given ``text`` to be logged.

        If `Selenium Grid`_
        is used and the ``text`` argument points to a file in the file system,
        then this keyword prevents the Selenium to transfer the file to the
        Selenium Grid hub. Instead, this keyword will send the ``text`` string
        as is to the element. If a file should be transferred to the hub and
        upload should be performed, please use `Choose File` keyword.

        .. _Selenium Grid: https://github.com/SeleniumHQ/selenium/wiki/Grid2

        See the `Locating elements` section for details about the locator
        syntax. See the `Boolean arguments` section how Boolean values are
        handled.

        Disabling the file upload the Selenium Grid node and the `clear`
        argument are new in SeleniumLibrary 4.0

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Input Text Into Text Field
                    Input Text
                    ...    id=text_field
                    ...    Text I would like to enter

        :param locator: element locator
        :param text: what is typed into the element locator
        :param clear: When `True`, the input element is cleared before
        the text is typed into the element, default is `True`
        """

        super().input_text(locator, text, clear=clear)

    @keyword
    def input_text_into_alert(
        self, text: str, action: str = ACCEPT, timeout: Optional[timedelta] = None
    ):
        """Types the given ``text`` into an input field in an alert.

        The alert is accepted by default, but that behavior can be controlled
        by using the ``action`` argument same way as with `Handle Alert`.

        ``timeout`` specifies how long to wait for the alert to appear.
        If it is not given, the global default `timeout` is used instead.

        New in SeleniumLibrary 3.0.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Add Text To Alert
                    Input Text Into Alert    Why add text to an alert?    action=ACCEPT    timeout=30s

        :param text: alert message text
        :param action: additional alert actions can be found
         in the ``Handle Alert`` keyword, defaults to `ACCEPT`
        :param timeout: how long to wait for the alert to appear
        """

        super().input_text_into_alert(text, action=action, timeout=timeout)

    @keyword
    def list_selection_should_be(self, locator: Union[WebElement, str], *expected: str):
        """Verifies selection list ``locator`` has ``expected`` options selected.

        It is possible to give expected options both as visible labels and
        as values. Starting from SeleniumLibrary 3.0, mixing labels and
        values is not possible. Order of the selected options is not
        validated.

        If no expected options are given, validates that the list has
        no selections. A more explicit alternative is using `List Should
        Have No Selections`.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Select Just One
                    List Selection Should Be    gender    Female

                *** Keyword ***
                Select Two
                    List Selection Should Be    interests    Test Automation    Python

        :param locator: element locator
        :param expected: visible labels or values. mixing labels and values is
         not possible
        :raises AssertionError: if the selection was different than ``expected``
        """

        super().list_selection_should_be(locator, *expected)

    @keyword
    def list_should_have_no_selections(self, locator: Union[WebElement, str]):
        """Verifies selection list ``locator`` has no options selected.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                None Of The Above Please
                    List Should Have No Selections    list_locator

        :param locator: element locator
        :raises AssertionError: if the list has a selection
        """

        super().list_should_have_no_selections(locator)

    @keyword
    def location_should_be(self, url: str, message: Optional[str] = None):
        """Verifies that the current URL is exactly ``url``.

        The ``url`` argument contains the exact url that should exist in browser.

        The ``message`` argument can be used to override the default error
        message.

        ``message`` argument is new in SeleniumLibrary 3.2.0.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Is My URL The Same
                    Location Should Be
                    ...    https://robocorp.com/docs/libraries/rpa-framework/rpa-browser-selenium
                    ...    message=You are not on the Robocorp Selenium Docs page!

        :param url: contains the exact url that should exist in browser
        :param message: used to override the default error message
        """

        super().location_should_be(url=url, message=message)

    @keyword
    def location_should_contain(self, expected: str, message: Optional[str] = None):
        """Verifies that the current URL contains ``expected``.

        The ``expected`` argument contains the expected value in url.

        The ``message`` argument can be used to override the default error
        message.

        ``message`` argument is new in SeleniumLibrary 3.2.0.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Should Be On The Robocorp Site
                    Location Should Contain
                    ...    robocorp.com
                    ...    message=This is not the Robocorp site!

        :param expected: expected value in url
        :param message: used to override the default error message
        """

        super().location_should_contain(expected=expected, message=message)

    @keyword
    def log_location(self) -> str:
        """Logs and returns the current browser window URL.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Log And Tell Me Where I Am
                    ${url}=    Log Location

        :return: current browser window URL
        """

        super().log_location()

    @keyword
    def log_source(self, loglevel: str = "INFO") -> str:
        """Logs and returns the HTML source of the current page or frame.

        The ``loglevel`` argument defines the used log level. Valid log
        levels are ``WARN``, ``INFO`` (default), ``DEBUG``, ``TRACE``
        and ``NONE`` (no logging).

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Log And Tell Me The Source
                    ${source}=    Log Source

        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        :return: HTML source of the current page or frame
        """

        super().log_source(loglevel=loglevel)

    @keyword
    def log_title(self) -> str:
        """Logs and returns the title of the current page.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Log And Tell Me The Title
                    ${title}=    Log Title

        :return: title of the current page as string
        """

        super().log_title()

    @keyword
    def maximize_browser_window(self):
        """Maximizes current browser window.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Make The Browser Window BIG
                    Maximize Browser Window
        """

        super().maximize_browser_window()

    @keyword
    def mouse_down(self, locator: Union[WebElement, str]):
        """Simulates pressing the left mouse button on the element ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        The element is pressed without releasing the mouse button.

        See also the more specific keywords `Mouse Down On Image` and
        `Mouse Down On Link`.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Hold The Left Mouse Button Down
                    Mouse Down    id:button_locator

        :param locator: element locator
        """

        super().mouse_down(locator)

    @keyword
    def mouse_down_on_image(self, locator: Union[WebElement, str]):
        """Simulates a mouse down event on an image identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax. When using the default locator strategy, images are searched
        using ``id``, ``name``, ``src`` and ``alt``.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Simulate Mouse Down Event On Image
                    Mouse Down On Image    id:image_locator

        :param locator: element locator
        """

        super().mouse_down_on_image(locator)

    @keyword
    def mouse_down_on_link(self, locator: Union[WebElement, str]):
        """Simulates a mouse down event on a link identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax. When using the default locator strategy, links are searched
        using ``id``, ``name``, ``href`` and the link text.
        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Mouse Down Event on Link
                    Mouse Down On Link    id:link_locator

        :param locator: element locator
        """

        super().mouse_down_on_link(locator)

    @keyword
    def mouse_out(self, locator: Union[WebElement, str]):
        """Simulates moving the mouse away from the element ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Move Away From The Scary Element
                    Mouse Out    id:scary_element_locator

        :param locator: element locator
        """

        super().mouse_out(locator)

    @keyword
    def mouse_over(self, locator: Union[WebElement, str]):
        """Simulates hovering the mouse over the element ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Show Me That Hover Text
                    Mouse Over    id:scary_element_locator

        :param locator: element locator
        """

        super().mouse_out(locator)

    @keyword
    def mouse_up(self, locator: Union[WebElement, str]):
        """Simulates releasing the left mouse button on the element ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Let The Left Mouse Button Go
                    Mouse Up    id:element_locator

        :param locator: element locator
        """

        super().mouse_up(locator)

    @keyword
    def open_context_menu(self, locator: Union[WebElement, str]):
        """Opens the context menu on the element identified by ``locator``.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Let Us Expand The Current Menu
                    Open Context Menu    id:element_locator
        """

        super().open_context_menu(locator)

    @keyword
    def page_should_contain(
        self,
        text: str,
        loglevel: str = "TRACE",
    ):
        """Verifies that current page contains ``text``.

        If this keyword fails, it automatically logs the page source
        using the log level specified with the optional ``loglevel``
        argument. Valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``. If the log level is ``NONE`` or below
        the current active log level the source will not be logged.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Look For Text On Page
                    Page Should Contain
                    ...    This is my text
                    ...    loglevel=DEBUG

        :param text: text the page should contain
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_contain(text, loglevel=loglevel)

    @keyword
    def page_should_contain_checkbox(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies checkbox ``locator`` is found from the current page.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Confirm Checkbox On Page
                    Page Should Contain Checkbox
                    ...    id:checkbox_locator

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_contain_checkbox(
            locator, message=message, loglevel=loglevel
        )

    @keyword
    def page_should_contain_element(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
        limit: Optional[int] = None,
    ):
        """Verifies that element ``locator`` is found on the current page.

        See the `Locating elements` section for details about the locator
        syntax.

        The ``message`` argument can be used to override the default error
        message.

        The ``limit`` argument can used to define how many elements the
        page should contain. When ``limit`` is ``None`` (default) page can
        contain one or more elements. When limit is a number, page must
        contain same number of elements.

        See `Page Should Contain` for an explanation about the ``loglevel``
        argument.

        The ``limit`` argument is new in SeleniumLibrary 3.0.

        **Example** (assumes that locator matches to two elements)

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Look For One Element On Page
                    `Page Should Contain Element`    div_name    limit=1       # Keyword fails.

                *** Keyword ***
                Look For Two Elements On Page
                    `Page Should Contain Element`    div_name    limit=2       # Keyword passes.

                *** Keyword ***
                Look For One Or More Elements On Page
                    `Page Should Contain Element`    div_name    limit=none    # None is considered one or more.

                *** Keyword ***
                Look For Element On Page With Default Arguments
                    `Page Should Contain Element`    div_name    # Same as above.

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        :param limit: used to define how many elements the page should contain
        """

        super().page_should_contain_element(
            locator, message=message, loglevel=loglevel, limit=limit
        )

    @keyword
    def page_should_contain_image(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies image identified by ``locator`` is found from current page.

        See the `Locating elements` section for details about the locator
        syntax. When using the default locator strategy, images are searched
        using ``id``, ``name``, ``src`` and ``alt``.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Looking For An Image With Default Message and Loglevel
                    Page Should Contain Image    id:image_locator

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_contain_image(locator, message=message, loglevel=loglevel)

    @keyword
    def page_should_contain_link(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies link identified by ``locator`` is found from current page.

        See the `Locating elements` section for details about the locator
        syntax. When using the default locator strategy, links are searched
        using ``id``, ``name``, ``href`` and the link text.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Looking For A Link With Default Message and Loglevel
                    Page Should Contain Link    id:link_locator

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_contain_link(locator, message=message, loglevel=loglevel)

    @keyword
    def page_should_contain_list(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies selection list ``locator`` is found from current page.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Looking For A List On A Page With Default Message and Loglevel
                    Page Should Contain List    id:list_locator

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_contain_list(locator, message=message, loglevel=loglevel)

    @keyword
    def page_should_contain_radio_button(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies radio button ``locator`` is found from current page.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        See the `Locating elements` section for details about the locator
        syntax. When using the default locator strategy, radio buttons are
        searched using ``id``, ``name`` and ``value``.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Radio Button Should Be On Page
                    Page Should Contain Radio Button
                    ...    name=radio_button
                    ...    message=My Error Message!

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_contain_radio_button(
            locator, message=message, loglevel=loglevel
        )

    @keyword
    def page_should_contain_textfield(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies text field ``locator`` is found from current page.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Textfield Should Be On Page
                    Page Should Contain Textfield
                    ...    id=TextField
                    ...    message=This is my error message
                    ...    loglevel=DEBUG

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_contain_textfield(
            locator, message=message, loglevel=loglevel
        )

    @keyword
    def page_should_not_contain(self, text: str, loglevel: str = "TRACE"):
        """Verifies the current page does not contain ``text``.

        See `Page Should Contain` for an explanation about the ``loglevel``
        argument.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                I Do Not Want To See This Text
                    Page Should Not Contain    manual tasks

        :param text: text the page should not contain
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_not_contain(text, loglevel=loglevel)

    @keyword
    def page_should_not_contain_button(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies button ``locator`` is not found from current page.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        See the `Locating elements` section for details about the locator
        syntax. When using the default locator strategy, buttons are
        searched using ``id``, ``name``, and ``value``.
        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Button Should Not Be On Page
                    Page Should Not Contain Button
                    ...    id=Button
                    ...    message=This is my message

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_not_contain_button(
            locator, message=message, loglevel=loglevel
        )

    @keyword
    def page_should_not_contain_checkbox(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies checkbox ``locator`` is not found from the current page.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Confirm No Checkbox On Page
                    Page Should Not Contain Checkbox
                    ...    id:checkbox_locator

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_not_contain_checkbox(
            locator, message=message, loglevel=loglevel
        )

    @keyword
    def page_should_not_contain_element(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies that element ``locator`` is not found on the current page.

        See the `Locating elements` section for details about the locator
        syntax.

        See `Page Should Contain` for an explanation about ``message`` and
        ``loglevel`` arguments.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Confirm This Element Is Not On Page
                    Page Should Not Contain Element
                    ...    id:element_locator
                    ...    message=I found the element
                    ...    loglevel=DEBUG

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_not_contain_element(
            locator, message=message, loglevel=loglevel
        )

    @keyword
    def page_should_not_contain_image(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies image identified by ``locator`` is not found from current page.

        See the `Locating elements` section for details about the locator
        syntax. When using the default locator strategy, images are searched
        using ``id``, ``name``, ``src`` and ``alt``.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Not Looking For An Image With Default Message and Loglevel
                    Page Should Not Contain Image    id:image_locator

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_not_contain_image(
            locator, message=message, loglevel=loglevel
        )

    @keyword
    def page_should_not_contain_link(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies link identified by ``locator`` is not found from current page.

        See the `Locating elements` section for details about the locator
        syntax. When using the default locator strategy, links are searched
        using ``id``, ``name``, ``href`` and the link text.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Not Looking For A Link With Default Message and Loglevel
                    Page Should Not Contain Link    id:link_locator

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_not_contain_link(
            locator, message=message, loglevel=loglevel
        )

    @keyword
    def page_should_not_contain_list(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies selection list ``locator`` is not found from current page.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Not Looking For A List On A Page With Default Message and Loglevel
                    Page Should Not Contain List    id:list_locator

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_not_contain_list(
            locator, message=message, loglevel=loglevel
        )

    @keyword
    def page_should_not_contain_radio_button(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies radio button ``locator`` is not found from current page.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        See the `Locating elements` section for details about the locator
        syntax. When using the default locator strategy, radio buttons are
        searched using ``id``, ``name`` and ``value``.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Radio Button Should Not Be On Page
                    Page Should Not Contain Radio Button
                    ...    name=radio_button
                    ...    message=My Error Message!

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_not_contain_radio_button(
            locator, message=message, loglevel=loglevel
        )

    @keyword
    def page_should_not_contain_textfield(
        self,
        locator: Union[WebElement, str],
        message: Optional[str] = None,
        loglevel: str = "TRACE",
    ):
        """Verifies text field ``locator`` is not found from current page.

        See `Page Should Contain Element` for an explanation about ``message``
        and ``loglevel`` arguments.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Textfield Should Not Be On Page
                    Page Should Not Contain Textfield
                    ...    id=TextField
                    ...    message=This is my error message
                    ...    loglevel=DEBUG

        :param locator: element locator
        :param message: used to override the default error message
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        """

        super().page_should_not_contain_textfield(
            locator, message=message, loglevel=loglevel
        )

    @keyword
    def press_key(self, locator: Union[WebElement, str], key: str):
        """*DEPRECATED in SeleniumLibrary 4.0.* use `Press Keys` instead.

        :param locator: element locator
        :param key: the key to be typed or selected on the user's keyboard
        """

        super().press_key(locator, key)

    @keyword
    def press_keys(self, locator: Union[WebElement, None, str] = None, *keys: str):
        """Simulates the user pressing key(s) to an element or on the active browser.

        If ``locator`` evaluates as false, see `Boolean arguments` for more
        details, then the ``keys`` are sent to the currently active browser.
        Otherwise element is searched and ``keys`` are send to the element
        identified by the ``locator``. In later case, keyword fails if element
        is not found. See the `Locating elements` section for details about
        the locator syntax.

        ``keys`` arguments can contain one or many strings, but it can not
        be empty. ``keys`` can also be a combination of `Selenium Keys`_
        and strings or a single Selenium Key. If Selenium Key is combined
        with strings, Selenium key and strings must be separated by the
        `+` character, like in `CONTROL+c`. Selenium Keys
        are space and case sensitive and Selenium Keys are not parsed
        inside of the string. Example AALTO, would send string `AALTO`
        and `ALT` not parsed inside of the string. But `A+ALT+O` would
        found Selenium ALT key from the ``keys`` argument. It also possible
        to press many Selenium Keys down at the same time, example
        'ALT+ARROW_DOWN`.

        .. _Selenium Keys: https://seleniumhq.github.io/selenium/docs/api/py/webdriver/selenium.webdriver.common.keys.html

        If Selenium Keys are detected in the ``keys`` argument, keyword
        will press the Selenium Key down, send the strings and
         then release the Selenium Key. If keyword needs to send a Selenium
        Key as a string, then each character must be separated with
        `+` character, example `E+N+D`.

        `CTRL` is alias for `Selenium CONTROL`_
        and ESC is alias for `Selenium ESCAPE`_

        .. _Selenium CONTROL: https://seleniumhq.github.io/selenium/docs/api/py/webdriver/selenium.webdriver.common.keys.html#selenium.webdriver.common.keys.Keys.CONTROL
        .. _Selenium ESCAPE: https://seleniumhq.github.io/selenium/docs/api/py/webdriver/selenium.webdriver.common.keys.html#selenium.webdriver.common.keys.Keys.ESCAPE

        New in SeleniumLibrary 3.3

        **Examples**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Sends string AAAAA to element
                    Press Keys    text_field    AAAAA

                *** Keyword ***
                Sends string BBBBB to currently active browser
                    Press Keys    None    BBBBB

                *** Keyword ***
                Sends string END to element
                    Press Keys    text_field    E+N+D

                *** Keyword ***
                Sends strings XXX and YY to element
                    Press Keys    text_field    XXX    YY

                *** Keyword ***
                Same as above
                    Press Keys    text_field    XXX+YY

                *** Keyword ***
                Pressing ALT key down, then pressing ARROW_DOWN and then releasing both keys
                    Press Keys    text_field    ALT+ARROW_DOWN

                *** Keyword ***
                Pressing ALT key and then pressing ARROW_DOWN
                    Press Keys    text_field    ALT    ARROW_DOWN

                *** Keyword ***
                Pressing CTRL key down, sends string c and then releases CTRL key
                    Press Keys    text_field    CTRL+c

                *** Keyword ***
                Pressing ENTER key to element
                    Press Keys    button    RETURN

        :param locator: element locator
        :param keys: the keys to be typed or selected on the user's keyboard
        """

        super().press_keys(locator, keys)

    @keyword
    def radio_button_should_be_set_to(self, group_name: str, value: str):
        """Verifies radio button group ``group_name`` is set to ``value``.

        ``group_name`` is the ``name`` of the radio button group.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Select Email Button
                    Select Radio Button
                    ...    group_name=contact
                    ...    value=email

        :parma group_name: name of the radio button group
        :param value: the ``value`` attribute of the radio
         button that should be set
        """

        super().radio_button_should_be_set_to(group_name, value)

    @keyword
    def radio_button_should_not_be_selected(self, group_name: str):
        """Verifies radio button group ``group_name`` has no selection.

        ``group_name`` is the ``name`` of the radio button group.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Make Sure Anything Else Is Chosen
                    Radio Button Should Not Be Selected    uncontacted

        :parma group_name: name of the radio button group
        """

        super().radio_button_should_not_be_selected(group_name)

    @keyword
    def register_keyword_to_run_on_failure(self, keyword: Optional[str]) -> str:
        """Sets the keyword to execute, when a SeleniumLibrary keyword fails.

        ``keyword`` is the name of a keyword that will be executed if a
        SeleniumLibrary keyword fails. It is possible to use any available
        keyword, including user keywords or keywords from other libraries,
        but the keyword must not take any arguments.

        The initial keyword to use is set when `importing` the library, and
        the keyword that is used by default is `Capture Page Screenshot`.
        Taking a screenshot when something failed is a very useful
        feature, but notice that it can slow down the execution.

        It is possible to use string ``NOTHING`` or ``NONE``,
        case-insensitively, as well as Python ``None`` to disable this
        feature altogether.

        This keyword returns the name of the previously registered
        failure keyword or Python ``None`` if this functionality was
        previously disabled. The return value can be always used to
        restore the original value later.

        Changes in SeleniumLibrary 3.0:
        - Possible to use string ``NONE`` or Python ``None`` to disable the
          functionality.
        - Return Python ``None`` when the functionality was disabled earlier.
          In previous versions special value ``No Keyword`` was returned and
          it could not be used to restore the original state.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Setting And Reverting The Failure Keyword
                    Register Keyword To Run On Failure    Log Source
                    ${previous kw}=    Register Keyword To Run On Failure    NONE
                    Register Keyword To Run On Failure    ${previous kw}

        :param keyword: the name of a keyword that will be executed if a
        SeleniumLibrary keyword fails
        :return: the name of the previously registered
        failure keyword or Python ``None`` if this functionality was
        previously disabled
        """

        super().register_keyword_to_run_on_failure(keyword)

    @keyword
    def reload_page(self):
        """Simulates user reloading page.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Page Refresh
                    Reload Page
        """

        super().reload_page()

    @keyword
    def remove_location_strategy(self, strategy_name: str):
        """Removes a previously added custom location strategy.

        See `Custom locators` for information on how to create and use
        custom strategies.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Get Rid Of Persistent Location Strategy
                    Remove Location Strategy    extJs

        :param strategy_name: previously added custom location strategy
        """

        super().remove_location_strategy(strategy_name)

    @keyword
    def scroll_element_into_view(self, locator: Union[WebElement, str]):
        """Scrolls the element identified by ``locator`` into view.

        See the `Locating elements` section for details about the locator
        syntax.

        New in SeleniumLibrary 3.2.0

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                You Can Not Hide
                    Scroll Element Into View    id:element_locator

        :param locator: element locator
        """

        super().scroll_element_into_view(locator)

    @keyword
    def select_all_from_list(self, locator: Union[WebElement, str]):
        """Selects all options from multi-selection list ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Select All From A Multi-Selection List
                    Select All From List    list_locator

        :param locator: element locator
        :raises RuntimeError: if ``locator`` is not a multi-selection list
        """

        super().select_all_from_list(locator)

    @keyword
    def select_checkbox(self, locator: Union[WebElement, str]):
        """Selects the checkbox identified by ``locator``.

        Does nothing if checkbox is already selected.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Mark The Checkbox
                    Select Checkbox    id=checkbox_locator

        :param locator: element locator
        """

        super().select_checkbox(locator)

    @keyword
    def select_frame(self, locator: Union[WebElement, str]):
        """Sets frame identified by ``locator`` as the current frame.

        See the `Locating elements` section for details about the locator
        syntax.

        Works both with frames and iframes. Use `Unselect Frame` to cancel
        the frame selection and return to the main frame.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Changing Frames
                    Select Frame    top-frame    # Select frame with id or name 'top-frame'
                    Click Link    example    # Click link 'example' in the selected frame
                    Unselect Frame    # Back to main frame.
                    Select Frame    //iframe[@name='xxx']    # Select frame using xpath

        :param locator: element locator
        """

        super().select_frame(locator)

    @keyword
    def select_from_list_by_index(self, locator: Union[WebElement, str], *indexes: str):
        """Selects options from selection list ``locator`` by ``indexes``.

        Indexes of list options start from 0.

        If more than one option is given for a single-selection list,
        the last value will be selected. With multi-selection lists all
        specified options are selected, but possible old selections are
        not cleared.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                This will take the last index
                    Select From List By Index
                    ...    single_selection_list_locator
                    ...    0 4 6 8

                *** Keyword ***
                This will read in all indexes
                    Select From List By Index
                    ...    multi_selection_list_locator
                    ...    0 4 6 8

        :param locator: element locator
        :param indexes: one or more options from selection list
        :raises ValueError: if no idexes is given
        """

        super().select_from_list_by_index(locator, *indexes)

    @keyword
    def select_from_list_by_label(self, locator: Union[WebElement, str], *labels: str):
        """Selects options from selection list ``locator`` by ``labels``.

        If more than one option is given for a single-selection list,
        the last value will be selected. With multi-selection lists all
        specified options are selected, but possible old selections are
        not cleared.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                This will take the last label
                    Select From List By Label
                    ...    single_selection_list_locator
                    ...    DE CT MD NH

                *** Keyword ***
                This will read in all labels
                    Select From List By Label
                    ...    multi_selection_list_locator
                    ...    DE CT MD NH

        :param locator: element locator
        :param indexes: one or more options from selection list
        :raises ValueError: if no label is given
        """

        super().select_from_list_by_label(locator, *indexes)

    @keyword
    def select_from_list_by_value(self, locator: Union[WebElement, str], *values: str):
        """Selects options from selection list ``locator`` by ``values``.

        If more than one option is given for a single-selection list,
        the last value will be selected. With multi-selection lists all
        specified options are selected, but possible old selections are
        not cleared.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                This will take the last value
                    Select From List By Value
                    ...    single_selection_list_locator
                    ...    Delaware Connecticut Maryland New Hampshire

                *** Keyword ***
                This will read in all values
                    Select From List By Value
                    ...    multi_selection_list_locator
                    ...    Delaware Connecticut Maryland New Hampshire

        :param locator: element locator
        :param indexes: one or more options from selection list
        :raises ValueError: if no value is given
        """

        super().select_from_list_by_value(locator, *indexes)

    @keyword
    def select_radio_button(self, group_name: str, value: str):
        """Sets the radio button group ``group_name`` to ``value``.

        The radio button to be selected is located by two arguments:
        - ``group_name`` is the name of the radio button group.
        - ``value`` is the ``id`` or ``value`` attribute of the actual
          radio button.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Select XL Size Button
                    Select Radio Button    size    XL

                *** Keyword ***
                Select Email Button
                    Select Radio Button    contact    email

        :parma group_name: name of the radio button group
        :param value: the ``id`` or ``value`` attribute of the actual radio button
        """

        super().select_radio_button(group_name, value)

    @keyword
    def set_browser_implicit_wait(self, value: timedelta):
        """Sets the implicit wait value used by Selenium.

        Same as `Set Selenium Implicit Wait` but only affects the current
        browser.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Update Just This Browser's Implicit Wait
                    Set Browser Implicit Wait    15 seconds

        :param value: the implicit wait value used by Selenium
        """

        super().set_browser_implicit_wait(value=value)

    @keyword
    def set_focus_to_element(self, locator: Union[WebElement, str]):
        """Sets the focus to the element identified by ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        Prior to SeleniumLibrary 3.0 this keyword was named `Focus`.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                I Want To See This Element Better
                    Set Focus To Element    id:image_locator

        :param locator: element locator
        """

        super().set_focus_to_element(locator)

    @keyword
    def set_screenshot_directory(self, path: Union[None, str]) -> str:
        """Sets the directory for captured screenshots.

        ``path`` argument specifies the absolute path to a directory where
        the screenshots should be written to. If the directory does not
        exist, it will be created. The directory can also be set when
        `importing` the library. If it is not configured anywhere,
        screenshots are saved to the same directory where Robot Framework's
        log file is written.

        If ``path`` equals to EMBED (case insensitive) and
        `Capture Page Screenshot` or `capture Element Screenshot` keywords
        filename argument is not changed from the default value, then
        the page or element screenshot is embedded as Base64 image to
        the log.html.

        The previous value is returned and can be used to restore
        the original value later if needed.

        Returning the previous value is new in SeleniumLibrary 3.0.
        The persist argument was removed in SeleniumLibrary 3.2 and
        EMBED is new in SeleniumLibrary 4.2.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Set A New Screenshot Directory
                    ${old_directory}=    Set Screenshot Directory
                    ...    ${OUTPUT_DIR}${/}new_images_folder

                *** Keyword ***
                Reset Screenshot Directory
                    Set Screenshot Directory    ${old_directory}

        :param path: specifies the absolute path to a directory where
        the screenshots should be written to
        :return: previous value
        """

        super().set_screenshot_directory(path)

    @keyword
    def set_selenium_implicit_wait(self, value: timedelta) -> str:
        """Sets the implicit wait value used by Selenium.

        The value can be given as a number that is considered to be
        seconds or as a human-readable string like ``1 second``.
        The previous value is returned and can be used to restore
        the original value later if needed.

        This keyword sets the implicit wait for all opened browsers.
        Use `Set Browser Implicit Wait` to set it only to the current
        browser.

        See the `Implicit wait` section above for more information.


        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Update Selenium Implict Wait
                    ${orig wait}=    Set Selenium Implicit Wait    10 seconds
                    Perform AJAX call that is slow
                    Set Selenium Implicit Wait    ${orig wait}

        :param value: the implicit wait value used by Selenium
        :return: previous implicit wait used by Selenium, returned as a string
        """

        super().set_selenium_implicit_wait(value=value)

    @keyword
    def set_selenium_speed(self, value: timedelta) -> str:
        """Sets the delay that is waited after each Selenium command.

        The value can be given as a number that is considered to be
        seconds or as a human-readable string like ``1 second``.
        The previous value is returned and can be used to restore
        the original value later if needed.

        See the `Selenium Speed` section above for more information.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Update Selenium Wait After Each Command
                    ${old_selenium_speed}=    Set Selenium Speed    0.5 seconds

        :param value: the delay that is waited after each Selenium command
        :return: previous Selenium speed value, returned as a string
        """

        super().set_selenium_speed(value=value)

    @keyword
    def set_selenium_timeout(self, value: timedelta) -> str:
        """Sets the timeout that is used by various keywords.

        The value can be given as a number that is considered to be
        seconds or as a human-readable string like ``1 second``.
        The previous value is returned and can be used to restore
        the original value later if needed.

        See the `Timeout` section above for more information.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Update Selenium Timeout Used By Keywords
                    ${orig timeout}=    Set Selenium Timeout    15 seconds
                    Open page that loads slowly
                    Set Selenium Timeout    ${orig timeout}

        :param value: the timeout that is used by various keywords
        :return: previous Selenium timeout value, returned as a string
        """

        super().set_selenium_timeout(value=value)

    @keyword
    def set_window_position(self, x: int, y: int):
        """Sets window position using ``x`` and ``y`` coordinates.

        The position is relative to the top left corner of the screen,
        but some browsers exclude possible task bar set by the operating
        system from the calculation. The actual position may thus be
        different with different browsers.

        Values can be given using strings containing numbers or by using
        actual numbers. See also `Get Window Position`.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Reposition Window
                    Set Window Position    100    200

        :param x: new left to right position on the screen in relation to the top
         left corner of the screen
        :param y: new up and down position on the screen in relation to the top
         left corner of the screen
        """

        super().set_window_position()

    @keyword
    def set_window_size(self, width: int, height: int, inner: bool = False):
        """Sets current windows size to given ``width`` and ``height``.

        Values can be given using strings containing numbers or by using
        actual numbers. See also `Get Window Size`.

        Browsers have a limit on their minimum size. Trying to set them
        smaller will cause the actual size to be bigger than the requested
        size.

        If ``inner`` parameter is set to True, keyword sets the necessary
        window width and height to have the desired HTML DOM _window.innerWidth_
        and _window.innerHeight_. See `Boolean arguments` for more details on how to set boolean
        arguments.

        The ``inner`` argument is new since SeleniumLibrary 4.0.

        This ``inner`` argument does not support Frames. If a frame is selected,
        switch to default before running this.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Set Outer Window Size
                    Set Window Size
                    ...    width=500
                    ...    height=900

                *** Keyword ***
                Set Inner Window Size
                    Set Window Size
                    ...    width=500
                    ...    height=900
                    ...    inner=${TRUE}

        :param width: new window width
        :param height: new window height
        :param inner: set inner (`True`) or outer (`False`) window property, default is `False`
        :raises AssertionError: if keyword fails to set the correct window size
        """

        super().set_window_size(width=width, height=height, inner=inner)

    @keyword
    def simulate_event(self, locator: Union[WebElement, str], event: str):
        """Simulates ``event`` on the element identified by ``locator``.

        This keyword is useful if element has ``OnEvent`` handler that
        needs to be explicitly invoked.

        See the `Locating elements` section for details about the locator
        syntax.

        Prior to SeleniumLibrary 3.0 this keyword was named `Simulate`.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Envoke OnEvent Handler
                    Simulate Event
                    ...    id:element_locator
                    ...    onfocus

        :param locator: element locator
        :param event: the HTML5 event that is to be simulated
        """

        super().simulate_event(locator, event)

    @keyword
    def submit_form(self, locator: Union[WebElement, None, str] = None):
        """Submits a form identified by ``locator``.

        If ``locator`` is not given, first form on the page is submitted.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Send Form To Robocorp
                    Submit Form    id=form_locator

        :param locator: element locator
        """

        super().submit_form(locator)

    @keyword
    def switch_browser(self, index_or_alias: str):
        """Switches between active browsers using ``index_or_alias``.

        Indices are returned by the `Open Browser` keyword and aliases can
        be given to it explicitly. Indices start from 1.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Switch Between Browsers
                    [Documentation]    The first example below expects that
                    ...    there is no other open browsers when opening the
                    ...    first one because it used index ``1`` when
                    ...    switching to it later.

                    Open Browser    http://google.com    ff
                    Location Should Be    http://google.com
                    Open Browser    http://yahoo.com    ie    alias=second
                    Location Should Be    http://yahoo.com
                    Switch Browser    1    # index
                    Page Should Contain    I'm feeling lucky
                    Switch Browser    second    # alias
                    Page Should Contain    More Yahoo!
                    Close All Browsers

                    # If you are not sure about that, you can store the index
                    # into a variable as below.

                    ${index} =    Open Browser    http://google.com
                    # Do something ...
                    Switch Browser    ${index}

        :param index_or_alias: index or alias assigned to the browser upon opening
        """

        super().switch_browser(index_or_alias)

    @keyword
    def switch_window(
        self,
        locator: Union[list, str] = "MAIN",
        timeout: Optional[str] = None,
        browser: str = "CURRENT",
    ):
        """Switches to browser window matching ``locator``.

        If the window is found, all subsequent commands use the selected
        window, until this keyword is used again. If the window is not
        found, this keyword fails. The previous windows handle is returned
        and can be used to switch back to it later.

        Notice that alerts should be handled with
        `Handle Alert` or other alert related keywords.

        The ``locator`` can be specified using different strategies somewhat
        similarly as when `locating elements` on pages.

        - By default, the ``locator`` is matched against window handle, name,
          title, and URL. Matching is done in that order and the first
          matching window is selected.

        - The ``locator`` can specify an explicit strategy by using the format
          ``strategy:value`` (recommended) or ``strategy=value``. Supported
          strategies are ``name``, ``title``, and ``url``. These matches windows
          using their name, title, or URL, respectively. Additionally, ``default``
          can be used to explicitly use the default strategy explained above.

        - If the ``locator`` is ``NEW`` (case-insensitive), the latest
          opened window is selected. It is an error if this is the same
          as the current window.

        - If the ``locator`` is ``MAIN`` (default, case-insensitive),
          the main window is selected.

        - If the ``locator`` is ``CURRENT`` (case-insensitive), nothing is
          done. This effectively just returns the current window handle.

        - If the ``locator`` is not a string, it is expected to be a list
          of window handles _to exclude_. Such a list of excluded windows
          can be got from `Get Window Handles` before doing an action that
          opens a new window.

        The ``timeout`` is used to specify how long keyword will poll to select
        the new window. The ``timeout`` is new in SeleniumLibrary 3.2.

        The ``browser`` argument allows with ``index_or_alias`` to implicitly switch to
        a specific browser when switching to a window. See `Switch Browser`

        - If the ``browser`` is ``CURRENT`` (case-insensitive), no other browser is
          selected.

        *NOTE:*

        - The ``strategy:value`` syntax is only supported by SeleniumLibrary
          3.0 and newer.
        - Prior to SeleniumLibrary 3.0 matching windows by name, title
          and URL was case-insensitive.
        - Earlier versions supported aliases ``None``, ``null`` and the
          empty string for selecting the main window, and alias ``self``
          for selecting the current window. Support for these aliases was
          removed in SeleniumLibrary 3.2.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Opening Up New Windows And Swithching
                    Click Link     popup1    # Open new window
                    Switch Window    example    # Select window using default strategy
                    Title Should Be    Pop-up 1
                    Click Button    popup2    # Open another window
                    ${handle}=    Switch Window    NEW    # Select latest opened window
                    Title Should Be    Pop-up 2
                    Switch Window    ${handle}    # Select window using handle
                    Title Should Be    Pop-up 1
                    Switch Window    MAIN    # Select the main window
                    Title Should Be    Main
                    ${excludes}=    Get Window Handles    # Get list of current windows
                    Click Link    popup3    # Open one more window
                    Switch Window    ${excludes}    # Select window using excludes
                    Title Should Be    Pop-up 3

        :param locator: window locator
        :param timeout: used to specify how long keyword will poll to select the
         new window
        :param browser: allows with ``index_or_alias`` to implicitly switch to
         a specific browser when switching to a window
        :return: current window handle
        """

        super().switch_window(locator, timeout=timeout, browser=browser)

    @keyword
    def table_cell_should_contain(
        self,
        locator: Union[WebElement, None, str],
        row: int,
        column: int,
        expected: str,
        loglevel: str = "TRACE",
    ):
        """Verifies table cell contains text ``expected``.

        See `Get Table Cell` that this keyword uses internally for
        an explanation about accepted arguments.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Does The Cell Match My Expectations
                    Table Cell Should Contain
                    ...    table_locator
                    ...    row=7
                    ...    column=15
                    ...    expected=Robocorp

        :param locator: element locator
        :param row: row number to access (index starts from 1)
        :param column: column number to access (index starts from 1)
        :param expected: text the cell is expected to contain
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        :raises AssertionError: if the cell contains different text than ``expected``
        """

        super().table_cell_should_contain(
            locator, row, column, expected, loglevel=loglevel
        )

    @keyword
    def table_column_should_contain(
        self,
        locator: Union[WebElement, None, str],
        column: int,
        expected: str,
        loglevel: str = "TRACE",
    ):
        """Verifies table column contains text ``expected``.

        The table is located using the ``locator`` argument and its column
        found using ``column``. See the `Locating elements` section for
        details about the locator syntax.

        Column indexes start from 1. It is possible to refer to columns
        from the end by using negative indexes so that -1 is the last column,
        -2 is the second last, and so on.

        If a table contains cells that span multiple columns, those merged
        cells count as a single column.

        See `Page Should Contain Element` for an explanation about the
        ``loglevel`` argument.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Does The Column Match My Expectations
                    Table Column Should Contain
                    ...    table_locator
                    ...    column=15
                    ...    expected=Robocorp

        :param locator: element locator
        :param column: column number to access (index starts from 1)
        :param expected: text the column is expected to contain
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        :raises AssertionError: if the column text does not contain ``expected``
        """

        super().table_column_should_contain(
            locator, column, expected, loglevel=loglevel
        )

    @keyword
    def table_footer_should_contain(
        self,
        locator: Union[WebElement, None, str],
        expected: str,
        loglevel: str = "TRACE",
    ):
        """Verifies table footer contains text ``expected``.

        Any ``<td>`` element inside ``<tfoot>`` element is considered to
        be part of the footer.

        The table is located using the ``locator`` argument. See the
        `Locating elements` section for details about the locator syntax.

        See `Page Should Contain Element` for an explanation about the
        ``loglevel`` argument.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Does The Footer Match My Expectations
                    Table Footer Should Contain
                    ...    table_locator
                    ...    expected=Robocorp

        :param locator: element locator
        :param expected: text the footer is expected to contain
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        :raises AssertionError: if the footer text does not contain ``expected``
        """

        super().table_footer_should_contain(locator, expected, loglevel=loglevel)

    @keyword
    def table_header_should_contain(
        self,
        locator: Union[WebElement, None, str],
        expected: str,
        loglevel: str = "TRACE",
    ):
        """Verifies table header contains text ``expected``.

        Any ``<th>`` element anywhere in the table is considered to be
        part of the header.

        The table is located using the ``locator`` argument. See the
        `Locating elements` section for details about the locator syntax.

        See `Page Should Contain Element` for an explanation about the
        ``loglevel`` argument.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Does The Header Match My Expectations
                    Table Header Should Contain
                    ...    table_locator
                    ...    expected=Robocorp

        :param locator: element locator
        :param expected: text the header is expected to contain
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        :raises AssertionError: if the header text does not contain ``expected``
        """

        super().table_header_should_contain(locator, expected, loglevel=loglevel)

    @keyword
    def table_row_should_contain(
        self,
        locator: Union[WebElement, None, str],
        row: int,
        expected: str,
        loglevel: str = "TRACE",
    ):
        """Verifies that table row contains text ``expected``.

        The table is located using the ``locator`` argument and its column
        found using ``column``. See the `Locating elements` section for
        details about the locator syntax.

        Row indexes start from 1. It is possible to refer to rows
        from the end by using negative indexes so that -1 is the last row,
        -2 is the second last, and so on.

        If a table contains cells that span multiple rows, a match
        only occurs for the uppermost row of those merged cells.

        See `Page Should Contain Element` for an explanation about the
        ``loglevel`` argument.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Does The Row Match My Expectations
                    Table Row Should Contain
                    ...    table_locator
                    ...    row=7
                    ...    expected=Robocorp

        :param locator: element locator
        :param row: row number to access (index starts from 1)
        :param expected: text the row is expected to contain
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        :raises AssertionError: if the row text does not contain ``expected``
        """

        super().table_row_should_contain(locator, row, expected, loglevel=loglevel)

    @keyword
    def table_should_contain(
        self,
        locator: Union[WebElement, None, str],
        expected: str,
        loglevel: str = "TRACE",
    ):
        """Verifies table contains text ``expected``.

        The table is located using the ``locator`` argument. See the
        `Locating elements` section for details about the locator syntax.

        See `Page Should Contain Element` for an explanation about the
        ``loglevel`` argument.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Does The Table Match My Expectations
                    Table Should Contain
                    ...    table_locator
                    ...    expected=Robocorp

        :param locator: element locator
        :param expected: text the row is expected to contain
        :param loglevel: valid log levels are ``DEBUG``, ``INFO`` (default),
        ``WARN``, and ``NONE``
        :raises AssertionError: if the row table does not contain ``expected``
        """

        super().table_should_contain(locator, expected, loglevel=loglevel)

    @keyword
    def textarea_should_contain(
        self,
        locator: Union[WebElement, str],
        expected: str,
        message: Optional[str] = None,
    ):
        """Verifies text area ``locator`` contains text ``expected``.

        ``message`` can be used to override default error message.

        See the `Locating elements` section for details about the locator
        syntax.
        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Is The Text In The Textarea What I Expect
                    Textfield Should Contain
                    ...    textarea_locator
                    ...    My Text Here
                    ...    My optional error message here

        :param locator: element locator
        :param expected: text that should be present in the textarea
        :param message: used to override the default error message
        """

        super().textarea_should_contain(locator, expected, message=message)

    @keyword
    def textarea_value_should_be(
        self,
        locator: Union[WebElement, str],
        expected: str,
        message: Optional[str] = None,
    ):
        """Verifies text area ``locator`` has exactly text ``expected``.

        ``message`` can be used to override default error message.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Is The Text In The Textarea Exactly What I Expect
                    Textfield Should Contain
                    ...    textarea_locator
                    ...    My Exact Text Here
                    ...    My optional error message here

        :param locator: element locator
        :param expected: text that should match exactly in the textarea
        :param message: used to override the default error message
        """

        super().textarea_value_should_be(locator, expected, message=message)

    @keyword
    def textfield_should_contain(
        self,
        locator: Union[WebElement, str],
        expected: str,
        message: Optional[str] = None,
    ):
        """Verifies text field ``locator`` contains text ``expected``.

        ``message`` can be used to override the default error message.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Is The Text In The Textfield What I Expect
                    Textfield Should Contain
                    ...    textfield_locator
                    ...    My Text Here
                    ...    My optional error message here

        :param locator: element locator
        :param expected: text that should be present in the textfield
        :param message: used to override the default error message
        """

        super().textfield_should_contain(locator, expected, message=message)

    @keyword
    def textfield_value_should_be(
        self,
        locator: Union[WebElement, str],
        expected: str,
        message: Optional[str] = None,
    ):
        """Verifies text field ``locator`` has exactly text ``expected``.

        ``message`` can be used to override default error message.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Is The Text In The Textfield Exactly What I Expect
                    Textfield Should Contain
                    ...    textfield_locator
                    ...    My Exact Text Here
                    ...    My optional error message here

        :param locator: element locator
        :param expected: text that should match exactly in the textfield
        :param message: used to override the default error message
        """

        super().textfield_value_should_be(locator, expected, message=message)

    @keyword
    def title_should_be(self, title: str, message: Optional[str] = None):
        """Verifies that the current page title equals ``title``.

        The ``message`` argument can be used to override the default error
        message.

        ``message`` argument is new in SeleniumLibrary 3.1.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Is My Title What I Expect
                    Title Should Be
                    ...    My Title Here
                    ...    message=My Title Is Not Correct. It Shoudl Be "My Title Here"

        :param title: title that the current page should equal
        :param messgae: used to override the default error message
        """

        super().title_should_be(title=title, message=message)

    @keyword
    def unselect_all_from_list(self, locator: Union[WebElement, str]):
        """Unselects all options from multi-selection list ``locator``.

        See the `Locating elements` section for details about the locator
        syntax.

        New in SeleniumLibrary 3.0.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                I Choose None Of The Above
                    Unselect All From List    list_locator

        :param locator: element locator
        :raises RuntimeError: if used on a single selection list
        """

        super().unselect_all_from_list(locator)

    @keyword
    def unselect_checkbox(self, locator: Union[WebElement, str]):
        """Removes the selection of checkbox identified by ``locator``.

        Does nothing if the checkbox is not selected.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Checkbox Left Blank
                    Unselect Checkbox    id=checkbox_locator

        :param locator: element locator
        """

        super().unselect_checkbox(locator)

    @keyword
    def unselect_from_list_by_index(
        self, locator: Union[WebElement, str], *indexes: str
    ):
        """Unselects options from selection list ``locator`` by ``indexes``.

        Indexes of list options start from 0. This keyword works only with
        multi-selection lists.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                This will unselect the following indexes
                    Unselect From List By Index
                    ...    multi_selection_list_locator
                    ...    0 4 6 8

        :param locator: element locator
        :param indexes: one or more options from selection list
        :raises ValueError: if no index is given
        :raises RuntimeError: if used on a single selection list
        """

        super().unselect_from_list_by_index(locator, *indexes)

    @keyword
    def unselect_from_list_by_label(
        self, locator: Union[WebElement, str], *labels: str
    ):
        """Unselects options from selection list ``locator`` by ``labels``.

        This keyword works only with multi-selection lists.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                This will unselect the following labels
                    Unselect From List By Label
                    ...    multi_selection_list_locator
                    ...    DE CT MD NH

        :param locator: element locator
        :param indexes: one or more options from selection list
        :raises ValueError: if no label is given
        :raises RuntimeError: if used on a single selection list
        """

        super().unselect_from_list_by_label(locator, *indexes)

    @keyword
    def unselect_from_list_by_value(
        self, locator: Union[WebElement, str], *values: str
    ):
        """Unselects options from selection list ``locator`` by ``values``.

        This keyword works only with multi-selection lists.

        See the `Locating elements` section for details about the locator
        syntax.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                This will unselect the following values
                    Unselect From List By Value
                    ...    multi_selection_list_locator
                    ...    Delaware Connecticut Maryland New Hampshire

        :param locator: element locator
        :param indexes: one or more options from selection list
        :raises ValueError: if no value is given
        :raises RuntimeError: if used on a single selection list
        """

        super().unselect_from_list_by_value(locator, *indexes)

    @keyword
    def wait_for_condition(
        condition: str,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        """Waits until ``condition`` is true or ``timeout`` expires.

        The condition can be arbitrary JavaScript expression but it
        must return a value to be evaluated. See `Execute JavaScript` for
        information about accessing content on pages.

        Fails if the timeout expires before the condition becomes true. See
        the `Timeouts` section for more information about using timeouts
        and their default value.

        ``error`` can be used to override the default error message.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Wait On Title Return
                    Wait For Condition
                    ...    return document.title == "New Title"

                *** Keyword ***
                Wait On Not Active Status
                    Wait For Condition
                    ...    return jQuery.active == 0
                    ...    timeout=60s
                    ...    error=My error message

                *** Keyword ***
                Wait On Background Colors
                    Wait For Condition
                    ...    style = document.querySelector('h1').style; return style.background == "red" && style.color == "white"

        :param condition: arbitrary JavaScript expression but it must return a value
         to be evaluated
        :para timeout: how long to wait for the condition
        :para error: used to override the default error message
        """

        super().wait_for_condition(condition, timeout=timeout, error=error)

    @keyword
    def wait_until_element_contains(
        locator: Union[WebElement, None, str],
        text: str,
        timeout: Optional[timedelta] = None,
        error: Optional[str] = None,
    ):
        """Waits until the element ``locator`` contains ``text``.

        Fails if ``timeout`` expires before the text appears. See
        the `Timeouts` section for more information about using timeouts and
        their default value and the `Locating elements` section for details
        about the locator syntax.

        ``error`` can be used to override the default error message.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Wait For Element To Contain
                    Wait Until Element Contains
                    ...    name:textBox
                    ...    open door
                    ...    timeout=30s
                    ...    error=My Error Message

        :para locator: element locator
        :para text: text the locator should contain
        :para timeout: how long to wait to see if the text is contained in the element
        :para error: used to override the default error message
        """

        super().wait_until_element_contains(
            locator=locator, text=text, timeout=timeout, error=error
        )

    @keyword
    def wait_until_element_does_not_contain(
        locator: Union[WebElement, None, str],
        text: str,
        timeout: Optional[Union[timedelta, None]] = None,
        error: Optional[Union[str, None]] = None,
    ):

        """Waits until the element ``locator`` does not contain ``text``.

        Fails if ``timeout`` expires before the text disappears. See
        the `Timeouts` section for more information about using timeouts and
        their default value and the `Locating elements` section for details
        about the locator syntax.

        ``error`` can be used to override the default error message.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Wait For Element To Not Contain
                    Wait Until Element Does Not Contain
                    ...    name:textBox
                    ...    open door
                    ...    timeout=30s
                    ...    error=My Error Message

        :para locator: element locator
        :para text: text the locator should not contain
        :para timeout: how long to wait to see if the text is contained in the element
        :para error: used to override the default error message
        """

        super().wait_until_element_does_not_contain(
            locator=locator, text=text, timeout=timeout, error=error
        )

    @keyword
    def wait_until_element_is_enabled(
        locator: Union[WebElement, None, str],
        timeout: Optional[Union[timedelta, None]] = None,
        error: Optional[Union[str, None]] = None,
    ):
        """Waits until the element `locator` is enabled.

        Element is considered enabled if it is not disabled nor read-only.

        Fails if `timeout` expires before the element is enabled. See the _Timeouts_
        section for more information about using timeouts and their default value
        and the _Locating elements_ section for details about the locator syntax.

        `error` can be used to override the default error message.

        Considering read-only elements to be disabled is a new feature in SeleniumLibrary 3.0.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Should Be Enabled
                    Wait Until Element Is Enabled
                    ...    id:locator
                    ...    timeout=30s
                    ...    error=This is my error message

        :param locator: element locator
        :param timeout: how long to wait for the element to be enabled
        :param error: used to override the default error message
        """

        super().wait_until_element_is_enabled(locator, timeout=timeout, error=error)

    @keyword
    def wait_until_element_is_not_visible(
        locator: Union[WebElement, None, str],
        timeout: Optional[Union[timedelta, None]] = None,
        error: Optional[Union[str, None]] = None,
    ):
        """Waits until the element `locator` is not visible.

        Fails if `timeout` expires before the element is not visible. See the
        _Timeouts_ section for more information about using timeouts and their
        default value and the _Locating elements_ section for details about the
        locator syntax.

        `error` can be used to override the default error message.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Should Not See Element
                    Wait Until Element Is Not Visible
                    ...    id:locator
                    ...    timeout=30s
                    ...    error=This is my error message

        :param locator: element locator
        :param timeout: how long to wait for the element to not be visable
        :param error: used to override the default error message
        """

        super().wait_until_element_is_not_visible(locator, timeout=timeout, error=error)

    @keyword
    def wait_until_element_is_visible(
        locator: Union[WebElement, None, str],
        timeout: Optional[Union[timedelta, None]] = None,
        error: Optional[Union[str, None]] = None,
    ):
        """Waits until the element `locator` is visible.

        Fails if `timeout` expires before the element is visible. See the _Timeouts_
        section for more information about using timeouts and their default value and
        the _Locating elements_ section for details about the locator syntax.

        `error` can be used to override the default error message.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Should See Element
                    Wait Until Element Is Visible
                    ...    id:locator
                    ...    timeout=30s
                    ...    error=This is my error message

        :param locator: element locator
        :param timeout: how long to wait for the element to be visable
        :param error: used to override the default error message
        """

        super().wait_until_element_is_visible(locator, timeout=timeout, error=error)

    @keyword
    def wait_until_location_contains(
        expected: str,
        timeout: Optional[Union[timedelta, None]] = None,
        message: Optional[Union[str, None]] = None,
    ):
        """Waits until the current URL contains `expected`.

        The `expected` argument contains the expected value in url.

        Fails if `timeout` expires before the location contains. See the _Timeouts_
        section for more information about using timeouts and their default value.

        The message argument can be used to override the default error message.

        New in SeleniumLibrary 4.0

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                URL Should Contain
                    Wait Until Locatin Contains
                    ...    /shopping/laptops
                    ...    timeout=30s
                    ...    message=This is my error message

        :param expected: expected value in url
        :param timeout: how long to wait for the expected url
        :param message: used to override the default error message
        """

        super().wait_until_location_contains(expected, timeout=timeout, message=message)

    @keyword
    def wait_until_location_does_not_contain(
        location: str,
        timeout: Optional[Union[timedelta, None]] = None,
        message: Optional[Union[str, None]] = None,
    ):
        """Waits until the current URL does not contain `location`.

        The `location` argument contains value not expected in url.

        Fails if `timeout` expires before the location not contains. See the
        _Timeouts_ section for more information about using timeouts and their default value.

        The `message` argument can be used to override the default error message.

        New in SeleniumLibrary 4.3

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                URL Shoud Not Contain
                    Wait Until Location Does Not Contain
                    ...    /pictures/2020
                    ...    timeout=30s
                    ...    message=This is my error message

        :param location: unexpected value in url
        :param timeout: how long to wait for the location to change
        :param message: used to override the default error message
        """

        super().wait_until_location_does_not_contain(
            location, timeout=timeout, message=message
        )

    @keyword
    def wait_until_location_is(
        expected: str,
        timeout: Optional[Union[timedelta, None]] = None,
        message: Optional[Union[str, None]] = None,
    ):

        """Waits until the current URL is `expected`.

        The `expected` argument is the expected value in url.

        Fails if `timeout` expires before the location is. See the _Timeouts_
        section for more information about using timeouts and their default value.

        The `message` argument can be used to override the default error message.

        New in SeleniumLibrary 4.0

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                URL We Expect
                    Wait Until Locatin Is
                    ...    www.google.com
                    ...    timeout=30s
                    ...    message=This is my error message

        :param expected: expected value in url
        :param timeout: how long to wait for the expected url
        :param message: used to override the default error message
        """

        super().wait_until_location_is(expected, timeout=timeout, message=message)

    @keyword
    def wait_until_location_is_not(
        location: str,
        timeout: Optional[Union[timedelta, None]] = None,
        message: Optional[Union[str, None]] = None,
    ):
        """Waits until the current URL is not `location`.

        The `location` argument is the unexpected value in url.

        Fails if `timeout` expires before the location is not. See the _Timeouts_
        section for more information about using timeouts and their default value.

        The `message` argument can be used to override the default error message.

        New in SeleniumLibrary 4.3

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                URL Shoud Change
                    Wait Until Locatin Is Not
                    ...    www.google.com
                    ...    timeout=30s
                    ...    message=This is my error message

        :param location: unexpected value in url
        :param timeout: how long to wait for the location to change
        :param message: used to override the default error message
        """

        super().wait_until_location_is_not(location, timeout=timeout, message=message)

    @keyword
    def wait_until_page_contains(
        text: Union[WebElement, None, str],
        timeout: Optional[Union[timedelta, None]] = None,
        error: Optional[Union[str, None]] = None,
    ):
        """Waits until `text` appears on the current page.

        Fails if `timeout` expires before the text appears. See the _Timeouts_
        section for more information about using timeouts and their default value.

        `error` can be used to override the default error message.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Text Shoud Appear
                    Wait Until Page Contain
                    ...    Text I am looking for
                    ...    timeout=30s
                    ...    error=This is my error message

        :param text: text that should appear on the current page
        :param timeout: how long to wait for the element to appear
        :param error: used to override the default error message
        """

        super().wait_until_page_contains(text, timeout=timeout, error=error)

    @keyword
    def wait_until_page_contains_element(
        locator: Union[WebElement, None, str],
        timeout: Optional[Union[timedelta, None]] = None,
        error: Optional[Union[str, None]] = None,
        limit: Optional[Union[int, None]] = None,
    ):
        """Waits until the element `locator` appears on the current page.

        Fails if `timeout` expires before the element appears. See the _Timeouts_
        section for more information about using timeouts and their default value
        and the _Locating elements_ section for details about the locator syntax.

        `error` can be used to override the default error message.

        The `limit` argument can used to define how many elements the page should
        contain. When `limit` is _None_ (default) page can contain one or more
        elements. When limit is a number, page must contain same number of elements.

        `limit` is new in SeleniumLibrary 4.4

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Element Should Be On Page
                    Wait Until Page Contains Element
                    ...    id:locator
                    ...    timeout=30s
                    ...    error=This is my error message
                    ...    limit=${3}

        :param locator: element locator
        :param timeout: how long to wait for the element to appear
        :param error: used to override the default error message
        :param limit: used to define how many elements the page should contain
        """

        super().wait_until_page_contains_element(
            locator, timeout=timeout, error=error, limit=limit
        )

    @keyword
    def wait_until_page_does_not_contain(
        text: Union[WebElement, None, str],
        timeout: Optional[Union[timedelta, None]] = None,
        error: Optional[Union[str, None]] = None,
    ):
        """Waits until `text` disappears from the current page.

        Fails if `timeout` expires before the text disappears. See the _Timeouts_
        section for more information about using timeouts and their default value.

        `error` can be used to override the default error message.

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Text Shoud Disappear
                    Wait Until Page Does Not Contain
                    ...    Text I am looking for
                    ...    timeout=30s
                    ...    error=This is my error message

        :param text: text that should disappear from the current page
        :param timeout: how long to wait for the element to appear
        :param error: used to override the default error message
        """

        super().wait_until_page_does_not_contain(text, timeout=timeout, error=error)

    @keyword
    def wait_until_page_does_not_contain_element(
        locator: Union[WebElement, None, str],
        timeout: Optional[Union[timedelta, None]] = None,
        error: Optional[Union[str, None]] = None,
        limit: Optional[Union[int, None]] = None,
    ):
        """Waits until the element locator disappears from the current page.

        Fails if `timeout` expires before the element disappears. See the _Timeouts_
        section for more information about using timeouts and their default value
        and the _Locating elements_ section for details about the locator syntax.

        `error` can be used to override the default error message.

        The `limit` argument can used to define how many elements the page should not
        contain. When `limit` is _None_ (default) page can`t contain any elements. When
        limit is a number, page must not contain same number of elements.

        `limit` is new in SeleniumLibrary 4.4

        **Example**

            **Robot Framework**

            .. code-block:: robotframework

                *** Keyword ***
                Element Should Not Be On Page
                    Wait Until Page Does Not Contain Element
                    ...    id:locator
                    ...    timeout=30s
                    ...    error=This is my error message
                    ...    limit=${3}

        :param locator: element locator
        :param timeout: how long to wait for the element to appear
        :param error: used to override the default error message
        :param limit: used to define how many elements the page should not contain
        """

        super().wait_until_page_does_not_contain_element(
            locator, timeout=timeout, error=error, limit=limit
        )


class Selenium(SeleniumLibrary):
    """Browser is a web testing library for Robot Framework,
    based on the popular SeleniumLibrary.

    It uses the Selenium WebDriver modules internally to
    control a web browser. See http://seleniumhq.org for more information
    about Selenium in general.

    =================
    Locating elements
    =================

    All keywords in the browser library that need to interact with an element
    on a web page take an argument typically named ``locator`` that specifies
    how to find the element. Most often the locator is given as a string
    using the locator syntax described below, but `using WebElements` is
    possible too.

    Locator syntax
    ==============

    Finding elements can be done using different strategies
    such as the element id, XPath expressions, or CSS selectors. The strategy
    can either be explicitly specified with a prefix or the strategy can be
    implicit.

    Default locator strategy
    ------------------------

    By default, locators are considered to use the keyword specific default
    locator strategy. All keywords support finding elements based on ``id``
    and ``name`` attributes, but some keywords support additional attributes
    or other values that make sense in their context. For example, `Click
    Link` supports the ``href`` attribute and the link text in addition
    to the normal ``id`` and ``name``.

    Examples:

    +-----------------+---------+-------------------------------------------------+
    | `Click Element` | example | # Match based on ``id`` or ``name``.            |
    +-----------------+---------+-------------------------------------------------+
    | `Click Link`    | example | # Match also based on link text and ``href``.   |
    +-----------------+---------+-------------------------------------------------+
    | `Click Button`  | example | # Match based on ``id``, ``name`` or ``value``. |
    +-----------------+---------+-------------------------------------------------+

    If a locator accidentally starts with a prefix recognized as `explicit
    locator strategy` or `implicit XPath strategy`, it is possible to use
    the explicit ``default`` prefix to enable the default strategy.

    Examples:

    +-----------------+------------------+-------------------------------------------------+
    | `Click Element` | name:foo         | # Find element with name ``foo``.               |
    +-----------------+------------------+-------------------------------------------------+
    | `Click Element` | default:name:foo | # Use default strategy with value ``name:foo``. |
    +-----------------+------------------+-------------------------------------------------+
    | `Click Element` | //foo            | # Find element using XPath ``//foo``.           |
    +-----------------+------------------+-------------------------------------------------+
    | `Click Element` | default: //foo   | # Use default strategy with value ``//foo``.    |
    +-----------------+------------------+-------------------------------------------------+

    Explicit locator strategy
    -------------------------

    The explicit locator strategy is specified with a prefix using either
    syntax ``strategy:value`` or ``strategy=value``. The former syntax
    is preferred because the latter is identical to Robot Framework's
    `named argument syntax`_ and that can cause problems. Spaces around
    the separator are ignored, so ``id:foo``, ``id: foo`` and ``id : foo``
    are all equivalent.

    .. _named argument syntax: http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#named-argument-syntax

    Locator strategies that are supported by default are listed in the table
    below. In addition to them, it is possible to register `custom locators`.

    +--------------+-------------------------------------+--------------------------------+
    | Strategy     | Match based on                      | Example                        |
    +==============+=====================================+================================+
    | id           | Element ``id``.                     | ``id:example``                 |
    +--------------+-------------------------------------+--------------------------------+
    | name         | ``name`` attribute.                 | ``name:example``               |
    +--------------+-------------------------------------+--------------------------------+
    | identifier   | Either ``id`` or ``name``.          | ``identifier:example``         |
    +--------------+-------------------------------------+--------------------------------+
    | class        | Element ``class``.                  | ``class:example``              |
    +--------------+-------------------------------------+--------------------------------+
    | tag          | Tag name.                           | ``tag:div``                    |
    +--------------+-------------------------------------+--------------------------------+
    | xpath        | XPath expression.                   | ``xpath://div[@id="example"]`` |
    +--------------+-------------------------------------+--------------------------------+
    | css          | CSS selector.                       | ``css:div#example``            |
    +--------------+-------------------------------------+--------------------------------+
    | dom          | DOM expression.                     | ``dom:document.images[5]``     |
    +--------------+-------------------------------------+--------------------------------+
    | link         | Exact text a link has.              | ``link:The example``           |
    +--------------+-------------------------------------+--------------------------------+
    | partial link | Partial link text.                  | ``partial link:he ex``         |
    +--------------+-------------------------------------+--------------------------------+
    | sizzle       | Sizzle selector deprecated.         | ``sizzle:div.example``         |
    +--------------+-------------------------------------+--------------------------------+
    | jquery       | jQuery expression.                  | ``jquery:div.example``         |
    +--------------+-------------------------------------+--------------------------------+
    | default      | Keyword specific default behavior.  | ``default:example``            |
    +--------------+-------------------------------------+--------------------------------+

    See the `Default locator strategy` section below for more information
    about how the default strategy works. Using the explicit ``default``
    prefix is only necessary if the locator value itself accidentally
    matches some of the explicit strategies.

    Different locator strategies have different pros and cons. Using ids,
    either explicitly like ``id:foo`` or by using the `default locator
    strategy` simply like ``foo``, is recommended when possible, because
    the syntax is simple and locating elements by id is fast for browsers.
    If an element does not have an id or the id is not stable, other
    solutions need to be used. If an element has a unique tag name or class,
    using ``tag``, ``class`` or ``css`` strategy like ``tag:h1``,
    ``class:example`` or ``css:h1.example`` is often an easy solution. In
    more complex cases using XPath expressions is typically the best
    approach. They are very powerful but a downside is that they can also
    get complex.

    Examples:

    +-----------------+-------------------------------------------+---------------------------------------------------+
    | `Click Element` | id:foo                                    | # Element with id 'foo'.                          |
    +-----------------+-------------------------------------------+---------------------------------------------------+
    | `Click Element` | css:div#foo h1                            | # h1 element under div with id 'foo'.             |
    +-----------------+-------------------------------------------+---------------------------------------------------+
    | `Click Element` | xpath: //div[@id="foo"]//h1               | # Same as the above using XPath, not CSS.         |
    +-----------------+-------------------------------------------+---------------------------------------------------+
    | `Click Element` | xpath: //\*[contains(text(), "example")]  | # Element containing text 'example'.              |
    +-----------------+-------------------------------------------+---------------------------------------------------+

    **NOTE:**

    - Using the ``sizzle`` strategy or its alias ``jquery`` requires that
      the system under test contains the jQuery library.

    Implicit XPath strategy
    -----------------------

    If the locator starts with ``//`` or ``(//``, the locator is considered
    to be an XPath expression. In other words, using ``//div`` is equivalent
    to using explicit ``xpath://div``.

    Examples:

    +-----------------+----------------------+
    | `Click Element` | //div[@id="foo"]//h1 |
    +-----------------+----------------------+
    | `Click Element` | (//div)[2]           |
    +-----------------+----------------------+

    Chaining locators
    -----------------

    It's possible to chain multiple locators together as a single locator. Each chained locator must start
    with a locator strategy. Chained locators must be separated with a single space, two greater than characters,
    and followed with a space. It's also possible to mix different locator strategies, such as css or xpath.
    Also, a list can also be used to specify multiple locators, for instance when the chaining separator
    would conflict with the actual locator, or when an existing web element is used as a base.

    Although all locators support chaining, some locator strategies don't chain properly with previous values.
    This is because some locator strategies use JavaScript to find elements and JavaScript is executed
    for the whole browser context and not for the element found by the previous locator. Locator strategies
    that support chaining are the ones that are based on the Selenium API, such as `xpath` or `css`, but for example
    chaining is not supported by `sizzle` or `jquery`.

    Examples:

    +-----------------+-----------------------+----------------------------------------------------------------------+
    | `Click Element` | css:.bar >> xpath://a | # To find a link which is present inside an element with class "bar" |
    +-----------------+-----------------------+----------------------------------------------------------------------+

    List examples:

    +-------------------------------+-----------------+----------------------------+----------------------------+
    | ${locator_list} =             | `Create List`   | css:div#div_id             | xpath://\*[text(), " >> "] |
    +-------------------------------+-----------------+----------------------------+----------------------------+
    | `Page Should Contain Element` | ${locator_list} |                            |                            |
    +-------------------------------+-----------------+----------------------------+----------------------------+
    | ${element} =                  | Get WebElement  | xpath://\*[text(), " >> "] |                            |
    +-------------------------------+-----------------+----------------------------+----------------------------+
    | ${locator_list} =             | `Create List`   | css:div#div_id             | ${element}                 |
    +-------------------------------+-----------------+----------------------------+----------------------------+
    | `Page Should Contain Element` | ${locator_list} |                            |                            |
    +-------------------------------+-----------------+----------------------------+----------------------------+

    Using WebElements
    =================

    In addition to specifying a locator as a string, it is possible to use
    Selenium's WebElement objects. This requires first getting a WebElement,
    for example, by using the `Get WebElement` keyword.

    +-----------------+------------------+------------+
    | ${elem} =       | `Get WebElement` | id:example |
    +-----------------+------------------+------------+
    | `Click Element` | ${elem}          |            |
    +-----------------+------------------+------------+

    Custom locators
    ===============

    If more complex lookups are required than what is provided through the
    default locators, custom lookup strategies can be created. Using custom
    locators is a two part process. First, create a keyword that returns
    a WebElement that should be acted on:

    +-------------------------+-------------+--------------------+------------------------------------------------------+--------+----------------+
    | Custom Locator Strategy | [Arguments] | ${browser}         | ${locator}                                           | ${tag} | ${constraints} |
    +-------------------------+-------------+--------------------+------------------------------------------------------+--------+----------------+
    |                         | ${element}= | Execute Javascript | return window.document.getElementById('${locator}'); |        |                |
    +-------------------------+-------------+--------------------+------------------------------------------------------+--------+----------------+
    |                         | [Return]    | ${element}         |                                                      |        |                |
    +-------------------------+-------------+--------------------+------------------------------------------------------+--------+----------------+

    This keyword is a reimplementation of the basic functionality of the
    ``id`` locator where ``${browser}`` is a reference to a WebDriver
    instance and ``${locator}`` is the name of the locator strategy. To use
    this locator, it must first be registered by using the
    `Add Location Strategy` keyword:

    +-------------------------+--------+-------------------------+
    | `Add Location Strategy` | custom | Custom Locator Strategy |
    +-------------------------+--------+-------------------------+

    The first argument of `Add Location Strategy` specifies the name of
    the strategy and it must be unique. After registering the strategy,
    the usage is the same as with other locators:

    +-----------------+----------------+
    | `Click Element` | custom:example |
    +-----------------+----------------+

    See the `Add Location Strategy` keyword for more details.

    ==================
    Browser and Window
    ==================

    There is different conceptual meaning when this library talks
    about windows or browsers. This chapter explains those differences.

    Browser
    =======

    When `Open Browser` or `Create WebDriver` keyword is called, it
    will create a new Selenium WebDriver instance by using the `Selenium WebDriver`_
    API. In this library's terms, a new browser is created. It is
    possible to start multiple independent browsers (Selenium Webdriver
    instances) at the same time, by calling `Open Browser` or
    `Create WebDriver` multiple times. These browsers are usually
    independent of each other and do not share data like cookies,
    sessions or profiles. Typically when the browser starts, it
    creates a single window which is shown to the user.

    .. _Selenium WebDriver: https://www.seleniumhq.org/docs/03_webdriver.jsp

    Window
    ======

    Windows are the part of a browser that loads the web site and presents
    it to the user. All content of the site is the content of the window.
    Windows are children of a browser. In this context a browser is a
    synonym for WebDriver instance. One browser may have multiple
    windows. Windows can appear as tabs, as separate windows or pop-ups with
    different position and size. Windows belonging to the same browser
    typically share the sessions detail, like cookies. If there is a
    need to separate sessions detail, example login with two different
    users, two browsers (Selenium WebDriver instances) must be created.
    New windows can be opened example by the application under test or
    by example `Execute Javascript` keyword:

    | `Execute Javascript`    window.open()    # Opens a new window with location about:blank

    The example below opens multiple browsers and windows,
    to demonstrate how the different keywords can be used to interact
    with browsers, and windows attached to these browsers.

    Structure:

    +----------+-----------------------------------------------------------+
    | BrowserA |    Window 1  (location=https://robotframework.org/)       |
    |          +-----------------------------------------------------------+
    |          |  Window 2  (location=https://robocon.io/)                 |
    |          +-----------------------------------------------------------+
    |          |  Window 3  (location=https://github.com/robotframework/)  |
    +----------+-----------------------------------------------------------+
    | BrowserB |  Window 1  (location=https://github.com/)                 |
    +----------+-----------------------------------------------------------+

    Example:

    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | `Open Browser`       | https://robotframework.org         | ${BROWSER}       | alias=BrowserA   | # BrowserA with first window is opened.                                       |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | `Execute Javascript` | window.open()                      |                  |                  | # In BrowserA second window is opened.                                        |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | `Switch Window`      | locator=NEW                        |                  |                  | # Switched to second window in BrowserA                                       |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | `Go To`              | https://robocon.io                 |                  |                  | # Second window navigates to robocon site.                                    |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | `Execute Javascript` | window.open()                      |                  |                  | # In BrowserA third window is opened.                                         |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | ${handle}            | `Switch Window`                    | locator=NEW      |                  | # Switched to third window in BrowserA                                        |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | `Go To`              | https://github.com/robotframework/ |                  |                  | # Third windows goes to robot framework github site.                          |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | `Open Browser`       | https://github.com                 | ${BROWSER}       | alias=BrowserB   | # BrowserB with first windows is opened.                                      |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | ${location}          | `Get Location`                     |                  |                  | # ${location} is: https://www.github.com                                      |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | `Switch Window`      | ${handle}                          | browser=BrowserA |                  | # BrowserA second windows is selected.                                        |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | ${location}          | `Get Location`                     |                  |                  | # ${location} = https://robocon.io/                                           |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | @{locations 1}       | `Get Locations`                    |                  |                  | # By default, lists locations under the currectly active browser (BrowserA).  |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+
    | @{locations 2}       | `Get Locations`                    |  browser=ALL     |                  | # By using browser=ALL argument keyword list all locations from all browsers. |
    +----------------------+------------------------------------+------------------+------------------+-------------------------------------------------------------------------------+

    The above example, @{locations 1} contains the following items:
    https://robotframework.org/, https://robocon.io/ and
    https://github.com/robotframework/'. The @{locations 2}
    contains the following items: https://robotframework.org/,
    https://robocon.io/, https://github.com/robotframework/'
    and 'https://github.com/.

    ===========================
    Timeouts, waits, and delays
    ===========================

    This section discusses different ways on how to wait for elements to
    appear on web pages and to slow down execution speed otherwise.
    It also explains the `time format` that can be used when setting various
    timeouts, waits, and delays.

    Timeout
    =======

    This library contains various keywords that have an optional
    ``timeout`` argument that specifies how long these keywords should
    wait for certain events or actions. These keywords include, for example,
    ``Wait ...`` keywords and keywords related to alerts. Additionally
    `Execute Async Javascript`. Although it does not have ``timeout``,
    argument, uses a timeout to define how long asynchronous JavaScript
    can run.

    The default timeout these keywords use can be set globally either by
    using the `Set Selenium Timeout` keyword or with the ``timeout`` argument
    when `importing` the library. See `time format` below for supported
    timeout syntax.

    Implicit wait
    =============

    Implicit wait specifies the maximum time how long Selenium waits when
    searching for elements. It can be set by using the `Set Selenium Implicit
    Wait` keyword or with the ``implicit_wait`` argument when `importing`
    the library. See `Selenium documentation`_
    for more information about this functionality.

    .. _Selenium documentation: https://www.seleniumhq.org/docs/04_webdriver_advanced.jsp

    See `time format` below for supported syntax.

    Selenium speed
    ==============

    Selenium execution speed can be slowed down globally by using `Set
    Selenium speed` keyword. This functionality is designed to be used for
    demonstrating or debugging purposes. Using it to make sure that elements
    appear on a page is not a good idea. The above-explained timeouts
    and waits should be used instead.

    See `time format` below for supported syntax.

    Time format
    ===========

    All timeouts and waits can be given as numbers considered seconds
    (e.g. ``0.5`` or ``42``) or in Robot Framework's time syntax
    (e.g. ``1.5 seconds`` or ``1 min 30 s``). For more information about
    the time syntax see the `Robot Framework User Guide`_.

    .. _Robot Framework User Guide: http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#time-format

    ============================
    Run-on-failure functionality
    ============================

    This library has a handy feature that it can automatically execute
    a keyword if any of its own keywords fails. By default, it uses the
    `Capture Page Screenshot` keyword, but this can be changed either by
    using the `Register Keyword To Run On Failure` keyword or with the
    ``run_on_failure`` argument when `importing` the library. It is
    possible to use any keyword from any imported library or resource file.

    The run-on-failure functionality can be disabled by using a special value
    ``NOTHING`` or anything considered false (see `Boolean arguments`)
    such as ``NONE``.

    ====================
    Auto closing browser
    ====================

    By default browser instances created during task execution are closed
    at the end of the task. This can be prevented with the ``auto_close``
    argument when `importing` the library.

    Value needs to be set to ``False`` or anything considered false (see `Boolean arguments`).

    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    AVAILABLE_OPTIONS = {
        "chrome": "ChromeOptions",
        "firefox": "FirefoxOptions",
        # "safari": "WebKitGTKOptions",
        # "ie": "IeOptions",
    }

    def __init__(self, *args, **kwargs) -> None:
        # We need to pop our kwargs before passing kwargs to SeleniumLibrary
        self.auto_close = kwargs.pop("auto_close", True)
        self.locators_path = kwargs.pop("locators_path", None)

        # Parse user-given plugins
        plugins = kwargs.get("plugins", "")
        plugins = set(p for p in plugins.split(",") if p)

        # Add testability if requested
        if "use_testability" in args:
            args = [arg for arg in args if arg != "use_testability"]
            plugins.add("SeleniumTestability")

        # Refresh plugins list
        kwargs["plugins"] = ",".join(plugins)

        SeleniumLibrary.__init__(self, *args, **kwargs)

        # Add inherit/overriden library keywords
        overrides = [BrowserManagementKeywordsOverride(self)]
        self.add_library_components(overrides)

        self.logger = logging.getLogger(__name__)
        self.using_testability = bool("SeleniumTestability" in plugins)

        # Add support for locator aliases
        self._element_finder.register("alias", self._find_by_alias, persist=True)

        # Embed screenshots in logs by default
        if not notebook.IPYTHON_AVAILABLE:
            self._embedding_screenshots = True
            self._previous_screenshot_directory = self.set_screenshot_directory(EMBED)
        else:
            self._embedding_screenshots = False
            self._previous_screenshot_directory = None

        self.download_preferences = {}
        self._close_on_exit()

    def _close_on_exit(self):
        """Register function to clean leftover webdrivers on process exit."""
        current_platform = platform.system()

        def stop_drivers():
            if not self.auto_close:
                # On Windows chromedriver.exe keeps hanging and
                # prevents rcc close
                if current_platform == "Windows":
                    self._driver_connection_handler(process_kill=True)
                return
            self._driver_connection_handler(process_kill=False)

        atexit.register(stop_drivers)

    def _driver_connection_handler(self, process_kill: bool = False):
        connections = self._drivers._connections  # pylint: disable=protected-access
        for driver in connections:
            try:
                if process_kill:
                    driver.service.process.kill()
                else:
                    driver.service.stop()
            except Exception:  # pylint: disable=broad-except
                pass

    @property
    def location(self) -> str:
        """Return browser location."""
        return self.get_location()

    def _find_by_alias(self, parent, criteria, tag, constraints):
        """Custom 'alias' locator that uses locators database."""
        del constraints
        locator = LocatorsDatabase.load_by_name(criteria, self.locators_path)

        if not isinstance(locator, BrowserLocator):
            raise ValueError(f"Not a browser locator: {criteria}")

        selector = "{strategy}:{value}".format(
            strategy=locator.strategy, value=locator.value
        )

        return self._element_finder.find(selector, tag, parent)

    @keyword
    def open_available_browser(
        self,
        url: Optional[str] = None,
        use_profile: bool = False,
        headless: Any = "AUTO",
        maximized: bool = False,
        browser_selection: Any = "AUTO",
        alias: Optional[str] = None,
        profile_name: Optional[str] = None,
        profile_path: Optional[str] = None,
        preferences: Optional[dict] = None,
        proxy: str = None,
        user_agent: Optional[str] = None,
        download: Any = "AUTO",
    ) -> int:
        # pylint: disable=C0301
        """Attempts to open a browser on the user's device from a set of
        supported browsers. Automatically downloads a corresponding webdriver
        if none is already installed.

        Optionally can be given a ``url`` as the first argument,
        to open the browser directly to the given page.

        Returns either a generated index or a custom ``alias`` for the
        browser instance. The returned value can be used to refer to that
        specific browser instance in other keywords.

        If the browser should start in a maximized window, this can be
        enabled with the argument ``maximized``, but is disabled by default.

        For certain applications it might also be required to force a
        certain user-agent string for Selenium, which can be overriden
        with the ``user_agent`` argument.

        == Browser order ==

        The default order of supported browsers is based on the operating system
        and is as follows:

        | Platform    | Default order                    |
        | ``Windows`` | Chrome, Firefox, Edge, IE, Opera |
        | ``Linux``   | Chrome, Firefox, Opera           |
        | ``Darwin``  | Chrome, Safari, Firefox, Opera   |

        The order can be overriden with a custom list by using the argument
        ``browser_selection``. The argument can be either a comma-separated
        string or a list object.

        == Webdriver download ==

        The library can (if requested) automatically download webdrivers
        for all supported browsers. This can be controlled with the argument
        ``download``.

        If the value is ``False``, it will only attempt to start
        webdrivers found from the system PATH.

        If the value is ``True``, it will download a webdriver that matches
        the current browser.

        By default the argument has the value ``AUTO``, which means it
        first attempts to use webdrivers found in PATH and if that fails
        forces a webdriver download.

        == Opening process ==

        1. Parse list of preferred browser order. If not given, use values
           from above table.

        2. Loop through listed browsers:

            a. Set the webdriver options for the browser.

            b. Download webdriver (if requested).

            c. Attempt to launch the webdriver and stop the loop if successful.

        3. Return index/alias if webdriver was created, or raise an exception
           if no browsers were successfully opened.

        == Headless mode ==

        If required, the browser can also run `headless`, which means that
        it does not create a visible window. Generally a headless browser is
        slightly faster, but might not support all features a normal browser does.

        One typical use-case for headless mode is in cloud containers,
        where there is no display available. It also prevents manual interaction
        with the browser, which can be either a benefit or a drawback depending on
        the context.

        It can be explicitly enabled or disabled with the argument ``headless``.
        By default it will be disabled, unless it detects that it is running
        in a Linux environment without a display, i.e. a container.

        == Chrome options ==

        Some features are currently available only for Chrome/Chromium.
        This includes using an existing user profile. By default Selenium
        uses a new profile for each session, but it can use an existing
        one by enabling the ``use_profile`` argument.

        If a custom profile is stored somewhere outside of the default location,
        the path to the profiles directory and the name of the profile can
        be controlled with ``profile_path`` and ``profile_name`` respectively.

        Profile preferences can be further overriden with the ``preferences``
        argument by giving a dictionary of key/value pairs.

        Chrome can additionally connect through a ``proxy``, which
        should be given as either local or remote address.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Open Browser to Webpage
                Open Available Browser    https://www.robocorp.com

            *** Keyword ***
            Open Browser to Webpage
                ${index}=    Open Available Browser    ${URL}    browser_selection=opera,firefox

            *** Keyword ***
            Open Browser to Webpage
                Open Available Browser    ${URL}    headless=True    alias=HeadlessBrowser

        :param url: URL to open
        :param use_profile: chrome profile to load into browser, default is `False`.
         Chrome only feature
        :param headless: opens a human visable or invisable browser instance,
         default is "AUTO"
        :param maximized: maximizes the browser window when opened, default is `False`
        :param browser_selection: the order in which webdrivers are attempted when
         opening a new browser, default is `AUTO`
        :param alias: custom alias for this browser instance
        :param profile_name: name of the profile, used in conjunction with `use_profile`.
         Chrome only feature
        :param profile_path: path to the profile, used in conjunction with `use_profile`.
         Chrome only feature
        :param preferences: loads the browser with different preferences for the
         selected profile, used in conjunction with `use_profile`. Chrome only feature
        :param proxy: address of the proxy the browser instance should use
        :param user_agent: a string to set the user identity
         e.g. User-Agent: Mozilla/<version> (<system-information>)
          <platform> (<platform-details>) <extensions>
        :param download: will download an instance of the webdriver for the chosen
         browser, default is `AUTO`
        :returns: index or alias of the browser instance
        """  # noqa: E501
        # pylint: disable=redefined-argument-from-local
        browsers = self._arg_browser_selection(browser_selection)
        downloads = self._arg_download(download)
        headless = self._arg_headless(headless)

        attempts = []
        index_or_alias = None

        # Try all browsers in preferred order
        for browser, download in product(browsers, downloads):
            try:
                self.logger.debug(
                    "Creating webdriver for '%s' (headless: %s, download: %s)",
                    browser,
                    headless,
                    download,
                )
                kwargs, arguments = self._get_driver_args(
                    browser,
                    headless,
                    maximized,
                    use_profile,
                    profile_name,
                    profile_path,
                    preferences,
                    proxy,
                    user_agent,
                )
                index_or_alias = self._create_webdriver(
                    browser, alias, download, **kwargs
                )
                attempts.append((browser, download, ""))
                self.logger.info(
                    "Created %s browser with arguments: %s",
                    browser,
                    " ".join(arguments),
                )
                break
            except Exception as error:  # pylint: disable=broad-except
                attempts.append((browser, download, error))
                self.logger.debug(traceback.format_exc())

        # Log table of all attempted combinations
        table_headers = ["Browser", "Download", "Error"]
        try:
            table = html_table(header=table_headers, rows=attempts)
            BuiltIn().log("<p>Attempted combinations:</p>" + table, html=True)
        except RobotNotRunningError:
            pass

        # No webdriver was started
        if index_or_alias is None:
            errors = OrderedDict((browser, error) for browser, _, error in attempts)

            msg = "Failed to start a browser:\n"
            for browser, error in errors.items():
                msg += f"- {browser}: {error}\n"

            notebook.notebook_table(attempts, columns=table_headers)
            raise BrowserNotFoundError(msg)

        if url is not None:
            self.go_to(url)

        return index_or_alias

    def _arg_browser_selection(self, browser_selection: Any) -> List:
        """Parse argument for browser selection."""
        if str(browser_selection).strip().lower() == "auto":
            order = webdriver.DRIVER_PREFERENCE.get(
                platform.system(), webdriver.DRIVER_PREFERENCE["default"]
            )
        else:
            order = (
                browser_selection
                if isinstance(browser_selection, list)
                else browser_selection.split(",")
            )
        return order

    def _arg_download(self, download: Any) -> List:
        """Parse argument for webdriver download."""
        if str(download).strip().lower() == "auto":
            return [False, True]
        else:
            return [bool(download)]

    def _arg_headless(self, headless: Any) -> bool:
        """Parse argument for headless mode."""
        if str(headless).strip().lower() == "auto":
            # If in Linux and with no valid display, we can assume we are in a container
            headless = platform.system() == "Linux" and not (
                os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
            )
            if headless:
                self.logger.info("Autodetected headless environment")
            return headless
        else:
            return bool(headless)

    def _get_driver_args(
        self,
        browser: str,
        headless: bool = False,
        maximized: bool = False,
        use_profile: bool = False,
        profile_name: Optional[str] = None,
        profile_path: Optional[str] = None,
        preferences: Optional[dict] = None,
        proxy: str = None,
        user_agent: Optional[str] = None,
    ) -> dict:
        """Get browser and webdriver arguments for given options."""
        preferences = preferences or {}
        browser = browser.lower()
        headless = headless or bool(int(os.getenv("RPA_HEADLESS_MODE", "0")))
        kwargs = {}

        if browser not in self.AVAILABLE_OPTIONS:
            return kwargs, []

        module = importlib.import_module("selenium.webdriver")
        factory = getattr(module, self.AVAILABLE_OPTIONS[browser])
        options = factory()

        if headless:
            self._set_headless_options(browser, options)

        if maximized:
            options.add_argument("--start-maximized")

        if user_agent:
            options.add_argument(f"user-agent={user_agent}")

        if browser != "chrome":
            kwargs["options"] = options
            if use_profile:
                self.logger.warning("Profiles are supported only with Chrome")

        else:
            default_preferences = {
                "safebrowsing.enabled": True,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
            }
            if proxy:
                options.add_argument("--proxy-server=%s" % proxy)
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
            options.add_argument("--no-sandbox")
            options.add_experimental_option(
                "prefs",
                {**default_preferences, **preferences, **self.download_preferences},
            )
            options.add_experimental_option(
                "excludeSwitches", ["enable-logging", "enable-automation"]
            )

            if use_profile:
                self._set_user_profile(options, profile_path, profile_name)

            if self.logger.isEnabledFor(logging.DEBUG):
                kwargs["service_log_path"] = "chromedriver.log"
                kwargs["service_args"] = ["--verbose"]

            kwargs["options"] = options

        return kwargs, options.arguments

    def _set_headless_options(self, browser: str, options: dict) -> None:
        """Set headless mode for the browser, if possible.

        ``browser`` string name of the browser

        ``options`` browser options class instance
        """
        if browser.lower() == "safari":
            self.logger.warning(
                "Safari does not support headless mode. "
                "(https://github.com/SeleniumHQ/selenium/issues/5985)"
            )
            return

        options.add_argument("--headless")
        options.add_argument("--disable-gpu")

        if browser.lower() == "chrome":
            options.add_argument("--window-size=1440,900")

    def _set_user_profile(
        self,
        options: dict,
        profile_path: Optional[str] = None,
        profile_name: Optional[str] = None,
    ) -> None:
        """Set user profile configuration into browser options

        Requires environment variable ``RPA_CHROME_USER_PROFILE_DIR``
        to point into user profile directory.

        ``options`` dictionary of browser options
        """
        data_dir = profile_path or os.getenv("RPA_CHROME_USER_PROFILE_DIR")

        system = platform.system()
        home = Path.home()

        if data_dir is not None:
            pass
        elif system == "Windows":
            data_dir = home / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
        elif system == "Linux":
            data_dir = home / ".config" / "google-chrome"
        elif system == "Darwin":
            data_dir = home / "Library" / "Application Support" / "Google" / "Chrome"
        else:
            self.logger.warning("Unable to resolve profile directory for: %s", system)
            return

        if not Path(data_dir).exists():
            self.logger.warning("Given profile directory does not exist: %s", data_dir)

        options.add_argument("--enable-local-sync-backend")
        options.add_argument(f"--local-sync-backend-dir={data_dir}")
        options.add_argument(f"--user-data-dir={data_dir}")

        if profile_name is not None:
            options.add_argument(f"--profile-directory={profile_name}")

    def _create_webdriver(
        self, browser: str, alias: Optional[str], download: bool, **kwargs
    ):
        """Create a webdriver instance with given options.

        If webdriver download is requested, try using a cached
        version first and if that fails force a re-download.
        """
        browser = browser.lower()

        def _create_driver(path=None):
            options = dict(kwargs)
            if path is not None:
                options["executable_path"] = str(path)

            lib = BrowserManagementKeywords(self)
            return lib.create_webdriver(browser.capitalize(), alias, **options)

        # No download requested
        if not download:
            return _create_driver()

        # Check if webdriver is available for given browser
        if browser not in webdriver.AVAILABLE_DRIVERS:
            raise ValueError(f"Webdriver download not available for {browser.title()}")

        # Try to use webdriver already in cache
        path_cache = webdriver.cache(browser)
        if path_cache:
            try:
                return _create_driver(path_cache)
            except Exception:  # pylint: disable=broad-except
                pass

        # Try to download webdriver
        with suppress_logging():
            path_download = webdriver.download(browser)
        if path_download:
            return _create_driver(path_download)

        # No webdriver required
        return _create_driver()

    @keyword
    def open_chrome_browser(
        self,
        url: str,
        use_profile: bool = False,
        headless: bool = False,
        maximized: bool = False,
        alias: Optional[str] = None,
        profile_name: Optional[str] = None,
        profile_path: Optional[str] = None,
        preferences: Optional[dict] = None,
        proxy: str = None,
        user_agent: Optional[str] = None,
    ) -> int:
        """Open Chrome browser. See ``Open Available Browser`` for
        descriptions of arguments.
        """
        return self.open_available_browser(
            url,
            alias=alias,
            headless=headless,
            maximized=maximized,
            use_profile=use_profile,
            browser_selection="Chrome",
            profile_name=profile_name,
            profile_path=profile_path,
            preferences=preferences,
            proxy=proxy,
            user_agent=user_agent,
        )

    @keyword
    def attach_chrome_browser(self, port: int, alias: Optional[str] = None):
        """Attach to an existing instance of Chrome or Chromium.

        Requires that the browser was started with the command line
        option ``--remote-debugging-port=<port>``, where port is any
        4-digit number not being used by other applications.

        That port can then be used to connect using this keyword.

        **Example**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Attach Existing Instance of Chrome Browser
                Attach Chrome Browser    port=9222

        :param port: the unique port number he chrome browser is using
        :param alias: alias to assign to this browser instance
        """
        options = ChromeOptions()
        options.add_experimental_option("debuggerAddress", f"localhost:{port:d}")
        create = partial(self._create_webdriver, "Chrome", alias, options=options)

        try:
            return create(download=False)
        except Exception:  # pylint: disable=broad-except
            self.logger.debug(traceback.format_exc())
        return create(download=True)

    @keyword
    def open_headless_chrome_browser(self, url: str) -> int:
        """Open Chrome browser in headless mode.

        **Example**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Headless Chrome Browser Instance
                ${idx}=    Open Headless Chrome Browser    https://www.google.com

        :param url: URL to open
        """
        return self.open_chrome_browser(url, headless=True)

    @keyword
    def screenshot(
        self,
        locator: str = None,
        filename: str = "",
    ) -> None:
        # pylint: disable=C0301, W0212
        """Capture page and/or element screenshot.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Take a Screenshot defaults
                Screenshot    # page screenshot, default filename

            *** Keyword ***
            Take a Screenshot Example 1
                Screenshot    locator=//img[@alt="Google"]    filename=locator.png    # element screenshot, defined filename

            *** Keyword ***
            Take a Screenshot Example 2
                Screenshot    filename=page.png    # page screenshot, defined filename

            *** Keyword ***
            Take a Screenshot Example 3
                Screenshot    filename=${NONE}    # page screenshot, NO file will be created

            *** Keyword ***
            Take a Screenshot Example 4
                Screenshot    locator=//img[@alt="Google"]    # element screenshot, default filename

            *** Keyword ***
            Take a Screenshot Example 5
                Screenshot    locator=//img[@alt="Google"]    filename=${CURDIR}/subdir/loc.png    # element screenshot, create dirs if not existing

        :param locator: if ``locator`` if defined, take element screenshot, if not
         takes page screenshot
        :param filename: provides a filename for the screenshot, by default creates
         file `screenshot-timestamp-element/page.png`. If set to `None` then file is
         not saved at all
        """  # noqa: E501
        screenshot_keywords = ScreenshotKeywords(self)
        default_filename_prefix = f"screenshot-{int(time.time())}"

        # pylint: disable=unused-private-member
        def __save_base64_screenshot_to_file(base64_string, filename):
            path = screenshot_keywords._get_screenshot_path(filename)
            screenshot_keywords._create_directory(path)
            with open(filename, "wb") as fh:
                fh.write(base64.b64decode(base64_string))
                self.logger.info("Screenshot saved to file: %s", filename)

        if locator:
            element = screenshot_keywords.find_element(locator)
            screenshot_keywords._embed_to_log_as_base64(
                element.screenshot_as_base64, 400
            )
            if filename is not None:
                filename = filename or os.path.join(
                    os.curdir, f"{default_filename_prefix}-element.png"
                )
                __save_base64_screenshot_to_file(element.screenshot_as_base64, filename)
                notebook.notebook_image(filename)
        else:
            screenshot_as_base64 = self.driver.get_screenshot_as_base64()
            screenshot_keywords._embed_to_log_as_base64(screenshot_as_base64, 800)
            if filename is not None:
                filename = filename or os.path.join(
                    os.curdir, f"{default_filename_prefix}-page.png"
                )
                __save_base64_screenshot_to_file(screenshot_as_base64, filename)
                notebook.notebook_image(filename)

    @keyword
    def click_element_when_visible(
        self, locator: str, modifier: Optional[str] = None, action_chain: bool = False
    ) -> None:
        """Click element identified by ``locator``, once it becomes visible.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Click Visable Element
                Click Element When Visible    q

            Click Visable Element Example 1
                Click Element When Visible    id:button    CTRL+ALT

            Click Visable Element Example 2
                Click Element When Visible    action_chain=True

        :param locator: element locator
        :param modifier: press given keys while clicking the element, e.g. CTRL
        :param action_chain: store action in Selenium ActionChain queue
        """
        self.wait_until_element_is_visible(locator)
        self.click_element(locator, modifier, action_chain)

    @keyword
    def click_button_when_visible(
        self, locator: str, modifier: Optional[str] = None
    ) -> None:
        """Click button identified by ``locator``, once it becomes visible.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Click Visable Button
                Click Button When Visible    //button[@class="mybutton"]

        :param locator: element locator
        :param modifier: press given keys while clicking the element, e.g. CTRL
        """
        self.wait_until_element_is_visible(locator)
        self.click_button(locator, modifier)

    # Alias for backwards compatibility
    wait_and_click_button = click_button_when_visible

    @keyword
    def click_element_if_visible(self, locator: str) -> None:
        """Click element if it is visible

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Click Visable Element
                Click Element If Visible    //button[@class="mybutton"]

        :parma locator: element locator
        """
        visible = self.is_element_visible(locator)
        if visible:
            self.click_element(locator)

    @keyword
    def input_text_when_element_is_visible(self, locator: str, text: str) -> None:
        # pylint: disable=C0301
        """Input text into locator after it has become visible.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Input Text Into Visable Element
                Input Text When Element Is Visible    //input[@id="freetext"]    my feedback

        :param locator: element locator
        "param text: insert text to locator
        """  # noqa: E501
        self.wait_until_element_is_visible(locator)
        self.input_text(locator, text)

    @keyword
    def is_element_enabled(self, locator: str, missing_ok: bool = True) -> bool:
        """Is element enabled

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Check If Input Field Is Enabled
                ${res}    Is Element Enabled    input.field1

        :param locator: element locator
        :parma missing_ok: default True, set to False if keyword should Fail
         if element does not exist
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.element_should_be_enabled,
            locator,
            missing_ok=missing_ok,
        )

    @keyword
    def is_element_visible(self, locator: str, missing_ok: bool = True) -> bool:
        """Is element visible

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Check If Confirmation Button Is Visable
                ${res}    Is Element Visible    id:confirmation

        :param locator: element locator
        :parma missing_ok: default True, set to False if keyword should Fail
         if element does not exist
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.element_should_be_visible,
            locator,
            missing_ok=missing_ok,
        )

    @keyword
    def is_element_disabled(self, locator: str, missing_ok: bool = True) -> bool:
        """Is element disabled

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Check if Submit Button is Disabled
                ${res}    Is Element Disabled    //input[@type="submit"]

        :param locator: element locator
        :parma missing_ok: default True, set to False if keyword should Fail
         if element does not exist
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.element_should_be_disabled,
            locator,
            missing_ok=missing_ok,
        )

    @keyword
    def is_element_focused(self, locator: str, missing_ok: bool = True) -> bool:
        """Is element focused

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Check if Text Field is Focused
                ${res}    Is Element Focused    //input[@id="freetext"]

        :param locator: element locator
        :parma missing_ok: default True, set to False if keyword should Fail
         if element does not exist
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.element_should_be_focused,
            locator,
            missing_ok=missing_ok,
        )

    @keyword
    def is_element_attribute_equal_to(
        self, locator: str, attribute: str, expected: str
    ) -> bool:
        """Is element attribute equal to expected value

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Does Element Attribute Equal Value
                ${res}    Is Element Attribute Equal To    h1    id    main

        :param locator: element locator
        "param attribute: element attribute to check for
        :param expected: is attribute value equal to this
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.element_attribute_value_should_be, locator, attribute, expected
        )

    @keyword
    def is_alert_present(self, text: str = None, action: str = "ACCEPT") -> bool:
        """Is alert box present, which can be identified with text
        and action can also be done which by default is ACCEPT.

        Other possible actions are DISMISS and LEAVE.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Check for Alert
                ${res}    Is Alert Present    alert message

        :param text: check if alert text is matching to this, if `None`
         will check if alert is present at all
        :param action: possible action if alert is present, default ACCEPT
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.alert_should_be_present, text, action
        )

    @keyword
    def does_alert_contain(self, text: str = None, timeout: float = None) -> bool:
        # pylint: disable=W0212
        """Does alert contain text.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Check Alert Message
                ${res}    Does Alert Contain    alert message

        :param text: check if alert includes text, will raise ValueError if text
         does not exist
        :return: `True` or `False`
        :raises ValueError: if text does not exist in the alert message
        """
        alert_keywords = AlertKeywords(self)
        alert = alert_keywords._wait_alert(timeout)
        if text in alert.text:
            return True
        else:
            raise ValueError('Alert did not contain text "%s"' % text)

    @keyword
    def does_alert_not_contain(self, text: str = None, timeout: float = None) -> bool:
        # pylint: disable=W0212
        """Does alert not contain text.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Alert Messgae Should Not Contain
                ${res}    Does Alert Not Contain    unexpected message

        :param text: check that alert does not include text, will raise ValueError
         if text does exist
        :return: `True` or `False`
        :raises ValueError: if text does exist in the alert message
        """
        alert_keywords = AlertKeywords(self)
        alert = alert_keywords._wait_alert(timeout)

        if alert and text not in alert.text:
            return True
        else:
            raise ValueError('Alert did contain text "%s"' % text)

    @keyword
    def is_checkbox_selected(self, locator: str) -> bool:
        """Is checkbox selected

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for Selected Checkbox
                ${res}    Is Checkbox Selected    id:taxes-paid

        :param locator: element locator
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.checkbox_should_be_selected, locator
        )

    @keyword
    def does_frame_contain(self, locator: str, text: str) -> bool:
        """Does frame contain expected text

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for Text in Frame
                ${res}    Does Frame Contain    id:myframe    secret

        :param locator: locator of the frame to check
        :param text: does frame contain this text
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.frame_should_contain, locator, text
        )

    @keyword
    def does_element_contain(
        self, locator: str, expected: str, ignore_case: bool = False
    ) -> bool:
        # pylint: disable=C0301
        """Does element contain expected text

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for X in Element
                ${res}=    Does Element Contain
                ...    id:spec
                ...    specification complete
                ...    ignore_case=True

        :param locator: element locator
        :param expected: expected element text
        :param ignore_case: should check be case insensitive, default `False`
        :return: `True` or `False`
        """  # noqa: E501
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

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Is the Element Text What We Expect
                ${res}=    Is Element Text    id:name    john doe

            *** Keyword ***
            Is the Element Text What We Expect Ignoring Case
                ${res}=    Is Element Text    id:name    john doe    ignore_case=True

        :param locator: element locator
        :param expected: expected element text
        :param ignore_case: should check be case insensitive, default `False`
        :return: `True` or `False`
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

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Does List Contain Our Values
                ${res}=    Is List Selection    id:cars    Ford

        :param locator: element locator
        :param expected: expected selected options
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.list_selection_should_be, locator, *expected
        )

    @keyword
    def is_list_selected(self, locator: str) -> bool:
        """Is any option selected in the

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Is A List Option Selected
                ${res}=    Is List Selected    id:cars

        :param locator: element locator
        :return: `True` or `False`
        """
        self.logger.info("Will return if anything is selected on the list")
        return not self._run_should_keyword_and_return_status(
            self.list_should_have_no_selections, locator
        )

    @keyword
    def is_location(self, url: str) -> bool:
        """Is current URL expected url

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Confirm the Website Is As Expected
                ${res}=    Is Location    https://www.robocorp.com

        :param url: expected current URL
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(self.location_should_be, url)

    @keyword
    def does_location_contain(self, expected: str) -> bool:
        """Does current URL contain expected

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Does the Website Contain
                ${res}=    Does Location Contain    robocorp

        :param expected: URL should contain this
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.location_should_contain, expected
        )

    @keyword
    def does_page_contain(self, text: str) -> bool:
        """Does page contain expected text

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Is Expected Text on This Page
                ${res}=    Does Page Contain    Gmail

        :param text: page should contain this
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain, text
        )

    @keyword
    def does_page_contain_button(self, locator: str) -> bool:
        """Does page contain expected button

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Is This Button on the Page
                ${res}=    Does Page Contain Button    search-button

        :param locator: element locator
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_button, locator
        )

    @keyword
    def does_page_contain_checkbox(self, locator: str) -> bool:
        """Does page contain expected checkbox

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Is This Checkbox on the Page
                ${res}=    Does Page Contain Checkbox    random-selection

        :param locator: element locator
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_checkbox, locator
        )

    @keyword
    def does_page_contain_element(self, locator: str, count: int = None) -> bool:
        """Does page contain expected element

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Is This Element on the Page
            ${res}=    Does Page Contain Element    textarea

            *** Keyword ***
            Is This Element on the Page Four Times
            ${res}=    Does Page Contain Element    button    count=4

        :param locator: element locator
        :param count: how many times element is expected to appear on page
         by default one or more
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_element, locator=locator, limit=count
        )

    @keyword
    def does_page_contain_image(self, locator: str) -> bool:
        """Does page contain expected image

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Is an Image on this Page
                ${res}=    Does Page Contain Image    Google

        :param locator: element locator
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_image, locator
        )

    @keyword
    def does_page_contain_link(self, locator: str) -> bool:
        """Does page contain expected link

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Is a Link on this Page
                ${res}=    Does Page Contain Link    id:submit

        :param locator: element locator
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_link, locator
        )

    @keyword
    def does_page_contain_list(self, locator: str) -> bool:
        """Does page contain expected list

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Is a List on this Page
                ${res}=    Does Page Contain List    class:selections

        :param locator: element locator
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_list, locator
        )

    @keyword
    def does_page_contain_radio_button(self, locator: str) -> bool:
        """Does page contain expected radio button

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Is a Radio Button on this Page
            ${res}=    Does Page Contain Radio Button    male

        :param locator: element locator
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_radio_button, locator
        )

    @keyword
    def does_page_contain_textfield(self, locator: str) -> bool:
        """Does page contain expected textfield

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Is a Textfield on this Page
                ${res}=    Does Page Contain Textfield    id:address

        :param locator: element locator
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_textfield, locator
        )

    @keyword
    def is_radio_button_set_to(self, group_name: str, value: str) -> bool:
        """Is radio button group set to expected value

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Check Radio Button Selection
                ${res}=    Is Radio Button Set To
                ...    group_name=gender
                ...    value=female

        :param group_name: radio button group name
        :param value: expected value
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.radio_button_should_be_set_to, group_name, value
        )

    @keyword
    def is_radio_button_selected(self, group_name: str) -> bool:
        """Is any radio button selected in the button group

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Check Radio Button Selection
                ${res}    Is Radio Button Selected    group_name=gender

        :param group_name: radio button group name
        :return: `True` or `False`
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

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for Value in Table Cells
                ${res}=    Does Table Cell Contain
                ...    //table
                ...    1
                ...    1
                ...    Company

        :param locator: element locator for the table
        :param row: row index starting from 1 (beginning) or -1 (from the end)
        :param column: column index starting from 1 (beginning) or -1 (from the end)
        :param expected: expected text in table row
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.table_cell_should_contain, locator, row, column, expected
        )

    @keyword
    def does_table_column_contain(
        self, locator: str, column: int, expected: str
    ) -> bool:
        """Does table column contain expected text

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for Value in Table Column
                ${res}=    Does Table Column Contain
                ...    //table
                ...    1
                ...    Nokia

        :param locator: element locator for the table
        :param column: column index starting from 1 (beginning) or -1 (from the end)
        :param expected: expected text in table column
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.table_column_should_contain, locator, column, expected
        )

    @keyword
    def does_table_row_contain(self, locator: str, row: int, expected: str) -> bool:
        """Does table row contain expected text

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for Value in Table Row
                ${res}=    Does Table Row Contain
                ...    //table
                ...    1
                ...    Company

        :param locator: element locator for the table
        :param row: row index starting from 1 (beginning) or -1 (from the end)
        :param expected: expected text in table row
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.table_row_should_contain, locator, row, expected
        )

    @keyword
    def does_table_footer_contain(self, locator: str, expected: str) -> bool:
        """Does table footer contain expected text

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for Value in Table Footer
                ${res}=    Does Table Footer Contain    //table    Sum

        :param locator: element locator for the table
        :param expected: expected text in table footer
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.table_footer_should_contain, locator, expected
        )

    @keyword
    def does_table_header_contain(self, locator: str, expected: str) -> bool:
        """Does table header contain expected text

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for Value in Table Header
                ${res}=    Does Table Header Contain    //table    Month

        :param locator: element locator for the table
        :param expected: expected text in table header
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.table_header_should_contain, locator, expected
        )

    @keyword
    def does_table_contain(self, locator: str, expected: str) -> bool:
        """Does table contain expected text

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for Value in Table
                ${res}=    Does Table Contain    //table    February

        :param locator: element locator
        :param expected: expected text in table
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.table_should_contain, locator, expected
        )

    @keyword
    def is_textarea_value(self, locator: str, expected: str) -> bool:
        """Is textarea matching expected value

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for Textarea Text to Match
                ${res}=    Is Textarea Value    //textarea    Yours sincerely

        :param locator: element locator
        :param expected: expected textarea value
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.textarea_value_should_be, locator, expected
        )

    @keyword
    def does_textarea_contain(self, locator: str, expected: str) -> bool:
        """Does textarea contain expected text

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for Specific Text in Textarea
                ${res}=    Does Textarea Contain    //textarea    sincerely

        :param locator: element locator
        :param expected: expected text in textarea
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.textarea_should_contain, locator, expected
        )

    @keyword
    def does_textfield_contain(self, locator: str, expected: str) -> bool:
        """Does textfield contain expected text

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Look for Specific Text in Textfield
                ${res}=    Does Textfield Contain    id:lname    Last

        :param locator: element locator
        :param expected: expected text in textfield
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.textfield_should_contain, locator, expected
        )

    @keyword
    def is_textfield_value(self, locator: str, expected: str) -> bool:
        """Is textfield value expected

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Does Textfield Value Match
                ${res}=    Is Textfield Value    id:lname    Lastname

        :param locator: element locator
        :param expected: expected textfield value
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(
            self.textfield_value_should_be, locator, expected
        )

    @keyword
    def is_title(self, title: str) -> bool:
        """Is page title expected

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Does Title Match
                ${res}=    Is Title    Webpage title text

        :param title: expected title value
        :return: `True` or `False`
        """
        return self._run_should_keyword_and_return_status(self.title_should_be, title)

    def _run_should_keyword_and_return_status(self, runnable_keyword, *args, **kwargs):
        missing_ok = kwargs.pop("missing_ok", False)
        catches = (AssertionError, ElementNotFound) if missing_ok else (AssertionError)

        try:
            runnable_keyword(*args, **kwargs)
            return True
        except catches as e:
            try:
                BuiltIn().log(
                    "Ran with keyword <b>%s</b> which returned error: <i>%s</i>"
                    % (runnable_keyword.__func__.__name__.replace("_", " ").title(), e),
                    html=True,
                )
            except RobotNotRunningError:
                pass
            return False

    @keyword
    def get_element_status(self, locator: str) -> dict:
        """Return dictionary containing element status of:

            - visible
            - enabled
            - disabled
            - focused

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Capture and Log Element Status
                &{res}  Get Element Status    class:special
                Log     ${res.visible}
                Log     ${res.enabled}
                Log     ${res.disabled}
                Log     ${res.focused}

        :param locator: element locator
        :return: dictionary of the status of four properties
        """
        status_object = {}
        status_object["visible"] = self.is_element_visible(locator)
        status_object["enabled"] = self.is_element_enabled(locator)
        status_object["disabled"] = self.is_element_disabled(locator)
        status_object["focused"] = self.is_element_focused(locator)
        notebook.notebook_json(status_object)
        return status_object

    @keyword
    def get_testability_status(self) -> bool:
        """Get SeleniumTestability plugin status

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            What Is The Plugin Status
                ${status}=    Get Testability Status

        :return: `True` or `False` based on the plugin status
        """
        return self.using_testability

    @keyword
    def open_user_browser(self, url: str, tab=True) -> None:
        """Open URL with user's default browser

        The browser opened with this keyword is not accessible
        with selenium. To interact with the opened browser it is
        possible to use ``Desktop`` library keywords.

        The keyword `Attach Chrome Browser` can be used to
        access already open browser with selenium keywords.

        Read more: https://robocorp.com/docs/development-guide/browser/how-to-attach-to-running-chrome-browser

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Open User Default Browser and a new Tab
                Open User Browser    https://www.google.com?q=rpa

            *** Keyword ***
            Open User Default Browser and a new Window
                Open User Browser    https://www.google.com?q=rpa    tab=False

        :param url: URL to open
        :param tab: defines is url is opened in a tab (default `True`) or
                in new window (`False`)
        """  # noqa: E501
        browser_method = webbrowser.open_new_tab if tab else webbrowser.open_new
        browser_method(url)

    @keyword
    def get_browser_capabilities(self) -> dict:
        """Get dictionary of browser properties

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Capture Browser Properties
                ${caps}=    Get Browser Capabilities

        :return: dictionary of the browser's properties
        """
        capabilities = self.driver.capabilities
        return dict(capabilities)

    @keyword
    def set_download_directory(
        self, directory: str = None, download_pdf: bool = True
    ) -> None:
        """Set browser download directory.

        Works with ``Open Available Browser``, ``Open Chrome Browser`` and
        ``Open Headless Chrome Browser`` keywords.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Define Download Directory for Browser
                Set Download Directory    /path/to/download/location

            *** Keyword ***
            Open PDF Instead of Download
                Set Download Directory
                ...    /path/to/download/location
                ...    download_pdf=${FALSE}

        :param directory: target directory for downloads, defaults to None which means
                         that setting is removed
        :param download_pdf: if `True` then PDF is downloaded instead of shown with
                         browser's internal viewer; default is `True`
        """
        if directory is None:
            self.logger.info("Download directory set back to browser default setting")
            self.download_preferences = {}
        else:
            download_directory = str(Path(directory))
            self.logger.info("Download directory set to: %s", download_directory)
            self.download_preferences = {
                "download.default_directory": download_directory,
                "plugins.always_open_pdf_externally": download_pdf,
                "download.directory_upgrade": True,
                "download.prompt_for_download": False,
            }

    @keyword
    def highlight_elements(
        self,
        locator: str,
        width: str = "2px",
        style: str = "dotted",
        color: str = "blue",
    ):
        """
        Highlight all matching elements by locator.

        Highlighting is done by adding a colored outline
        around the elements with CSS styling.

        ``locator``  element locator
        ``width``    highlight outline width
        ``style``    highlight outline style
        ``color``    highlight outline color

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Highlight H2 Elements
                Highlight Elements    xpath://h2
        """
        elements = self.find_elements(locator)
        attribute_name = "rpaframework-highlight"

        def inject_style():
            css = (
                "\n"
                f"[{attribute_name}] {{\n"
                f"  outline: {width} {style} {color};\n"
                "}\n"
            )
            script = (
                "var node = document.createElement('style');\n"
                "node.setAttribute('data-name', 'rpaframework');\n"
                f"node.innerHTML=`{css}`\n"
                "document.head.appendChild(node);"
            )
            self.driver.execute_script(script)

        def add_highlight_attribute_to_elements():
            script = "".join(
                f'arguments[{idx}].setAttribute("{attribute_name}", "");'
                for idx in range(len(elements))
            )
            self.driver.execute_script(script, *elements)

        inject_style()
        add_highlight_attribute_to_elements()

    @keyword
    def clear_all_highlights(self):
        """Remove all highlighting made by ``Highlight Elements``.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Remove Highlights
                Clear All Highlights
        """
        attribute_name = "rpaframework-highlight"

        elements = self.driver.find_elements_by_css_selector(f"[{attribute_name}]")
        script = "".join(
            f'arguments[{idx}].removeAttribute("{attribute_name}");'
            for idx in range(len(elements))
        )
        self.driver.execute_script(script, *elements)

    @keyword
    def print_to_pdf(self, output_path: str = None, params: dict = None):
        """
        Print the current page to a PDF document using Chromium devtools.

        For supported parameters see:
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-printToPDF

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Save Page as PDF
                &{print_parameters}=    Create Dictionary
                ...    landscape=False
                ...    displayHeaderFooter=False
                ...    printBackground=True
                ...    preferCSSPageSize=True
                Print To Pdf    ${OUTPUT_DIR}    ${print_parameters}

        :param output_path: filepath for the generated pdf. By default it is saved to
          the output folder with name `out.pdf`.
        :param params: parameters for the Chrome print method. By default uses values:
         {
             "landscape": False,
             "displayHeaderFooter": False,
             "printBackground": True,
             "preferCSSPageSize": True
         }
         :return: path to the printed PDF file
        """
        if "chrom" not in self.driver.name:
            raise NotImplementedError("PDF printing works only with Chrome/Chromium")

        default_params = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
        }

        try:
            output_dir = BuiltIn().get_variable_value("${OUTPUT_DIR}", "output")
        except robot.libraries.BuiltIn.RobotNotRunningError:
            output_dir = "output"
        default_output = f"{output_dir}/out.pdf"
        output_path = output_path or default_output

        params = params or default_params
        result = self._send_command_and_get_result("Page.printToPDF", params)
        pdf = base64.b64decode(result["data"])

        with open(output_path, "wb") as f:
            f.write(pdf)

        return output_path

    @keyword
    def execute_cdp(self, command, parameters):
        """
        Executes Chrome DevTools Protocol commands

        Works only with Chrome/Chromium

        For more information, available commands and parameters, see:
        https://chromedevtools.github.io/devtools-protocol/

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Keyword ***
            Execute Chrome DevTools Protocol and Navigate to Webpage
                Open Chrome Browser    about:blank    headless=True
                &{params}    Create Dictionary    useragent=Chrome/83.0.4103.53
                Execute CDP    Network.setUserAgentOverride    ${params}
                Go To    https://robocorp.com

        :param command: command to execute as string
        :param parameters: parameters for command as a dictionary
        :return: string of the returned response from the execution
        """
        if "chrom" not in self.driver.name:
            raise NotImplementedError(
                "Executing Chrome DevTools Protocol commands "
                "works only with Chrome/Chromium"
            )
        return self._send_command_and_get_result(command, parameters)

    def _send_command_and_get_result(self, cmd, params):
        resource = (
            f"session/{self.driver.session_id}/chromium/send_command_and_get_result"
        )
        # pylint: disable=protected-access
        url = f"{self.driver.command_executor._url}/{resource}"
        body = json.dumps({"cmd": cmd, "params": params})
        response = self.driver.command_executor._request("POST", url, body)

        return response.get("value")
