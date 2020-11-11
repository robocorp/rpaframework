import logging
from robotlibcore import DynamicCore

from RPA.Desktop.keywords import (
    ApplicationKeywords,
    ClipboardKeywords,
    FinderKeywords,
    KeyboardKeywords,
    MouseKeywords,
    ScreenKeywords,
)


class Desktop(DynamicCore):
    """`Desktop` is a cross-platform library for navigating and interacting with
    desktop environments. It can be used to automate applications through
    the same interfaces that are available to human users.

    The library includes the following features:

    - Mouse and keyboard input emulation
    - Starting and stopping applications
    - Finding elements through image template matching
    - Taking screenshots
    - Clipboard management

    **Note:** Windows element selectors are not currently supported,
        and require the use of ``RPA.Desktop.Windows``

    **Locating elements**

    To automate actions on the desktop, a robot needs to interact with various
    graphical elements such as buttons or input fields. The positions of these
    elements can be found using a feature called `locators`.

    A locator describes the properties or features of an element. This information
    can be later used to locate similar elements even when window positions or
    states change.

    The currently supported locator types are:

    =========== =================== ===========
    Name        Arguments           Description
    =========== =================== ===========
    alias       name (str)          A named locator, the default.
    image       path (str)          Image of an element that is matched to current screen content
    coordinates x (int), y (int)    Pixel coordinates as absolute position
    offset      x (int), y (int)    Pixel coordinates relative to current mouse position
    =========== =================== ===========

    A locator is defined by its type and arguments, divided by a colon.
    Some example usages are shown below. Note that the prefix for alias can
    be omitted as its the default type.

    .. code-block:: robotframework

        Click    alias:SpareBin.Login
        Click    SpareBin.Login

        Move mouse    image:%{ROBOT_ROOT}/logo.png
        Move mouse    offset:200,0
        Click

    **Named locators**

    The library supports storing locators in a database, which contains
    all of the required fields and various bits of metadata. This enables
    having one source of truth, which can be updated if a website's or applications's
    UI changes. Robot Framework scripts can then only contain a reference
    to a stored locator by name.

    The main way to create named locators is with `Robocorp Lab`_.

    .. _Robocorp Lab: https://robocorp.com/docs/product-manuals/robocorp-lab/robocorp-lab-overview

    **Keyboard and mouse**

    Keyboard keywords can emulate typing text, but also pressing various function keys.
    The name of a key is case-insensitive and spaces will be converted to underscores,
    i.e. the key ``Page Down`` and ``page_down`` are equivalent.

    The following function keys are supported:

    =============== ===========
    Key             Description
    =============== ===========
    shift           A generic Shift key. This is a modifier.
    shift_l         The left Shift key. This is a modifier.
    shift_r         The right Shift key. This is a modifier.
    ctrl            A generic Ctrl key. This is a modifier.
    ctrl_l          he left Ctrl key. This is a modifier.
    ctrl_r          The right Ctrl key. This is a modifier.
    alt             A generic Alt key. This is a modifier.
    alt_l           The left Alt key. This is a modifier.
    alt_r           The right Alt key. This is a modifier.
    alt_gr          The AltGr key. This is a modifier.
    cmd             A generic command button (Windows / Command / Super key). This may be a modifier.
    cmd_l           The left command button (Windows / Command / Super key). This may be a modifier.
    cmd_r           The right command button (Windows / Command / Super key). This may be a modifier.
    up              An up arrow key.
    down            A down arrow key.
    left            A left arrow key.
    right           A right arrow key.
    enter           The Enter or Return key.
    space           The Space key.
    tab             The Tab key.
    backspace       The Backspace key.
    delete          The Delete key.
    esc             The Esc key.
    home            The Home key.
    end             The End key.
    page_down       The Page Down key.
    page_up         The Page Up key.
    caps_lock       The Caps Lock key.
    f1 to f20       The function keys.
    insert          The Insert key. This may be undefined for some platforms.
    menu            The Menu key. This may be undefined for some platforms.
    num_lock        The Num Lock key. This may be undefined for some platforms.
    pause           The Pause / Break key. This may be undefined for some platforms.
    print_screen    The Print Screen key. This may be undefined for some platforms.
    scroll_lock     The Scroll Lock key. This may be undefined for some platforms.
    =============== ===========

    When controlling the mouse, there are different types of actions that can be
    done. Same formatting rules as function keys apply. They are as follows:

    ============ ===========
    Action       Description
    ============ ===========
    click        Click with left mouse button
    left_click   Click with left mouse button
    double_click Double click with left mouse button
    triple_click Triple click with left mouse button
    right_click  Click with right mouse button
    ============ ===========

    The supported mouse button types are ``left``, ``right``, and ``middle``.

    **Examples***

    The library can open applications and interact with them through
    keyboard and mouse events.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Desktop

        *** Keywords ***
        Write entry in accounting
            [Arguments]    ${entry}
            Open application    erp_client.exe
            Click         image:%{ROBOT_ROOT}/images/create.png
            Type text     ${entry}
            Press keys    ctrl    s
            Press keys    enter
            [Teardown]    Close all applications

    Targeting can be currently done using coordinates (absolute or relative),
    but using template matching is preferred.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Desktop

        *** Keywords ***
        Write to field
            [Arguments]    ${text}
            Move mouse   image:input_label.png
            Move mouse   offset:200,0
            Click
            Type text    ${text}
            Press keys   enter
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Register keyword libraries to LibCore
        libraries = [
            ApplicationKeywords(self),
            ClipboardKeywords(self),
            FinderKeywords(self),
            KeyboardKeywords(self),
            MouseKeywords(self),
            ScreenKeywords(self),
        ]
        super().__init__(libraries)
