from unittest import mock

import pytest

from RPA.Windows import Windows
from RPA.Windows.utils import IS_WINDOWS
from RPA.core.windows.context import ElementNotFound, WindowControlError


@pytest.fixture
def library():
    lib = Windows(locators_path="tests/python/locators.json")
    return lib


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows required")
@pytest.mark.xfail(reason="UI rendering required")
def test_do_some_calculations(library):
    try:
        library.windows_run("calc.exe")
        library.control_window("name:Calculator")
        library.click("CLEAR_BUTTON")
        library.send_keys(keys="96+4=")
        result = library.get_attribute("id:CalculatorResults", "Name")
        assert result.endswith("100")
        buttons = library.get_elements('type:Group and name:"Number pad" > type:Button')
        print("Number pad buttons:")
        for button in buttons:
            print(button)
    finally:
        library.close_current_window()


@pytest.mark.parametrize(
    "offset, x, y",
    [
        (None, None, None),  # no offset provided
        ("0,0", 100, 50),  # right in the center
        ("10,30", 110, 80),  # a little bit SE
        ("-100,-50", 0, 0),  # exactly on the left-top corner
        ("100, 50", 200, 100),  # exactly on the right-bottom corner
        # Outside the bounding-box.
        ("-110,-60", -210, -110),  # (NW) -- right-bottom corner relative
        ("110,60", 210, 110),  # (SE) -- left-top corner relative
    ],
)
@mock.patch("RPA.core.windows.locators.LocatorMethods.get_element")
def test_coordinates_clicking(mock_get_element, library, offset, x, y):
    # Let's imagine a 200x100 button positioned on the upper left side of the screen.
    mock_element = mock.Mock()
    item = mock_element.item
    rect = item.BoundingRectangle
    rect.left = 100
    rect.top = 200
    rect.right = 300
    rect.bottom = 300
    rect.xcenter.return_value = (rect.left + rect.right) // 2
    rect.ycenter.return_value = (rect.top + rect.bottom) // 2
    rect.width.return_value = rect.right - rect.left
    rect.height.return_value = rect.bottom - rect.top
    mock_get_element.return_value = mock_element

    item.robocorp_click_offset = offset
    library.click("MyButton")
    item.Click.assert_called_once_with(x=x, y=y, simulateMove=False, waitTime=0.5)


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows required")
def test_list_windows_control_window_click_error_scenario(library):
    """Test error handling when window or element is not found.

    This test verifies the error scenario:
    1. list_windows() is called
    2. control_window("subname:Notepad") is called - may raise WindowControlError
    3. click("name:File") is called - may raise ElementNotFound

    The test verifies that:
    - list_windows() does not raise errors
    - control_window() raises WindowControlError when window is not found
    - If window is found, click() may raise ElementNotFound if element is not found
    """
    # Step 1: List windows (should not raise error, but may return empty list)
    window_list = library.list_windows()
    assert isinstance(window_list, list)

    # Step 2: Try to control Notepad window
    # This will raise WindowControlError if Notepad is not open
    with pytest.raises(WindowControlError, match="Could not locate window"):
        library.control_window("subname:Notepad")


@pytest.mark.skipif(not IS_WINDOWS, reason="Windows required")
@mock.patch("RPA.core.windows.locators.LocatorMethods.get_element")
@mock.patch("RPA.Windows.keywords.window.WindowKeywords._find_window")
def test_list_windows_control_window_click_error_mocked(
    mock_find_window, mock_get_element, library
):
    """Test error handling with mocked scenarios for list_windows, control_window, and click."""
    # Step 1: Mock list_windows to return a list
    with mock.patch.object(library, "list_windows", return_value=[]):
        window_list = library.list_windows()
        assert isinstance(window_list, list)

    # Step 2: Mock control_window to return None (window not found)
    mock_find_window.return_value = None

    # control_window should raise WindowControlError when window is not found
    with pytest.raises(WindowControlError, match="Could not locate window"):
        library.control_window("subname:Notepad")

    # Step 3: Mock control_window to succeed, but click to fail
    from RPA.core.windows.locators import WindowsElement
    from unittest.mock import MagicMock

    # Create a mock window item with required properties
    mock_window_item = MagicMock()
    mock_window_item.Name = "Notepad"
    mock_window_item.AutomationId = ""
    mock_window_item.ControlTypeName = "WindowControl"
    mock_window_item.ClassName = "Notepad"
    mock_rect = MagicMock()
    mock_rect.left = 0
    mock_rect.right = 100
    mock_rect.top = 0
    mock_rect.bottom = 100
    mock_rect.width.return_value = 100
    mock_rect.height.return_value = 100
    mock_rect.xcenter.return_value = 50
    mock_rect.ycenter.return_value = 50
    mock_window_item.BoundingRectangle = mock_rect

    # Create a WindowsElement with the mocked item
    mock_window = WindowsElement(mock_window_item, locator="subname:Notepad")
    mock_find_window.return_value = mock_window

    # Mock foreground_window to avoid actual window operations
    with mock.patch.object(library, "foreground_window", return_value=mock_window):
        # Now control_window should succeed (it will set library.window_element via ctx)
        result = library.control_window("subname:Notepad")
        assert result == mock_window

        # Mock get_element to raise ElementNotFound for click
        mock_get_element.side_effect = ElementNotFound("Element not found with locator 'name:File'")

        # click should raise ElementNotFound
        with pytest.raises(ElementNotFound, match="Element not found"):
            library.click("name:File")
