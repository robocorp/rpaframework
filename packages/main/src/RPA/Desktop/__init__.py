import logging
import platform
import sys
import warnings

if platform.system() == "Windows":
    # Configure comtypes to not generate DLL bindings into
    # current environment, instead keeping them in memory.
    # Slower, but prevents dirtying environments.
    import comtypes.client

    comtypes.client.gen_dir = None

    # Ignore pywinauto warning about threading mode,
    # which comtypes initializes to STA instead of MTA on import.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        import pywinauto

# pylint: disable=wrong-import-position
from robotlibcore import DynamicCore
from RPA.Desktop.utils import Buffer, is_windows
from RPA.Desktop.keywords import (
    ElementNotFound,
    MultipleElementsFound,
    TimeoutException,
    ApplicationKeywords,
    ClipboardKeywords,
    FinderKeywords,
    KeyboardKeywords,
    MouseKeywords,
    ScreenKeywords,
    TextKeywords,
)


class Desktop(DynamicCore):
    """`Desktop` is a cross-platform library for navigating and interacting with
    desktop environments. It can be used to automate applications through
    the same interfaces that are available to human users.

    The library includes the following features:

    - Mouse and keyboard input emulation
    - Starting and stopping applications
    - Finding elements through image template matching
    - Scraping text from given regions
    - Taking screenshots
    - Clipboard management

    .. warning:: Windows element selectors are not currently supported, and require the use of ``RPA.Desktop.Windows``

    **Installation**

    The basic features such as mouse and keyboard input and application
    control work with a default ``rpaframework`` install.

    Advanced computer-vision features such as image template matching and
    OCR require an additional library called ``rpaframework-recognition``.

    The dependency can be either added separately or through additional
    extras with ``rpaframework[cv]``. If installing recognition through
    ``pip`` instead of ``conda``, the OCR feature also requires ``tesseract``.

    **Locating elements**

    To automate actions on the desktop, a robot needs to interact with various
    graphical elements such as buttons or input fields. The locations of these
    elements can be found using a feature called `locators`.

    A locator describes the properties or features of an element. This information
    can be later used to locate similar elements even when window positions or
    states change.

    The currently supported locator types are:

    =========== ================================================ ===========
    Name        Arguments                                        Description
    =========== ================================================ ===========
    alias       name (str)                                       A custom named locator from the locator database, the default.
    image       path (str)                                       Image of an element that is matched to current screen content.
    point       x (int), y (int)                                 Pixel coordinates as absolute position.
    offset      x (int), y (int)                                 Pixel coordinates relative to current mouse position.
    size        width (int), height (int)                        Region of fixed size, around point or screen top-left
    region      left (int), top (int), right (int), bottom (int) Bounding coordinates for a rectangular region.
    ocr         text (str), confidence (float, optional)         Text to find from the current screen.
    =========== ================================================ ===========

    A locator is defined by its type and arguments, divided by a colon.
    Some example usages are shown below. Note that the prefix for ``alias`` can
    be omitted as its the default type.

    .. code-block:: robotframework

        Click       point:50,100
        Click       region:20,20,100,30

        Move mouse  image:%{ROBOT_ROOT}/logo.png
        Move mouse  offset:200,0
        Click

        Click       alias:SpareBin.Login
        Click       SpareBin.Login

        Click       ocr:"Create New Account"

    You can also pass internal ``region`` objects as locators:

    .. code-block:: robotframework

        ${region}=  Find Element  ocr:"Customer name"
        Click       ${region}

    **Locator chaining**

    Often it is not enough to have one locator, but instead an element
    is defined through a relationship of various locators. For this use
    case the library supports a special syntax, which we will call
    locator chaining.

    An example of chaining:

    .. code-block:: robotframework

        # Read text from area on the right side of logo
        Read text    image:logo.png + offset:600,0 + size:400,200

    The supported operators are:

    ========== =========================================
    Operator   Description
    ========== =========================================
    then, +    Base locator relative to the previous one
    and, &&, & Both locators should be found
    or, ||, |  Either of the locators should be found
    not, !     The locator should not be found
    ========== =========================================

    Further examples:

    .. code-block:: robotframework

        # Click below either label
        Click    (image:name.png or image:email.png) then offset:0,300

        # Wait until dialog disappears
        Wait for element    not image:cookie.png

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

    **Examples**

    Both Robot Framework and Python examples follow.

    The library must be imported first.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Desktop

    .. code-block:: python

        from RPA.Desktop import Desktop
        desktop = Desktop()

    The library can open applications and interact with them through
    keyboard and mouse events.

    .. code-block:: robotframework

        *** Keywords ***
        Write entry in accounting
            [Arguments]    ${entry}
            Open application    erp_client.exe
            Click         image:%{ROBOT_ROOT}/images/create.png
            Type text     ${entry}
            Press keys    ctrl    s
            Press keys    enter

    .. code-block:: python

        def write_entry_in_accounting(entry):
            desktop.open_application("erp_client.exe")
            desktop.click(f"image:{ROBOT_ROOT}/images/create.png")
            desktop.type_text(entry)
            desktop.press_keys("ctrl", "s")
            desktop.press_keys("enter")


    Targeting can be currently done using coordinates (absolute or relative),
    but using template matching is preferred.

    .. code-block:: robotframework

        *** Keywords ***
        Write to field
            [Arguments]  ${text}
            Move mouse   image:input_label.png
            Move mouse   offset:200,0
            Click
            Type text    ${text}
            Press keys   enter

    .. code-block:: python

        def write_to_field(text):
            desktop.move_mouse("image:input_label.png")
            desktop.move_mouse("offset:200,0")
            desktop.click()
            desktop.type_text(text)
            desktop.press_keys("enter")


    Elements can be found by text too.

    .. code-block:: robotframework

        *** Keywords ***
        Click New
            Click       ocr:New

    .. code-block:: python

        def click_new():
            desktop.click('ocr:"New"')


    It is recommended to wait for the elements to be visible before
    trying any interaction. You can also pass ``region`` objects as locators.

    .. code-block:: robotframework

        *** Keywords ***
        Click New
            ${region}=  Wait For element  ocr:New
            Click       ${region}

    .. code-block:: python

        def click_new():
            region = desktop.wait_for_element("ocr:New")
            desktop.click(region)

    Another way to find elements by offsetting from an anchor:

    .. code-block:: robotframework

        *** Keywords ***
        Type Notes
            [Arguments]        ${text}
            Click With Offset  ocr:Notes  500  0
            Type Text          ${text}

    .. code-block:: python

        def type_notes(text):
            desktop.click_with_offset("ocr:Notes", 500, 0)
            desktop.type_text(text)

    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.buffer = Buffer(self.logger)

        # Register keyword libraries to LibCore
        libraries = [
            ApplicationKeywords(self),
            ClipboardKeywords(self),
            FinderKeywords(self),
            KeyboardKeywords(self),
            MouseKeywords(self),
            ScreenKeywords(self),
            TextKeywords(self),
        ]
        super().__init__(libraries)
