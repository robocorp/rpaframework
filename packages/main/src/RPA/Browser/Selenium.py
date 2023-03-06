# pylint: disable=too-many-lines
import atexit
import base64
import json
import logging
import os
import platform
import time
import traceback
import urllib.parse
import webbrowser
from collections import OrderedDict
from functools import partial
from itertools import product
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from selenium import webdriver as selenium_webdriver
from selenium.webdriver import ChromeOptions, FirefoxProfile, IeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.options import ArgOptions
from selenium.webdriver.ie.webdriver import WebDriver as IeWebDriver
from SeleniumLibrary import EMBED, SeleniumLibrary
from SeleniumLibrary.base import keyword
from SeleniumLibrary.errors import ElementNotFound
from SeleniumLibrary.keywords import (
    AlertKeywords,
    BrowserManagementKeywords,
    ScreenshotKeywords,
)
from SeleniumLibrary.keywords.webdrivertools import SeleniumOptions, WebDriverCreator

from RPA.core import notebook
from RPA.core import webdriver as core_webdriver
from RPA.core.locators import BrowserLocator, LocatorsDatabase
from RPA.Robocorp.utils import get_output_dir


OptionsType = Union[ArgOptions, str, Dict[str, Union[str, List, Dict]]]
AliasType = Union[str, int]


