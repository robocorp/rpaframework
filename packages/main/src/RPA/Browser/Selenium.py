# pylint: disable=too-many-lines
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
from typing import Any, Optional, List, Union
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


class Selenium(SeleniumLibrary):
    """Browser is a web testing library for Robot Framework,
    based on the popular SeleniumLibrary.

    It uses the Selenium WebDriver modules internally to
    control a web browser. See http://seleniumhq.org for more information
    about Selenium in general.

    = Locating elements =

    All keywords in the browser library that need to interact with an element
    on a web page take an argument typically named ``locator`` that specifies
    how to find the element. Most often the locator is given as a string
    using the locator syntax described below, but `using WebElements` is
    possible too.

    == Locator syntax ==

    Finding elements can be done using different strategies
    such as the element id, XPath expressions, or CSS selectors. The strategy
    can either be explicitly specified with a prefix or the strategy can be
    implicit.

    === Default locator strategy ===

    By default, locators are considered to use the keyword specific default
    locator strategy. All keywords support finding elements based on ``id``
    and ``name`` attributes, but some keywords support additional attributes
    or other values that make sense in their context. For example, `Click
    Link` supports the ``href`` attribute and the link text in addition
    to the normal ``id`` and ``name``.

    Examples:

    | `Click Element` | example | # Match based on ``id`` or ``name``.            |
    | `Click Link`    | example | # Match also based on link text and ``href``.   |
    | `Click Button`  | example | # Match based on ``id``, ``name`` or ``value``. |

    If a locator accidentally starts with a prefix recognized as `explicit
    locator strategy` or `implicit XPath strategy`, it is possible to use
    the explicit ``default`` prefix to enable the default strategy.

    Examples:

    | `Click Element` | name:foo         | # Find element with name ``foo``.               |
    | `Click Element` | default:name:foo | # Use default strategy with value ``name:foo``. |
    | `Click Element` | //foo            | # Find element using XPath ``//foo``.           |
    | `Click Element` | default: //foo   | # Use default strategy with value ``//foo``.    |

    === Explicit locator strategy ===

    The explicit locator strategy is specified with a prefix using either
    syntax ``strategy:value`` or ``strategy=value``. The former syntax
    is preferred because the latter is identical to Robot Framework's
    [http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#named-argument-syntax|
    named argument syntax] and that can cause problems. Spaces around
    the separator are ignored, so ``id:foo``, ``id: foo`` and ``id : foo``
    are all equivalent.

    Locator strategies that are supported by default are listed in the table
    below. In addition to them, it is possible to register `custom locators`.

    | = Strategy = |          = Match based on =         |         = Example =            |
    | id           | Element ``id``.                     | ``id:example``                 |
    | name         | ``name`` attribute.                 | ``name:example``               |
    | identifier   | Either ``id`` or ``name``.          | ``identifier:example``         |
    | class        | Element ``class``.                  | ``class:example``              |
    | tag          | Tag name.                           | ``tag:div``                    |
    | xpath        | XPath expression.                   | ``xpath://div[@id="example"]`` |
    | css          | CSS selector.                       | ``css:div#example``            |
    | dom          | DOM expression.                     | ``dom:document.images[5]``     |
    | link         | Exact text a link has.              | ``link:The example``           |
    | partial link | Partial link text.                  | ``partial link:he ex``         |
    | sizzle       | Sizzle selector deprecated.         | ``sizzle:div.example``         |
    | jquery       | jQuery expression.                  | ``jquery:div.example``         |
    | default      | Keyword specific default behavior.  | ``default:example``            |

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

    | `Click Element` | id:foo                      | # Element with id 'foo'. |
    | `Click Element` | css:div#foo h1              | # h1 element under div with id 'foo'. |
    | `Click Element` | xpath: //div[@id="foo"]//h1 | # Same as the above using XPath, not CSS. |
    | `Click Element` | xpath: //*[contains(text(), "example")] | # Element containing text 'example'. |

    *NOTE:*

    - Using the ``sizzle`` strategy or its alias ``jquery`` requires that
      the system under test contains the jQuery library.

    === Implicit XPath strategy ===

    If the locator starts with ``//`` or ``(//``, the locator is considered
    to be an XPath expression. In other words, using ``//div`` is equivalent
    to using explicit ``xpath://div``.

    Examples:

    | `Click Element` | //div[@id="foo"]//h1 |
    | `Click Element` | (//div)[2]           |

    === Chaining locators ===

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
    | `Click Element` | css:.bar >> xpath://a | # To find a link which is present inside an element with class "bar" |

    List examples:
    | ${locator_list} =             | `Create List`   | css:div#div_id            | xpath://*[text(), " >> "] |
    | `Page Should Contain Element` | ${locator_list} |                           |                           |
    | ${element} =                  | Get WebElement  | xpath://*[text(), " >> "] |                           |
    | ${locator_list} =             | `Create List`   | css:div#div_id            | ${element}                |
    | `Page Should Contain Element` | ${locator_list} |                           |                           |

    == Using WebElements ==

    In addition to specifying a locator as a string, it is possible to use
    Selenium's WebElement objects. This requires first getting a WebElement,
    for example, by using the `Get WebElement` keyword.

    | ${elem} =       | `Get WebElement` | id:example |
    | `Click Element` | ${elem}          |            |

    == Custom locators ==

    If more complex lookups are required than what is provided through the
    default locators, custom lookup strategies can be created. Using custom
    locators is a two part process. First, create a keyword that returns
    a WebElement that should be acted on:

    | Custom Locator Strategy | [Arguments] | ${browser} | ${locator} | ${tag} | ${constraints} |
    |   | ${element}= | Execute Javascript | return window.document.getElementById('${locator}'); |
    |   | [Return] | ${element} |

    This keyword is a reimplementation of the basic functionality of the
    ``id`` locator where ``${browser}`` is a reference to a WebDriver
    instance and ``${locator}`` is the name of the locator strategy. To use
    this locator, it must first be registered by using the
    `Add Location Strategy` keyword:

    | `Add Location Strategy` | custom | Custom Locator Strategy |

    The first argument of `Add Location Strategy` specifies the name of
    the strategy and it must be unique. After registering the strategy,
    the usage is the same as with other locators:

    | `Click Element` | custom:example |

    See the `Add Location Strategy` keyword for more details.

    = Browser and Window =

    There is different conceptual meaning when this library talks
    about windows or browsers. This chapter explains those differences.

    == Browser ==

    When `Open Browser` or `Create WebDriver` keyword is called, it
    will create a new Selenium WebDriver instance by using the
    [https://www.seleniumhq.org/docs/03_webdriver.jsp|Selenium WebDriver]
    API. In this library's terms, a new browser is created. It is
    possible to start multiple independent browsers (Selenium Webdriver
    instances) at the same time, by calling `Open Browser` or
    `Create WebDriver` multiple times. These browsers are usually
    independent of each other and do not share data like cookies,
    sessions or profiles. Typically when the browser starts, it
    creates a single window which is shown to the user.

    == Window ==

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
    | BrowserA
    |            Window 1  (location=https://robotframework.org/)
    |            Window 2  (location=https://robocon.io/)
    |            Window 3  (location=https://github.com/robotframework/)
    |
    | BrowserB
    |            Window 1  (location=https://github.com/)

    Example:
    | `Open Browser`       | https://robotframework.org         | ${BROWSER}       | alias=BrowserA   | # BrowserA with first window is opened.                                       |
    | `Execute Javascript` | window.open()                      |                  |                  | # In BrowserA second window is opened.                                        |
    | `Switch Window`      | locator=NEW                        |                  |                  | # Switched to second window in BrowserA                                       |
    | `Go To`              | https://robocon.io                 |                  |                  | # Second window navigates to robocon site.                                    |
    | `Execute Javascript` | window.open()                      |                  |                  | # In BrowserA third window is opened.                                         |
    | ${handle}            | `Switch Window`                    | locator=NEW      |                  | # Switched to third window in BrowserA                                        |
    | `Go To`              | https://github.com/robotframework/ |                  |                  | # Third windows goes to robot framework github site.                          |
    | `Open Browser`       | https://github.com                 | ${BROWSER}       | alias=BrowserB   | # BrowserB with first windows is opened.                                      |
    | ${location}          | `Get Location`                     |                  |                  | # ${location} is: https://www.github.com                                      |
    | `Switch Window`      | ${handle}                          | browser=BrowserA |                  | # BrowserA second windows is selected.                                        |
    | ${location}          | `Get Location`                     |                  |                  | # ${location} = https://robocon.io/                                           |
    | @{locations 1}       | `Get Locations`                    |                  |                  | # By default, lists locations under the currectly active browser (BrowserA).   |
    | @{locations 2}       | `Get Locations`                    |  browser=ALL     |                  | # By using browser=ALL argument keyword list all locations from all browsers. |

    The above example, @{locations 1} contains the following items:
    https://robotframework.org/, https://robocon.io/ and
    https://github.com/robotframework/'. The @{locations 2}
    contains the following items: https://robotframework.org/,
    https://robocon.io/, https://github.com/robotframework/'
    and 'https://github.com/.

    = Timeouts, waits, and delays =

    This section discusses different ways on how to wait for elements to
    appear on web pages and to slow down execution speed otherwise.
    It also explains the `time format` that can be used when setting various
    timeouts, waits, and delays.

    == Timeout ==

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

    == Implicit wait ==

    Implicit wait specifies the maximum time how long Selenium waits when
    searching for elements. It can be set by using the `Set Selenium Implicit
    Wait` keyword or with the ``implicit_wait`` argument when `importing`
    the library. See [https://www.seleniumhq.org/docs/04_webdriver_advanced.jsp|Selenium documentation]
    for more information about this functionality.

    See `time format` below for supported syntax.

    == Selenium speed ==

    Selenium execution speed can be slowed down globally by using `Set
    Selenium speed` keyword. This functionality is designed to be used for
    demonstrating or debugging purposes. Using it to make sure that elements
    appear on a page is not a good idea. The above-explained timeouts
    and waits should be used instead.

    See `time format` below for supported syntax.

    == Time format ==

    All timeouts and waits can be given as numbers considered seconds
    (e.g. ``0.5`` or ``42``) or in Robot Framework's time syntax
    (e.g. ``1.5 seconds`` or ``1 min 30 s``). For more information about
    the time syntax see the
    [http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#time-format|Robot Framework User Guide].

    = Run-on-failure functionality =

    This library has a handy feature that it can automatically execute
    a keyword if any of its own keywords fails. By default, it uses the
    `Capture Page Screenshot` keyword, but this can be changed either by
    using the `Register Keyword To Run On Failure` keyword or with the
    ``run_on_failure`` argument when `importing` the library. It is
    possible to use any keyword from any imported library or resource file.

    The run-on-failure functionality can be disabled by using a special value
    ``NOTHING`` or anything considered false (see `Boolean arguments`)
    such as ``NONE``.

    = Auto closing browser =

    By default browser instances created during task execution are closed
    at the end of the task. This can be prevented with the ``auto_close``
    argument when `importing` the library.

    Value needs to be set to ``False`` or anything considered false (see `Boolean arguments`).

    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"

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
        """Get SeleniumTestability plugin status"""
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
