import logging
from typing import Optional

# pylint: disable=wrong-import-position
from robotlibcore import DynamicCore

from . import utils
from .keywords import (
    ActionKeywords,
    ElementKeywords,
    Locator,
    LocatorKeywords,
    WindowKeywords,
)

if utils.IS_WINDOWS:
    # Configure comtypes to not generate DLL bindings into
    # current environment, instead keeping them in memory.
    # Slower, but prevents dirtying environments.
    import comtypes.client

    comtypes.client.gen_dir = None

    import uiautomation as auto
    from uiautomation.uiautomation import Logger


class Windows(DynamicCore):
    # pylint: disable=anomalous-backslash-in-string
    """The `Windows` is a library that can be used for Windows desktop automation.

    This library is at this moment in "BETA" stage as an alternative
    library for `RPA.Desktop.Windows`. Main difference being that this
    library is using `uiautomation`_ dependency instead of `pywinauto`.

    .. _uiautomation: https://github.com/yinkaisheng/Python-UIAutomation-for-Windows


    **Installation**

    This library, ``RPA.Windows`` is available via **rpaframework-windows** package. This
    package is first available as a separate package installation from **rpaframework** package.
    In the next stage this is integrated into **rpaframework** package. Ultimately this library
    will replace current library ``RPA.Desktop.Windows`` if seen as approriate.

    .. code-block:: yaml

        channels:
          - conda-forge
        dependencies:
          - python=3.7.5
          - pip=20.1
          - pip:
            - rpaframework-windows==2.0.0


    **About terminology**

    **ControlType** is a value referred to by locator keys `type:` or `control`. Represents type of application
    object, which can be e.g. `Window`, `Button` or `ListItem`.

    **Element** is an entity of an application structure (e.g. certain button in a window), which can be
    identified by a locator.

    **WindowsElement** is an library container object for the ``Element``. All keywords returning element, return
    element as ``WindowsElement`` and all keywords taking in ``locator`` or ``root_element`` arguments accept
    ``WindowsElement`` as an argument value.

    Structure of the ``WindowsElement``

    .. code-block:: python

        class WindowsElement:
            item: Control        # ``item`` contains object instance of the element
            locator: str         # ``locator`` that found this element
            name: str            # ``Name`` attribute of the element
            automation_id: str   # ``AutomationId`` attribute of the element
            control_type: str    # ``ControlTypeName`` attribute of the element
            class_name: str      # ``ClassName`` attribute of the element
            left: int            # element's rectangle left coordinate
            right: int           # element's rectangle right coordinate
            top: int             # element's rectangle top coordinate
            bottom: int          # element's rectangle bottom coordinate
            width: int           # element's rectangle horizontal width
            height: int          # element's rectangle vertical height
            xcenter: int         # element's rectangle center point x coordinate
            ycenter: int         # element's rectangle center point y coordinate

    Example of the ``WindowsElement`` usage

    .. code-block:: robotframework

        ${rows}=    Get Elements    class:DataGridRow
        # ${rows} is a list of ``WindowsElement``s
        FOR    ${row}    IN    @{rows}
            Log To Console   ${row.name}                # access ``WindowsElement``
            Log To Console   ${row.item.AutomationId}   # access ``WindowsElement.item`` directly
            Log To Console   ${row.item.Name}           # same as ``${row.name}``
        END


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
    desktop         *SPECIAL* target desktop, no value for the key e.g. `desktop:desktop and name:Calculator`
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

    Keys for the keyboard actions are given using ``uiautomation`` specification.

    Special keys which are given within `{}` syntax.

    =================== =======================
    Key                 Maps to action
    =================== =======================
    LBUTTON             Left mouse button
    RBUTTON             Right mouse button
    CANCEL              Control-break processing
    MBUTTON             Middle mouse button (three-button mouse)
    XBUTTON1            X1 mouse button
    XBUTTON2            X2 mouse button
    BACK                BACKSPACE key
    TAB                 TAB key
    CLEAR               CLEAR key
    RETURN              ENTER key
    ENTER               ENTER key
    SHIFT               SHIFT key
    CTRL                CTRL key
    CONTROL             CTRL key
    ALT                 ALT key
    PAUSE               PAUSE key
    CAPITAL             CAPS LOCK key
    KANA                IME Kana mode
    HANGUEL             IME Hanguel mode (maintained for compatibility; use VK_HANGUL)
    HANGUL              IME Hangul mode
    JUNJA               IME Junja mode
    FINAL               IME final mode
    HANJA               IME Hanja mode
    KANJI               IME Kanji mode
    ESC                 ESC key
    ESCAPE              ESC key
    CONVERT             IME convert
    NONCONVERT          IME nonconvert
    ACCEPT              IME accept
    MODECHANGE          IME mode change request
    SPACE               SPACEBAR
    PRIOR               PAGE UP key
    PAGEUP              PAGE UP key
    NEXT                PAGE DOWN key
    PAGEDOWN            PAGE DOWN key
    END                 END key
    HOME                HOME key
    LEFT                LEFT ARROW key
    UP                  UP ARROW key
    RIGHT               RIGHT ARROW key
    DOWN                DOWN ARROW key
    SELECT              SELECT key
    PRINT               PRINT key
    EXECUTE             EXECUTE key
    SNAPSHOT            PRINT SCREEN key
    PRINTSCREEN         PRINT SCREEN key
    INSERT              INS key
    INS                 INS key
    DELETE              DEL key
    DEL                 DEL key
    HELP                HELP key
    WIN                 Left Windows key (Natural keyboard)
    LWIN                Left Windows key (Natural keyboard)
    RWIN                Right Windows key (Natural keyboard)
    APPS                Applications key (Natural keyboard)
    SLEEP               Computer Sleep key
    NUMPAD0             Numeric keypad 0 key
    NUMPAD1             Numeric keypad 1 key
    NUMPAD2             Numeric keypad 2 key
    NUMPAD3             Numeric keypad 3 key
    NUMPAD4             Numeric keypad 4 key
    NUMPAD5             Numeric keypad 5 key
    NUMPAD6             Numeric keypad 6 key
    NUMPAD7             Numeric keypad 7 key
    NUMPAD8             Numeric keypad 8 key
    NUMPAD9             Numeric keypad 9 key
    MULTIPLY            Multiply key
    ADD                 Add key
    SEPARATOR           Separator key
    SUBTRACT            Subtract key
    DECIMAL             Decimal key
    DIVIDE              Divide key
    F1                  F1 key
    F2                  F2 key
    F3                  F3 key
    F4                  F4 key
    F5                  F5 key
    F6                  F6 key
    F7                  F7 key
    F8                  F8 key
    F9                  F9 key
    F10                 F10 key
    F11                 F11 key
    F12                 F12 key
    F13                 F13 key
    F14                 F14 key
    F15                 F15 key
    F16                 F16 key
    F17                 F17 key
    F18                 F18 key
    F19                 F19 key
    F20                 F20 key
    F21                 F21 key
    F22                 F22 key
    F23                 F23 key
    F24                 F24 key
    NUMLOCK             NUM LOCK key
    SCROLL              SCROLL LOCK key
    LSHIFT              Left SHIFT key
    RSHIFT              Right SHIFT key
    LCONTROL            Left CONTROL key
    LCTRL               Left CONTROL key
    RCONTROL            Right CONTROL key
    RCTRL               Right CONTROL key
    LALT                Left MENU key
    RALT                Right MENU key
    BROWSER_BACK        Browser Back key
    BROWSER_FORWARD     Browser Forward key
    BROWSER_REFRESH     Browser Refresh key
    BROWSER_STOP        Browser Stop key
    BROWSER_SEARCH      Browser Search key
    BROWSER_FAVORITES   Browser Favorites key
    BROWSER_HOME        Browser Start and Home key
    VOLUME_MUTE         Volume Mute key
    VOLUME_DOWN         Volume Down key
    VOLUME_UP           Volume Up key
    MEDIA_NEXT_TRACK    Next Track key
    MEDIA_PREV_TRACK    Previous Track key
    MEDIA_STOP          Stop Media key
    MEDIA_PLAY_PAUSE    Play/Pause Media key
    LAUNCH_MAIL         Start Mail key
    LAUNCH_MEDIA_SELECT Select Media key
    LAUNCH_APP1         Start Application 1 key
    LAUNCH_APP2         Start Application 2 key
    OEM_1               Used for miscellaneous characters; it can vary by keyboard.For the US standard keyboard, the ';:' key
    OEM_PLUS            For any country/region, the '+' key
    OEM_COMMA           For any country/region, the ',' key
    OEM_MINUS           For any country/region, the '-' key
    OEM_PERIOD          For any country/region, the '.' key
    OEM_2               Used for miscellaneous characters; it can vary by keyboard.
    OEM_3               Used for miscellaneous characters; it can vary by keyboard.
    OEM_4               Used for miscellaneous characters; it can vary by keyboard.
    OEM_5               Used for miscellaneous characters; it can vary by keyboard.
    OEM_6               Used for miscellaneous characters; it can vary by keyboard.
    OEM_7               Used for miscellaneous characters; it can vary by keyboard.
    OEM_8               Used for miscellaneous characters; it can vary by keyboard.
    OEM_102             Either the angle bracket key or the backslash key on the RT 102-key keyboard
    PROCESSKEY          IME PROCESS key
    PACKET              Used to pass Unicode characters as if they were keystrokes. The VK_PACKET key is the low word of a 32-bit Virtual Key value used for non-keyboard input methods. For more information, see Remark in KEYBDINPUT, SendInput, WM_KEYDOWN, and WM_KeyUp
    ATTN                Attn key
    CRSEL               CrSel key
    EXSEL               ExSel key
    EREOF               Erase EOF key
    PLAY                Play key
    ZOOM                Zoom key
    NONAME              Reserved
    PA1                 PA1 key
    OEM_CLEAR           Clear key
    =================== =======================

    Examples.

    .. code-block:: python

        lib = Windows()
        # {Ctrl}, {Delete} ... are special keys' name in SpecialKeyNames.
        lib.send_keys('{Ctrl}a{Delete}{Ctrl}v{Ctrl}s{Ctrl}{Shift}s{Win}e{PageDown}') #press Ctrl+a, Delete, Ctrl+v, Ctrl+s, Ctrl+Shift+s, Win+e, PageDown
        lib.send_keys('{Ctrl}(AB)({Shift}(123))') #press Ctrl+A+B, type '(', press Shift+1+2+3, type ')', if '()' follows a hold key, hold key won't release util ')'
        lib.send_keys('{Ctrl}{a 3}') #press Ctrl+a at the same time, release Ctrl+a, then type 'a' 2 times
        lib.send_keys('{a 3}{B 5}') #type 'a' 3 times, type 'B' 5 times
        lib.send_keys('{{}Hello{}}abc {a}{b}{c} test{} 3}{!}{a} (){(}{)}') #type: '{Hello}abc abc test}}}!a ()()'
        lib.send_keys('0123456789{Enter}')
        lib.send_keys('ABCDEFGHIJKLMNOPQRSTUVWXYZ{Enter}')
        lib.send_keys('abcdefghijklmnopqrstuvwxyz{Enter}')
        lib.send_keys('`~!@#$%^&*()-_=+{Enter}')
        lib.send_keys('[]{{}{}}\\|;:\'\",<.>/?{Enter}')

    Using access key of the element (element property -> AccessKey 'alt+s').
    The `(+s)` means that previous special key is kept down until closing parenthesis is reached.

    On the below example this means that 'ALT' key is pressed down, then '+' and 's' keys are pressed
    down before they are all released up.

    .. code-block:: robotframework

        Send Keys   keys={Alt}(+s)

    Mouse clicks can be executed with keywords specific for a type of a click, e.g. ``Click`` (normal click),
    ``Double Click`` and ``Right Click``.

    **How to inspect**

    Most common, and recommended by Microsoft, inspector tool for Windows is `Accessibility Insights`_ that
    can be installed separately. Other options are tools `Inspect Object`_  and `UI Automation Verify`_, which
    can be accessed by installing Windows SDK.

    A more programmatic approach is to run `Print Tree    log_as_warnings=${True}`
    keyword and then observe in the logs the found elements structure starting from
    Desktop as root. (refer to keyword's documentation for more details)

    .. _Accessibility Insights: https://accessibilityinsights.io/
    .. _Inspect Object: https://docs.microsoft.com/en-us/windows/win32/winauto/inspect-objects
    .. _UI Automation Verify: https://docs.microsoft.com/en-us/windows/win32/winauto/ui-automation-verify

    **Recording**

    The package provides some rudimentary inspecting and recording via script ``windows-record``, which can
    be started in the command line (in a environment containing ``rpaframework-windows`` installation).

    Recording inspects elements on **mouse click** and can be stopped with keyboard **ESC**.
    Expected console output.

    .. code-block:: bash

        C:\\Users\\User\\robots\\>windows-record  # or >python -m RPA.Windows
        keyboard and mouse listeners started

        --------------------------------------------------------------------------------
        COPY & PASTE BELOW CODE INTO *** Tasks *** or *** Keywords ***
        --------------------------------------------------------------------------------

        Control Window    Taskbar  # Handle: 131380
        Click   name:'Type here to search'
        Control Window    Calculator  # Handle: 3411840
        Click   name:'Five'
        Click   name:'Eight'
        Click   name:'Five'

        --------------------------------------------------------------------------------


    **Examples**

    Both Robot Framework and Python examples follow.

    The library must be imported first.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Windows


    Windows Calculator task

    .. code-block:: robotframework

        *** Tasks ***
        Do some calculations
            [Setup]  Windows Run   calc.exe
            Control Window    name:Calculator
            Click    id:clearButton
            Send Keys   keys=96+4=
            ${result}=    Get Attribute    id:CalculatorResults    Name
            Log To Console    ${result}
            ${buttons}=  Get Elements  type:Group and name:'Number pad' > type:Button
            FOR  ${button}  IN  @{buttons}
                Log To Console   ${button}
            END
            [Teardown]   Close Current Window

    Python example

    .. code-block:: robotframework

        from RPA.Windows import Windows

        library = Windows()

        def test_do_some_calculations():
            try:
                library.windows_run("calc.exe")
                library.control_window("name:Calculator")
                library.click("id:clearButton")
                library.send_keys(keys="96+4=")
                result = library.get_attribute("id:CalculatorResults", "Name")
                print(result)
                buttons = library.get_elements("type:Group and name:'Number pad' > type:Button")
                for button in buttons:
                    print(button)
            finally:
                library.close_current_window()

    """  # noqa: E501,W605

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self, locators_path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.wait_time: float = 0.5
        self.global_timeout: float = float(auto.uiautomation.TIME_OUT_SECOND)
        self.simulate_move = False  # this is currently used, but not set anywhere else
        self.window_element: Optional[Locator] = None
        self.anchor_element: Optional[Locator] = None

        # prevent comtypes writing lot of log messages
        comtypelogger = logging.getLogger("comtypes")
        comtypelogger.propagate = False

        # disable uiautomation writing a log file
        Logger.SetLogFile("")

        # register keyword libraries to LibCore
        libraries = [
            ActionKeywords(self),
            ElementKeywords(self),
            LocatorKeywords(self, locators_path=locators_path),
            WindowKeywords(self),
        ]
        super().__init__(libraries)