def html_table(header, rows):
    """Create HTML table that can be used for logging."""
    output = '<div class="doc"><table>'
    output += "<tr>" + "".join(f"<th>{name}</th>" for name in header) + "</tr>"
    for row in rows:
        output += "<tr>" + "".join(f"<td>{name}</td>" for name in row) + "</tr>"
    output += "</table></div>"
    return output


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
    """Overridden keywords for browser management."""

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
        options: Optional[OptionsType] = None,
        service_log_path: Optional[str] = None,
        executable_path: Optional[str] = None,
    ) -> str:
        url = ensure_scheme(url, self._default_scheme)
        if options:
            options: ArgOptions = self.ctx.normalize_options(options, browser=browser)
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
    """SeleniumLibrary is a web testing library for Robot Framework.

    This document explains how to use keywords provided by SeleniumLibrary.
    For information about installation, support, and more, please visit the
    [https://github.com/robotframework/SeleniumLibrary|project pages].
    For more information about Robot Framework, see https://robotframework.org.

    SeleniumLibrary uses the Selenium WebDriver modules internally to
    control a web browser. See https://www.selenium.dev/ for more information
    about Selenium in general and SeleniumLibrary README.rst
    [https://github.com/robotframework/SeleniumLibrary#browser-drivers|Browser drivers chapter]
    for more details about WebDriver binary installation.

    = Locating elements =

    All keywords in SeleniumLibrary that need to interact with an element
    on a web page take an argument typically named ``locator`` that specifies
    how to find the element. Most often the locator is given as a string
    using the locator syntax described below, but `using WebElements` is
    possible too.

    == Locator syntax ==

    SeleniumLibrary supports finding elements based on different strategies
    such as the element id, XPath expressions, or CSS selectors. The strategy
    can either be explicitly specified with a prefix or the strategy can be
    implicit.

    === Default locator strategy ===

    By default, locators are considered to use the keyword specific default
    locator strategy. All keywords support finding elements based on ``id``
    and ``name`` attributes, but some keywords support additional attributes
    or other values that make sense in their context. For example, `Click
    Link` supports the ``href`` attribute and the link text and addition
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
    [https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#named-argument-syntax|
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
    | data         | Element ``data-*`` attribute        | ``data:id:my_id``              |
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

    - The ``strategy:value`` syntax is only supported by SeleniumLibrary 3.0
      and newer.
    - Using the ``sizzle`` strategy or its alias ``jquery`` requires that
      the system under test contains the jQuery library.
    - Prior to SeleniumLibrary 3.0, table related keywords only supported
      ``xpath``, ``css`` and ``sizzle/jquery`` strategies.
    - ``data`` strategy is conveniance locator that will construct xpath from the parameters.
      If you have element like `<div data-automation="automation-id-2">`, you locate the element via
      ``data:automation:automation-id-2``. This feature was added in SeleniumLibrary 5.2.0

    === Implicit XPath strategy ===

    If the locator starts with ``//``  or multiple opening parenthesis in front
    of the ``//``, the locator is considered to be an XPath expression. In other
    words, using ``//div`` is equivalent to using explicit ``xpath://div`` and
    ``((//div))`` is equivalent to using explicit ``xpath:((//div))``

    Examples:

    | `Click Element` | //div[@id="foo"]//h1 |
    | `Click Element` | (//div)[2]           |

    The support for the ``(//`` prefix is new in SeleniumLibrary 3.0.
    Supporting multiple opening parenthesis is new in SeleniumLibrary 5.0.

    === Chaining locators ===

    It is possible chain multiple locators together as single locator. Each chained locator must start with locator
    strategy. Chained locators must be separated with single space, two greater than characters and followed with
    space. It is also possible mix different locator strategies, example css or xpath. Also a list can also be
    used to specify multiple locators. This is useful, is some part of locator would match as the locator separator
    but it should not. Or if there is need to existing WebElement as locator.

    Although all locators support chaining, some locator strategies do not abey the chaining. This is because
    some locator strategies use JavaScript to find elements and JavaScript is executed for the whole browser context
    and not for the element found be the previous locator. Chaining is supported by locator strategies which
    are based on Selenium API, like `xpath` or `css`, but example chaining is not supported by `sizzle` or `jquery

    Examples:
    | `Click Element` | css:.bar >> xpath://a | # To find a link which is present after an element with class "bar" |

    List examples:
    | ${locator_list} =             | `Create List`   | css:div#div_id            | xpath://*[text(), " >> "] |
    | `Page Should Contain Element` | ${locator_list} |                           |                           |
    | ${element} =                  | Get WebElement  | xpath://*[text(), " >> "] |                           |
    | ${locator_list} =             | `Create List`   | css:div#div_id            | ${element}                |
    | `Page Should Contain Element` | ${locator_list} |                           |                           |

    Chaining locators in new in SeleniumLibrary 5.0

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

    There is different conceptual meaning when SeleniumLibrary talks
    about windows or browsers. This chapter explains those differences.

    == Browser ==

    When `Open Browser` or `Create WebDriver` keyword is called, it
    will create a new Selenium WebDriver instance by using the
    [https://www.seleniumhq.org/docs/03_webdriver.jsp|Selenium WebDriver]
    API. In SeleniumLibrary terms, a new browser is created. It is
    possible to start multiple independent browsers (Selenium Webdriver
    instances) at the same time, by calling `Open Browser` or
    `Create WebDriver` multiple times. These browsers are usually
    independent of each other and do not share data like cookies,
    sessions or profiles. Typically when the browser starts, it
    creates a single window which is shown to the user.

    == Window ==

    Windows are the part of a browser that loads the web site and presents
    it to the user. All content of the site is the content of the window.
    Windows are children of a browser. In SeleniumLibrary browser is a
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

    This section discusses different ways how to wait for elements to
    appear on web pages and to slow down execution speed otherwise.
    It also explains the `time format` that can be used when setting various
    timeouts, waits, and delays.

    == Timeout ==

    SeleniumLibrary contains various keywords that have an optional
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
    the library. See [https://www.seleniumhq.org/docs/04_webdriver_advanced.jsp|
    Selenium documentation] for more information about this functionality.

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
    [https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#time-format|Robot Framework User Guide].

    = Run-on-failure functionality =

    SeleniumLibrary has a handy feature that it can automatically execute
    a keyword if any of its own keywords fails. By default, it uses the
    `Capture Page Screenshot` keyword, but this can be changed either by
    using the `Register Keyword To Run On Failure` keyword or with the
    ``run_on_failure`` argument when `importing` the library. It is
    possible to use any keyword from any imported library or resource file.

    The run-on-failure functionality can be disabled by using a special value
    ``NOTHING`` or anything considered false (see `Boolean arguments`)
    such as ``NONE``.

    = Boolean arguments =

    Starting from 5.0 SeleniumLibrary relies on Robot Framework to perform the
    boolean conversion based on keyword arguments [https://docs.python.org/3/library/typing.html|type hint].
    More details in Robot Framework
    [https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#supported-conversions|user guide]

    Please note SeleniumLibrary 3 and 4 did have own custom methods to covert
    arguments to boolean values.

    = EventFiringWebDriver =

    The SeleniumLibrary offers support for
    [https://seleniumhq.github.io/selenium/docs/api/py/webdriver_support/selenium.webdriver.support.event_firing_webdriver.html#module-selenium.webdriver.support.event_firing_webdriver|EventFiringWebDriver].
    See the Selenium and SeleniumLibrary
    [https://github.com/robotframework/SeleniumLibrary/blob/master/docs/extending/extending.rst#EventFiringWebDriver|EventFiringWebDriver support]
    documentation for further details.

    EventFiringWebDriver is new in SeleniumLibrary 4.0

    = Thread support =

    SeleniumLibrary is not thread-safe. This is mainly due because the underlying
    [https://github.com/SeleniumHQ/selenium/wiki/Frequently-Asked-Questions#q-is-webdriver-thread-safe|
    Selenium tool is not thread-safe] within one browser/driver instance.
    Because of the limitation in the Selenium side, the keywords or the
    API provided by the SeleniumLibrary is not thread-safe.

    = Plugins =

    SeleniumLibrary offers plugins as a way to modify and add library keywords and modify some of the internal
    functionality without creating a new library or hacking the source code. See
    [https://github.com/robotframework/SeleniumLibrary/blob/master/docs/extending/extending.rst#Plugins|plugin API]
    documentation for further details.

    Plugin API is new SeleniumLibrary 4.0

    = Auto closing browser =

    By default browser instances created during task execution are closed
    at the end of the task. This can be prevented with the ``auto_close``
    argument when `importing` the library.

    Value needs to be set to ``False`` or anything considered false (see `Boolean arguments`).

    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"

    BROWSER_NAMES = {
        **WebDriverCreator.browser_names,
        "chromiumedge": WebDriverCreator.browser_names["edge"],
    }
    AVAILABLE_OPTIONS = {
        # Supporting options only for a specific range of browsers.
        "chrome": selenium_webdriver.ChromeOptions,
        "firefox": selenium_webdriver.FirefoxOptions,
        "edge": selenium_webdriver.EdgeOptions,
        "chromiumedge": selenium_webdriver.EdgeOptions,
        "ie": selenium_webdriver.IeOptions,
    }
    AVAILABLE_SERVICES = {
        # Supporting services only for a specific range of browsers.
        "chrome": selenium_webdriver.chrome.service.Service,
        "firefox": selenium_webdriver.firefox.service.Service,
        "edge": selenium_webdriver.edge.service.Service,
        "chromiumedge": selenium_webdriver.edge.service.Service,
        "safari": selenium_webdriver.safari.service.Service,
        "ie": selenium_webdriver.ie.service.Service,
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

        # Add inherit/overridden library keywords
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
        """Register cleanup function for leftover webdrivers & browsers on process
        exit.
        """

        def stop_drivers():
            if self.auto_close:
                self._quit_all_drivers()
            elif platform.system() == "Windows":
                # NOTE: On Windows, the webdriver executable keeps hanging and prevents
                #  "rcc" to close even when the Python process exits.
                self._quit_all_drivers(driver_only=True)

        atexit.register(stop_drivers)

    def _quit_all_drivers(self, driver_only: bool = False):
        # With `driver_only` on, we'll close just the drivers, but still leave the
        #  browser window open.
        connections = self._drivers._connections  # pylint: disable=protected-access
        for driver in connections:
            try:
                if driver_only:
                    if isinstance(driver, IeWebDriver):
                        service = driver.iedriver
                    else:
                        service = driver.service
                    # A `service.stop()` will hang here, so killing the process
                    #  directly is the only way.
                    service.process.kill()
                else:
                    driver.quit()
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.debug("Encountered error during auto-close: %s", exc)

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
        options: Optional[OptionsType] = None,
        port: Optional[int] = None,
    ) -> AliasType:
        # pylint: disable=C0301
        """Attempts to open a browser on the user's device from a set of
        supported browsers. Automatically downloads a corresponding webdriver
        if none is already installed.

        Currently supported browsers: %s

        Optionally can be given a ``url`` as the first argument,
        to open the browser directly to the given page.

        Returns either a generated index or a custom ``alias`` for the
        browser instance. The returned value can be used to refer to that
        specific browser instance in other keywords.

        If the browser should start in a maximized window, this can be
        enabled with the argument ``maximized``, but is disabled by default.

        For certain applications it might also be required to force a
        certain user-agent string for Selenium, which can be overridden
        with the ``user_agent`` argument.

        WebDriver creation can be customized with ``options``. This accepts a class
        instance (e.g. ``ChromeOptions``), a string like
        `add_argument("--incognito");set_capability("acceptInsecureCerts", True)` or
        even a simple dictionary like:
        `{"arguments": ["--incognito"], "capabilities": {"acceptInsecureCerts": True}}`

        A custom ``port`` can be provided to start the browser without a random one.
        Make sure you provide every time a unique system-available local port if you
        plan to have multiple such browsers running in parallel.

        For incompatible web apps designed to work in Internet Explorer only, Edge can
        run in IE mode by simply setting `ie` in the ``browser_selection`` param.
        Robot example: https://github.com/robocorp/example-ie-mode-edge

        Example:

        | Open Available Browser | https://www.robocorp.com |
        | ${index}= | Open Available Browser | ${URL} | browser_selection=opera,firefox |
        | Open Available Browser | ${URL} | headless=True | alias=HeadlessBrowser |
        | Open Available Browser | ${URL} | options=add_argument("user-data-dir=path/to/data");add_argument("--incognito") |
        | Open Available Browser | ${URL} | port=${8888} |

        == Browser order ==

        The default order of supported browsers is based on the operating system
        and is as follows:

        | Platform    | Default order                         |
        | ``Windows`` | Chrome, Firefox, ChromiumEdge         |
        | ``Linux``   | Chrome, Firefox, ChromiumEdge         |
        | ``Darwin``  | Chrome, Firefox, ChromiumEdge, Safari |

        The order can be overridden with a custom list by using the argument
        ``browser_selection``. The argument can be either a comma-separated
        string or a list object.

        Example:

        | Open Available Browser | ${URL} | browser_selection=ie |

        == Webdriver download ==

        The library can (if requested) automatically download webdrivers
        for all the supported browsers. This can be controlled with the argument
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
        be controlled with ``profile_path`` and ``profile_name`` respectively. Keep in
        mind that the ``profile_path`` ends usually in "Chrome", "User Data" or
        "google-chrome" and the ``profile_name`` is a directory relative to
        ``profile_path``, usually named "Profile 1", "Profile 2" etc. (and not as your
        visible name in the Chrome browser)

        Examples:

        | Open Available Browser | https://www.robocorp.com | use_profile=${True} |
        | Open Available Browser | https://www.robocorp.com | use_profile=${True} | profile_name=Default |
        | Open Available Browser | https://www.robocorp.com | use_profile=${True} | profile_name=Profile 2 |
        | Open Available Browser | https://www.robocorp.com | use_profile=${True} | profile_name=Profile 1 | profile_path=path/to/custom/user_data_dir |

        Profile preferences can be further overridden with the ``preferences``
        argument by giving a dictionary of key/value pairs.

        Chrome can additionally connect through a ``proxy``, which
        should be given as either local or remote address.
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
                    options,
                    port,
                    url,
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

    open_available_browser.__doc__ %= ", ".join(AVAILABLE_SERVICES)

    def _arg_browser_selection(self, browser_selection: Any) -> List:
        """Parse argument for browser selection."""
        if str(browser_selection).strip().lower() == "auto":
            order = core_webdriver.get_browser_order()
        else:
            order = (
                browser_selection
                if isinstance(browser_selection, list)
                else [browser.strip() for browser in browser_selection.split(",")]
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

    def _set_chrome_options(
        self,
        kwargs: dict,
        options: ChromeOptions,
        use_profile: bool = False,
        profile_name: Optional[str] = None,
        profile_path: Optional[str] = None,
        preferences: Optional[dict] = None,
        proxy: str = None,
    ):
        if proxy:
            options.add_argument(f"--proxy-server={proxy}")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--no-sandbox")
        default_preferences = {
            "safebrowsing.enabled": True,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        }
        options.add_experimental_option(
            "prefs",
            {
                **default_preferences,
                **self.download_preferences,
                **(preferences or {}),
            },
        )
        options.add_experimental_option(
            "excludeSwitches", ["enable-logging", "enable-automation"]
        )
        if use_profile:
            self._set_user_profile(options, profile_path, profile_name)
        if self.logger.isEnabledFor(logging.DEBUG):
            # Deprecated params, but no worries as they get popped then bundled in a
            #  `Service` instance inside of the `self._create_webdriver` method.
            kwargs["service_log_path"] = "chromedriver.log"
            kwargs["service_args"] = ["--verbose"]

    def _set_ie_options(self, options: IeOptions, *, url: Optional[str]):
        binary_location = getattr(options, "binary_location", None)
        if binary_location:
            options.edge_executable_path = binary_location
        # An invalid default URL will make the automation freeze.
        options.initial_browser_url = (
            options.initial_browser_url or url or "https://robocorp.com/"
        )

    def _set_option(
        self, name: str, values: Union[str, List, Dict], *, method: Callable
    ):
        if name == "arguments":
            if isinstance(values, str):
                values = [value.strip() for value in values.split(",")]
            for value in values:
                self.logger.debug("Setting argument: %s", value)
                method(value)
        elif name == "capabilities":
            if isinstance(values, str):
                values, _values = {}, values
                for item in _values.split(","):
                    key, val = item.strip().split(":")
                    values[key.strip()] = val.strip()
            for key, val in values.items():
                self.logger.debug("Setting capability: %s=%s", key, val)
                method(key, val)
        elif name == "binary_location":
            self.logger.debug("Setting binary location: %s", values)
            method(values)

    def normalize_options(
        self, options: Optional[OptionsType], *, browser: str
    ) -> ArgOptions:
        """Normalize provided `options` to a `<Browser>Options` instance."""
        browser = browser.lower()

        # String or object based provided options, solved by the wrapped library.
        if isinstance(options, (ArgOptions, str)):
            return SeleniumOptions().create(self.BROWSER_NAMES[browser], options)

        BrowserOptions = self.AVAILABLE_OPTIONS.get(browser)
        if not BrowserOptions:
            raise ValueError(
                f"{browser!r} browser options other than string/object aren't supported"
            )

        options_obj = BrowserOptions()
        if isinstance(options, dict):
            option_method_map = {
                "arguments": options_obj.add_argument,
                "capabilities": options_obj.set_capability,
                "binary_location": lambda path: setattr(
                    options_obj, "binary_location", path
                ),
            }
            for name, values in options.items():
                if name not in option_method_map:
                    raise TypeError(
                        f"Option type {name!r} not supported, choose from "
                        f"{list(option_method_map)} or try providing them as string "
                        "or object"
                    )
                method = option_method_map[name]
                self._set_option(name, values, method=method)

        return options_obj

    def _get_driver_args(  # noqa: C901
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
        options: Optional[OptionsType] = None,
        port: Optional[int] = None,
        url: Optional[str] = None,
    ) -> Tuple[dict, Any]:
        """Get browser and webdriver arguments for given options."""
        browser = browser.lower()
        if browser not in self.AVAILABLE_OPTIONS:
            return {}, []

        options: ArgOptions = self.normalize_options(options, browser=browser)
        headless = headless or bool(int(os.getenv("RPA_HEADLESS_MODE", "0")))
        if headless:
            self._set_headless_options(browser, options)
        if maximized:
            options.add_argument("--start-maximized")
        if user_agent:
            options.add_argument(f"user-agent={user_agent}")

        kwargs = {}
        if port:
            # Deprecated kwarg which will be transferred into a service instance.
            kwargs["port"] = int(port)
        if browser == "chrome":
            self._set_chrome_options(
                kwargs,
                options,
                use_profile=use_profile,
                profile_name=profile_name,
                profile_path=profile_path,
                preferences=preferences,
                proxy=proxy,
            )
        elif use_profile:
            self.logger.warning("Profiles are supported with Chrome only")
        if browser == "ie":
            self._set_ie_options(options, url=url)

        try:
            path = options.binary_location or None
        except AttributeError:
            path = None
        if path:
            self.logger.warning(
                f"The custom provided browser ({path}) might be "
                "incompatible with the default downloaded webdriver. Use "
                "``Open Browser`` with these `options` and a compatible "
                "`executable_path` if running into issues."
            )

        kwargs["options"] = options  # legitimate webdriver kwarg separate from service
        return kwargs, options.arguments

    def _set_headless_options(self, browser: str, options: ArgOptions) -> None:
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

        options.headless = True
        options.add_argument("--disable-gpu")

        if browser.lower() == "chrome":
            options.add_argument("--window-size=1440,900")

    def _set_user_profile(
        self,
        options: ArgOptions,
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
    ) -> AliasType:
        """Create a webdriver instance with given options.

        If webdriver download is requested, a cached version will be used if exists.
        """

        def _create_driver(path: Optional[str] = None) -> AliasType:
            # Prepare webdriver's service instance keyword arguments.
            service_kwargs = {
                # Deprecated params if passed directly to the `WebDriver` class.
                "service_args": None,
                "service_log_path": None,
                "port": 0,
            }
            service_args = None  # for unsupported manual injection
            for name, default in service_kwargs.items():
                service_kwargs[name] = kwargs.pop(name, default)
            service_kwargs["log_path"] = service_kwargs.pop("service_log_path")
            if path:
                service_kwargs["executable_path"] = path

            # Instantiate the right service to be passed during the webdriver creation.
            Service = self.AVAILABLE_SERVICES[browser.lower()]
            if Service is selenium_webdriver.safari.service.Service:
                service_kwargs.pop("log_path")  # not supported at all
            elif Service is selenium_webdriver.ie.service.Service:
                service_kwargs["log_file"] = service_kwargs.pop("log_path")
                service_args = service_kwargs.pop("service_args")
            service = Service(**service_kwargs)
            if service_args:
                service.service_args.extend(service_args)

            lib = BrowserManagementKeywords(self)
            # Capitalize browser name just to ensure it works if passed as lower case.
            # NOTE: But don't break a browser name like "ChromiumEdge".
            cap_browser = browser[0].upper() + browser[1:]
            kwargs["service"] = service
            return lib.create_webdriver(cap_browser, alias, **kwargs)

        # No download requested.
        if not download:
            return _create_driver()

        # Download web driver. (caching is tackled internally)
        driver_path = core_webdriver.download(browser)
        return _create_driver(path=driver_path)

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
    ) -> AliasType:
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
    def attach_chrome_browser(
        self, port: int, alias: Optional[str] = None
    ) -> AliasType:
        """Attach to an existing instance of Chrome or Chromium.

        Requires that the browser was started with the command line
        option ``--remote-debugging-port=<port>``, where port is any
        4-digit number not being used by other applications.

        *Note.* The first Chrome instance on the system needs to be
        started with this command line option or this won't have an effect.

        That port can then be used to connect using this keyword.

        Example:

        | Attach Chrome Browser | port=9222 |
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
    def open_headless_chrome_browser(self, url: str) -> AliasType:
        """Open Chrome browser in headless mode.

        ``url`` URL to open

        Example:

        | ${idx} | Open Headless Chrome Browser | https://www.google.com |
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

        ``locator`` if defined, take element screenshot, if not takes page screenshot

        ``filename`` filename for the screenshot, by default creates file `screenshot-timestamp-element/page.png`
        if set to `None` then file is not saved at all

        Example:

        | Screenshot | locator=//img[@alt="Google"] | filename=locator.png              | # element screenshot, defined filename            |
        | Screenshot | filename=page.png            |                                   | # page screenshot, defined filename               |
        | Screenshot | filename=${NONE}             |                                   | # page screenshot, NO file will be created        |
        | Screenshot |                              |                                   | # page screenshot, default filename               |
        | Screenshot | locator=//img[@alt="Google"] |                                   | # element screenshot, default filename            |
        | Screenshot | locator=//img[@alt="Google"] | filename=${CURDIR}/subdir/loc.png | # element screenshot, create dirs if not existing |
        """  # noqa: E501
        screenshot_keywords = ScreenshotKeywords(self)
        default_filename_prefix = f"screenshot-{int(time.time())}"

        # pylint: disable=unused-private-member
        def __save_base64_screenshot_to_file(base64_string, fname):
            path = screenshot_keywords._get_screenshot_path(fname)
            screenshot_keywords._create_directory(path)
            with open(fname, "wb") as fh:
                fh.write(base64.b64decode(base64_string))
                self.logger.info("Screenshot saved to file: %s", fname)

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

        ``locator`` element locator

        ``modifier`` press given keys while clicking the element, e.g. CTRL

        ``action_chain`` store action in Selenium ActionChain queue

        Example:

        | Click Element When Visible | q |
        | Click Element When Visible | id:button | CTRL+ALT |
        | Click Element When Visible | action_chain=True |
        """
        self.wait_until_element_is_visible(locator)
        self.click_element(locator, modifier, action_chain)

    @keyword
    def click_button_when_visible(
        self, locator: str, modifier: Optional[str] = None
    ) -> None:
        """Click button identified by ``locator``, once it becomes visible.

        ``locator`` element locator

        ``modifier`` press given keys while clicking the element, e.g. CTRL

        Example:

        | Click Button When Visible  | //button[@class="mybutton"] |
        """
        self.wait_until_element_is_visible(locator)
        self.click_button(locator, modifier)

    # Alias for backwards compatibility
    wait_and_click_button = click_button_when_visible

    @keyword
    def click_element_if_visible(self, locator: str) -> None:
        """Click element if it is visible

        ``locator`` element locator

        Example:

        | Click Element If Visible | //button[@class="mybutton"] |
        """
        visible = self.is_element_visible(locator)
        if visible:
            self.click_element(locator)

    @keyword
    def input_text_when_element_is_visible(self, locator: str, text: str) -> None:
        # pylint: disable=C0301
        """Input text into locator after it has become visible.

        ``locator`` element locator

        ``text`` insert text to locator

        Example:

        | Input Text When Element Is Visible | //input[@id="freetext"]  | my feedback |
        """  # noqa: E501
        self.wait_until_element_is_visible(locator)
        self.input_text(locator, text)

    @keyword
    def is_element_enabled(self, locator: str, missing_ok: bool = True) -> bool:
        """Is element enabled

        ``locator`` element locator
        ``missing_ok`` default True, set to False if keyword should
        Fail if element does not exist

        Example:

        | ${res} | Is Element Enabled | input.field1 |
        """
        return self._run_should_keyword_and_return_status(
            self.element_should_be_enabled,
            locator,
            missing_ok=missing_ok,
        )

    @keyword
    def is_element_visible(self, locator: str, missing_ok: bool = True) -> bool:
        """Is element visible

        ``locator`` element locator
        ``missing_ok`` default True, set to False if keyword should
        Fail if element does not exist

        Example:

        | ${res} | Is Element Visible | id:confirmation |
        """
        return self._run_should_keyword_and_return_status(
            self.element_should_be_visible,
            locator,
            missing_ok=missing_ok,
        )

    @keyword
    def is_element_disabled(self, locator: str, missing_ok: bool = True) -> bool:
        """Is element disabled

        ``locator`` element locator
        ``missing_ok`` default True, set to False if keyword should
        Fail if element does not exist

        Example:

        | ${res} | Is Element Disabled | //input[@type="submit"] |
        """
        return self._run_should_keyword_and_return_status(
            self.element_should_be_disabled,
            locator,
            missing_ok=missing_ok,
        )

    @keyword
    def is_element_focused(self, locator: str, missing_ok: bool = True) -> bool:
        """Is element focused

        ``locator`` element locator
        ``missing_ok`` default True, set to False if keyword should
        Fail if element does not exist

        Example:

        | ${res} | Is Element Focused | //input[@id="freetext"] |
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

        ``locator`` element locator

        ``attribute`` element attribute to check for

        ``expected`` is attribute value equal to this

        Example:

        | ${res} | Is Element Attribute Equal To | h1 | id | main |
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

        ``action`` possible action if alert is present, default ACCEPT

        Example:

        | ${res} | Is Alert Present | alert message |
        """
        return self._run_should_keyword_and_return_status(
            self.alert_should_be_present, text, action
        )

    @keyword
    def does_alert_contain(self, text: str = None, timeout: float = None) -> bool:
        # pylint: disable=W0212
        """Does alert contain text.

        ``text`` check if alert includes text, will raise ValueError is text
        does not exist

        Example:

        | ${res} | Does Alert Contain | alert message |
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

        ``text`` check that alert does not include text, will raise ValueError if text
        does exist

        Example:

        | ${res} | Does Alert Not Contain | unexpected message |
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

        ``locator`` element locator

        Example:

        | ${res} |  Is Checkbox Selected  | id:taxes-paid |
        """
        return self._run_should_keyword_and_return_status(
            self.checkbox_should_be_selected, locator
        )

    @keyword
    def does_frame_contain(self, locator: str, text: str) -> bool:
        """Does frame contain expected text

        ``locator`` locator of the frame to check

        ``text`` does frame contain this text

        Example:

        | ${res} | Does Frame Contain | id:myframe | secret |
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

        ``locator`` element locator

        ``expected`` expected element text

        ``ignore_case`` should check be case insensitive, default `False`

        Example:

        | ${res} | Does Element Contain | id:spec | specification complete | ignore_case=True |
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

        ``locator`` element locator

        ``expected`` expected element text

        ``ignore_case`` should check be case insensitive, default `False`

        Example:

        | ${res} | Is Element Text | id:name | john doe |
        | ${res} | Is Element Text | id:name | john doe | ignore_case=True |
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

        Example:

        | ${res} | Is List Selection | id:cars | Ford |
        """
        return self._run_should_keyword_and_return_status(
            self.list_selection_should_be, locator, *expected
        )

    @keyword
    def is_list_selected(self, locator: str) -> bool:
        """Is any option selected in the

        ``locator`` element locator

        Example:

        | ${res} | Is List Selected | id:cars |
        """
        self.logger.info("Will return if anything is selected on the list")
        return not self._run_should_keyword_and_return_status(
            self.list_should_have_no_selections, locator
        )

    @keyword
    def is_location(self, url: str) -> bool:
        """Is current URL expected url

        ``url`` expected current URL

        Example:

        | Open Available Browser | https://www.robocorp.com |
        | ${res} | Is Location | https://www.robocorp.com |
        """
        return self._run_should_keyword_and_return_status(self.location_should_be, url)

    @keyword
    def does_location_contain(self, expected: str) -> bool:
        """Does current URL contain expected

        ``expected`` URL should contain this

        Example:

        | Open Available Browser | https://robocorp.com |
        | ${res} | Does Location Contain | robocorp |
        """
        return self._run_should_keyword_and_return_status(
            self.location_should_contain, expected
        )

    @keyword
    def does_page_contain(self, text: str) -> bool:
        """Does page contain expected text

        ``text`` page should contain this

        Example:

        | Open Available Browser | https://google.com |
        | ${res} | Does Page Contain | Gmail |
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain, text
        )

    @keyword
    def does_page_contain_button(self, locator: str) -> bool:
        """Does page contain expected button

        ``locator`` element locator

        Example:

        | ${res} | Does Page Contain Button | search-button |
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_button, locator
        )

    @keyword
    def does_page_contain_checkbox(self, locator: str) -> bool:
        """Does page contain expected checkbox

        ``locator`` element locator

        Example:

        | ${res} | Does Page Contain Checkbox | random-selection |
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

        Example:

        | ${res} | Does Page Contain Element | textarea |
        | ${res} | Does Page Contain Element | button | count=4 |
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_element, locator=locator, limit=count
        )

    @keyword
    def does_page_contain_image(self, locator: str) -> bool:
        """Does page contain expected image

        ``locator`` element locator

        Example:

        | Open Available Browser | https://google.com |
        | ${res} | Does Page Contain Image | Google |
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_image, locator
        )

    @keyword
    def does_page_contain_link(self, locator: str) -> bool:
        """Does page contain expected link

        ``locator`` element locator

        Example:

        | ${res} | Does Page Contain Link | id:submit |
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_link, locator
        )

    @keyword
    def does_page_contain_list(self, locator: str) -> bool:
        """Does page contain expected list

        ``locator`` element locator

        Example:

        | ${res} | Does Page Contain List | class:selections |
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_list, locator
        )

    @keyword
    def does_page_contain_radio_button(self, locator: str) -> bool:
        """Does page contain expected radio button

        ``locator`` element locator

        Example:

        | ${res} | Does Page Contain Radio Button | male |
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_radio_button, locator
        )

    @keyword
    def does_page_contain_textfield(self, locator: str) -> bool:
        """Does page contain expected textfield

        ``locator`` element locator

        Example:

        | ${res} | Does Page Contain Textfield | id:address |
        """
        return self._run_should_keyword_and_return_status(
            self.page_should_contain_textfield, locator
        )

    @keyword
    def is_radio_button_set_to(self, group_name: str, value: str) -> bool:
        """Is radio button group set to expected value

        ``group_name`` radio button group name

        ``value`` expected value

        Example:

        | ${res} | Is Radio Button Set To | group_name=gender | value=female |
        """
        return self._run_should_keyword_and_return_status(
            self.radio_button_should_be_set_to, group_name, value
        )

    @keyword
    def is_radio_button_selected(self, group_name: str) -> bool:
        """Is any radio button selected in the button group

        ``group_name`` radio button group name

        Example:

        | ${res} | Is Radio Button Selected | group_name=gender |
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

        Example:

        | ${res} | Does Table Cell Contain | //table | 1 | 1 | Company |
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

        Example:

        | ${res} | Does Table Column Contain | //table | 1 | Nokia |
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

        Example:

        | ${res} | Does Table Row Contain | //table | 1 | Company |
        """
        return self._run_should_keyword_and_return_status(
            self.table_row_should_contain, locator, row, expected
        )

    @keyword
    def does_table_footer_contain(self, locator: str, expected: str) -> bool:
        """Does table footer contain expected text

        ``locator`` element locator for the table

        ``expected`` expected text in table footer

        Example:

        | ${res} | Does Table Footer Contain | //table | Sum |
        """
        return self._run_should_keyword_and_return_status(
            self.table_footer_should_contain, locator, expected
        )

    @keyword
    def does_table_header_contain(self, locator: str, expected: str) -> bool:
        """Does table header contain expected text

        ``locator`` element locator for the table

        ``expected`` expected text in table header

        Example:

        | ${res} | Does Table Header Contain | //table | Month |
        """
        return self._run_should_keyword_and_return_status(
            self.table_header_should_contain, locator, expected
        )

    @keyword
    def does_table_contain(self, locator: str, expected: str) -> bool:
        """Does table contain expected text

        ``locator`` element locator

        ``expected`` expected text in table

        Example:

        | ${res} | Does Table Contain | //table | February |
        """
        return self._run_should_keyword_and_return_status(
            self.table_should_contain, locator, expected
        )

    @keyword
    def is_textarea_value(self, locator: str, expected: str) -> bool:
        """Is textarea matching expected value

        ``locator`` element locator

        ``expected`` expected textarea value

        Example:

        | ${res} | Is Textarea Value | //textarea | Yours sincerely |
        """
        return self._run_should_keyword_and_return_status(
            self.textarea_value_should_be, locator, expected
        )

    @keyword
    def does_textarea_contain(self, locator: str, expected: str) -> bool:
        """Does textarea contain expected text

        ``locator`` element locator

        ``expected`` expected text in textarea

        Example:

        | ${res} | Does Textarea Contain | //textarea | sincerely |
        """
        return self._run_should_keyword_and_return_status(
            self.textarea_should_contain, locator, expected
        )

    @keyword
    def does_textfield_contain(self, locator: str, expected: str) -> bool:
        """Does textfield contain expected text

        ``locator`` element locator

        ``expected`` expected text in textfield

        Example:

        | ${res} | Does Textfield Contain | id:lname | Last |
        """
        return self._run_should_keyword_and_return_status(
            self.textfield_should_contain, locator, expected
        )

    @keyword
    def is_textfield_value(self, locator: str, expected: str) -> bool:
        """Is textfield value expected

        ``locator`` element locator

        ``expected`` expected textfield value

        Example:

        | ${res} | Is Textfield Value | id:lname | Lastname |
        """
        return self._run_should_keyword_and_return_status(
            self.textfield_value_should_be, locator, expected
        )

    @keyword
    def is_title(self, title: str) -> bool:
        """Is page title expected

        ``title`` expected title value

        Example:

        | ${res} | Is Title | Webpage title text |
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

        ``locator`` element locator

        Example:

        | &{res}  | Get Element Status | class:special |
        | Log     | ${res.visible} |
        | Log     | ${res.enabled} |
        | Log     | ${res.disabled} |
        | Log     | ${res.focused} |
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

        ``url`` URL to open
        ``tab`` defines is url is opened in a tab (default `True`) or
                in new window (`False`)

        Example:

        | Open User Browser  | https://www.google.com?q=rpa |
        | Open User Browser  | https://www.google.com?q=rpa | tab=False |
        """  # noqa: E501
        browser_method = webbrowser.open_new_tab if tab else webbrowser.open_new
        browser_method(url)

    @keyword
    def get_browser_capabilities(self) -> dict:
        """Get dictionary of browser properties

        Example:

        | ${caps}= | Get Browser Capabilities |
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

        ``directory``    target directory for downloads, defaults to None which means
                         that setting is removed
        ``download_pdf`` if `True` then PDF is downloaded instead of shown with
                         browser's internal viewer
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

        Example:

        | Highlight Elements | xpath://h2 |
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
        """Remove all highlighting made by ``Highlight Elements``."""
        attribute_name = "rpaframework-highlight"

        elements = self.driver.find_elements(By.CSS_SELECTOR, f"[{attribute_name}]")
        script = "".join(
            f'arguments[{idx}].removeAttribute("{attribute_name}");'
            for idx in range(len(elements))
        )
        self.driver.execute_script(script, *elements)

    @keyword
    def print_to_pdf(
        self, output_path: Optional[str] = None, params: Optional[dict] = None
    ) -> str:
        """Print the current page to a PDF document using Chrome/Chromium DevTools.

        Attention: This works in ``headless`` mode only!
        For supported parameters see:
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-printToPDF
        Returns the output PDF file path.

        :param output_path: File path for the generated PDF document. By default, it is
            saved to the output folder with the name `out.pdf`.
        :param params: Parameters for the browser printing method. By default, it uses
            the following values:
            ``{
                "landscape": False,
                "displayHeaderFooter": False,
                "printBackground": True,
                "preferCSSPageSize": True,
            }``
        """
        if not self.driver.name.lower().startswith("chrom"):
            raise NotImplementedError("PDF printing works only with Chrome/Chromium")

        default_params = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
        }
        params = params or default_params
        result = self._send_command_and_get_result("Page.printToPDF", params)
        if isinstance(result, str) and "Printing is not available" in result:
            raise TypeError("PDF printing works in headless mode only")

        output_path = output_path or str(get_output_dir() / "out.pdf")
        pdf_data = base64.b64decode(result["data"])
        with open(output_path, "wb") as stream:
            stream.write(pdf_data)

        return output_path

    @keyword
    def execute_cdp(self, command, parameters):
        """
        Executes Chrome DevTools Protocol commands

        Works only with Chrome/Chromium

        For more information, available commands and parameters, see:
        https://chromedevtools.github.io/devtools-protocol/

        ``command`` command to execute as string

        ``parameters`` parameters for command as a dictionary

        Example:

        | Open Chrome Browser | about:blank | headless=True |
        | &{params} | Create Dictionary | useragent=Chrome/83.0.4103.53 |
        | Execute CDP | Network.setUserAgentOverride | ${params} |
        | Go To | https://robocorp.com |
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
