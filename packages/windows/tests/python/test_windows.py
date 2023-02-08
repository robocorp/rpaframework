import pytest
from unittest import mock

from RPA.Windows import Windows
from RPA.Windows.utils import IS_WINDOWS


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
