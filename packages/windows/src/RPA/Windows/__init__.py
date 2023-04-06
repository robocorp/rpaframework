import logging
from typing import Optional

from robotlibcore import DynamicCore

# pylint: disable=wrong-import-order
from RPA.core.windows import WindowsElementsMixin

from . import utils
from .keywords import ActionKeywords, ElementKeywords, LocatorKeywords, WindowKeywords

if utils.IS_WINDOWS:
    # Configure comtypes to not generate DLL bindings into
    # current environment, instead keeping them in memory.
    # Slower, but prevents dirtying environments.
    import comtypes.client
    from uiautomation.uiautomation import Logger

    comtypes.client.gen_dir = None


# NOTE(cmiN): We use as base the robotframework `DynamicCore` this time instead of the
#  vendorized one, like found in `RPA.core.windows.WindowsElements`.
class Windows(WindowsElementsMixin, DynamicCore):
    # pylint: disable=anomalous-backslash-in-string
    """The `Windows` is a library that can be used for Windows desktop automation.

    Library is included in the **rpaframework** package by default, but as shown in the
    below example library can be also installed separately without **rpaframework**.

    .. code-block:: yaml

        channels:
          - conda-forge
        dependencies:
          - python=3.9.13
          - pip=22.1.2
          - pip:
            - rpaframework-windows==7.0.2 # standalone Windows library (`rpaframework` includes this library)


    **About terminology**

    **ControlType** is a value referred to by locator keys `type:` or `control`. Represents type of application
    object, which can be e.g. `Window`, `Button` or `ListItem`.

    **Element** is an entity of an application structure (e.g. certain button in a window), which can be
    identified by a locator. (also referred as **Control**)

    **WindowsElement** is an library container object for the ``Element``. All the keywords returning elements, will in
    fact return ``WindowsElement``s. The ones accepting ``locator`` or ``root_element`` as arguments, will accept
    ``WindowsElement`` as an argument value. (``locator`` accepts strings as well)

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
    path            target element by its index-based path traversal (e.g. `path:2|3|8|2`)
    =============== =======================

    **About root element on locators**

    Locators work on currently active `root element`. At the start `root element` is the whole
    desktop. There are different ways on changing this root element.

    Keyword ``Control Window`` is the most common method of setting certain system window
    as a root element for further actions using locators. In the absence of a provided
    `root_element` parameter, here's how you can control the default root element
    resolving:

      - ``Set Anchor``: Sets the active anchor window from which the search begins.
      - ``Control Window``: Controls and focuses on a window and marks it as the current
        active window, from which all the subsequent searches will start from in the
        absence of a set anchor.
      - If there's no set anchor nor active window, then the last resort will be the
        "Desktop" element itself.

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
        type:Group and name:"Number pad" > type:Button and index:4
        type:Group and name:"Number pad" > control:Button index:5
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

    **About the path strategy**

    When automation IDs and names aren't enough (or not reliable), then you can fallback
    to the positions of elements in a tree. This can be achieved using the `path:`
    strategy to specify a list of element positions which indicates how to traverse the
    tree from parent to child beginning with the resolved root.

    Example: `Calculator > path:2|3|2|8|2` - this locator looks for the "Calculator"
    window, then it looks for the 2nd direct child and then it looks for the 3rd one of
    the previous child and so on until it consumes the path completely. (indexes start
    with `1`)

    An alternative way to get the whole tree to explore it yourself would be to use the
    ``Print Tree`` keyword.

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

    A more programmatic approach is to run ``Print Tree    log_as_warnings=${True}``
    keyword and then observe in the logs the found elements structure starting from
    Desktop (or the currently set anchor / active window) as root. (refer to keyword's
    `documentation <https://robocorp.com/docs/libraries/rpa-framework/rpa-windows/keywords#print-tree>`_
    for more details)

    .. _Accessibility Insights: https://accessibilityinsights.io/
    .. _Inspect Object: https://docs.microsoft.com/en-us/windows/win32/winauto/inspect-objects
    .. _UI Automation Verify: https://docs.microsoft.com/en-us/windows/win32/winauto/ui-automation-verify

    **Recording**

    The package provides some rudimentary inspecting and recording via the
    ``windows-record`` script, which can be started through the command line (in an
    environment containing the ``rpaframework-windows`` installation).

    Recording inspects elements on **mouse click** and can be stopped by pressing the
    **ESC** key. Expected console output:

    .. code-block:: winbatch

        C:\\Users\\User\\robots\\> windows-record -v  # or > python -m RPA.Windows -v
        Mouse recording started. Use ESC to stop recording.

        --------------------------------------------------------------------------------
        Copy-paste the code below into your `*** Tasks ***` or `*** Keywords ***`
        --------------------------------------------------------------------------------

        Control Window    name:Calculator and type:WindowControl and class:ApplicationFrameWindow  # handle:9569486
        Click    name:Calculator and id:TitleBar and type:WindowControl and class:ApplicationFrameTitleBarWindow and path:1
        Click    name:"Display is 0" and id:CalculatorResults and type:TextControl and path:2|3|2|2
        Click    name:Eight and id:num8Button and type:ButtonControl and class:Button and path:2|3|2|8|9
        Click    name:Nine and id:num9Button and type:ButtonControl and class:Button and path:2|3|2|8|10
        Click    name:Clear and id:clearButton and type:ButtonControl and class:Button and path:2|3|2|5|3

        --------------------------------------------------------------------------------

    Check our Portal example in order to learn more abot the `path:` strategy in
    locators and how to record elements displaying their paths:
    https://robocorp.com/portal/robot/robocorp/example-windows-element-path
    
    Video recorded demo on how to run the recorder script from VSCode:
    https://www.loom.com/share/2807372359f34b9cbe1bc2df9194ec68

    **Caveats**

    - Make sure your *display scaling* is set to *100%*, otherwise you might encounter
      issues when clicking or interacting with elements. (since offsets and coordinates
      get distorted)
    - Disturbing the automation (like interacting with your mouse/keyboard) or having
      other apps obstructing the process interacting with your app of interest will
      most probably affect the expected behaviour. In order to avoid this, try
      controlling the app's main window right before sending clicks or keys. And keep
      targeting elements through **string locators**, as interacting with Windows
      element objects previously retrieved will not work as expected in a future
      altered state of the app (changes under the element structure).

    **Example: Robot Framework**

    The library must be imported first.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Windows

    Windows Calculator automation task

    .. code-block:: robotframework

        *** Tasks ***
        Do some calculations
            [Setup]  Windows Run   calc.exe
            
            Control Window    name:Calculator
            Click    id:clearButton
            Send Keys   keys=96+4=
            ${result} =    Get Attribute    id:CalculatorResults    Name
            Log To Console    ${result}
            
            @{buttons} =  Get Elements  type:Group and name:"Number pad" > type:Button
            FOR  ${button}  IN  @{buttons}
                Log To Console   ${button}
            END
            
            [Teardown]   Close Current Window

    **Example: Python**

    .. code-block:: python

        from RPA.Windows import Windows

        library = Windows()

        def test_do_some_calculations():
            library.windows_run("calc.exe")
            try:
                library.control_window("name:Calculator")
                library.click("id:clearButton")
                library.send_keys(keys="96+4=")
                result = library.get_attribute("id:CalculatorResults", "Name")
                print(result)
                buttons = library.get_elements(
                    'type:Group and name:"Number pad" > type:Button'
                )
                for button in buttons:
                    print(button)
            finally:
                library.close_current_window()

    """  # noqa: E501,W605

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"
    SIMULATE_MOVE = False

    def __init__(self, locators_path: Optional[str] = None):
        self.wait_time: float = 0.5
        self.simulate_move: bool = self.SIMULATE_MOVE

        # Prevent comtypes writing a lot of log messages.
        comtypes_logger = logging.getLogger("comtypes")
        comtypes_logger.propagate = False
        if utils.IS_WINDOWS:
            # Disable uiautomation writing into a log file.
            Logger.SetLogFile("")

        super().__init__(locators_path=locators_path)

    def _get_libraries(self, locators_path: Optional[str]):
        return [
            ActionKeywords(self),
            ElementKeywords(self),
            LocatorKeywords(self, locators_path=locators_path),
            WindowKeywords(self),
        ]
