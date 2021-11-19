import logging

# pylint: disable=wrong-import-position
from robotlibcore import DynamicCore


from RPA.Windows.keywords import (
    ActionKeywords,
    ElementKeywords,
    LocatorKeywords,
    WindowKeywords,
)

from RPA.Windows import utils

if utils.is_windows():
    import uiautomation as auto
    from uiautomation.uiautomation import Logger


class Windows(DynamicCore):
    """The `Windows` is a library that can be used for Windows desktop automation.

    This library is at this moment in "BETA" stage as an alternative
    library for `RPA.Desktop.Windows`. Main difference being that this
    library is using `uiautomation`_ dependency instead of `pywinauto`.

    .. _uiautomation: https://github.com/yinkaisheng/Python-UIAutomation-for-Windows

    **About terminology**

    **ControlType** is a value referred to by locator keys `type:` or `control`. Represents type of application
    object, which can be e.g. `Window`, `Button` or `ListItem`.

    **Element** is an entity of an application structure (e.g. certain button in a window), which can be
    identified by a locator.


    **Locators**

    Locators are based on different strategies that can used identify Control object.

    Available strategies that can be used for the locators:

    =============== =======================
    Key             Maps to search property
    =============== =======================
    name            Name
    class           ClassName
    type            ControlType
    control         ControlType
    id              AutomationId
    automationid    AutomationId
    regex           RegexName
    subname         SubName
    index           foundIndex (int)
    offset          offset coordinates (x (int), y (int)) from control center
    executable      target window by its executable name
    handle          target window handle (int)
    desktop         *SPECIAL* target desktop, no value for the key e.g. `desktop and name:Calculator`
    process         *NOT YET SUPPORTED* target window by its executable's process id
    depth           searchDepth (int) for finding Control (default 8)
    =============== =======================

    **About root element on locators**

    Locators work on currently active `root element`. At the start `root element` is the whole
    desktop. There are different ways on changing this root element.

    Keyword ``Control Window`` is the most common method of setting certain system window
    as a root element for further actions using locators.

    Locators themselves support cascading syntax (denoted by character `>` in the locator string),
    which can denote root element in "parent (root) & child" terms.

    For example.

    .. code-block:: robotframework

        Click  id:controls > id:activate

    On the above example the left side of the `>` character, `id:controls`, represents the root element
    (can be called as "parent element" in this case). Right side of the locator string, `id:activate`,
    represents "child" element and it will be searched under the "parent element".

    This way element search is more efficient, because search are restricted to certain section of element
    tree which can be quite huge especially on the desktop level and in certain applications.

    Keyword examples:

    .. code-block:: robotframework

        Control Window    name:Calculator
        Control Window    Calculator  # will execute search by 'name:Calculator'
        Control Window    executable:Spotify.exe

    some example locators, `and` can be omitted ie. space ` ` between locator keys means the same thing as `and`:

    .. code-block:: bash

        id:clearButton
        type:Group and name:'Number pad' > type:Button and index:4
        type:Group and name:'Number pad' > control:Button index:5
        id:Units1 > name:${unit}
        class:Button offset:370,0

    **About locator restrictions**

    Visual locators are not supported in this library and they can't be used in the same chain with these
    Windows locators. Visual locators are supported by the `RPA.Desktop` library. Locator chaining (image and
    Windows locators) support will be added in the future.

    Locator syntax does not yet support OR operation (only AND operations).

    **About search depth**

    The library does element search depth by default to the level of 8. This means that locator will look into
    8 levels of elements under element tree of the root element. This can lead into situation where element
    can't be found. To fix this it is recommended to set root element which can be found within 8 levels OR
    defining `depth` in the locator string to a bigger value, e.g. `id:deeplyNestedButton depth:16`. Useful
    keywords for setting root element are ``Control Window``, ``Set Anchor`` and ``Get Element``.


    **Keyboard and mouse**

    TBD

    **How to inspect**

    Most common and recommended by Microsoft, inspector tool for Windows, is `Accessibility Insights`_ that
    can be installed separately. Other options are tools `Inspect Object`_  and `UI Automation Verify`_, which
    can be accessed by installing Windows SDK.

    .. _Accessibility Insights: https://github.com/yinkaisheng/Python-UIAutomation-for-Windows
    .. _Inspect Object: https://docs.microsoft.com/en-us/windows/win32/winauto/inspect-objects
    .. _UI Automation Verify: https://docs.microsoft.com/en-us/windows/win32/winauto/ui-automation-verify

    **Recording**

    The package provides some rudimentary inspecting and recording via script SCRIPT_NAME

    ADD GUIDE HERE

    **Examples**

    Both Robot Framework and Python examples follow.

    The library must be imported first.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Windows


    Windows Calculator steps

    .. code-block:: robotframework

        *** Keywords ***
        Do some calculations
            Control Window    name:Calculator
            Click    id:clearButton
            Send Keys   96+4=
            ${result}=    Access Attribute or Method    id:CalculatorResults    Name
            Log To Console    ${result}


    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        # , timeout: float = None, simulate_move: bool = False
        self.logger = logging.getLogger(__name__)
        self.timeout = 0.5
        self.simulate_move = False
        self.window = None
        self.anchor_element = None
        # prevent comtypes writing lot of log messages
        comtypelogger = logging.getLogger("comtypes")
        comtypelogger.propagate = False

        Logger.SetLogFile("")
        # Register keyword libraries to LibCore
        libraries = [
            ActionKeywords(self),
            ElementKeywords(self),
            LocatorKeywords(self),
            WindowKeywords(self),
        ]
        super().__init__(libraries)
