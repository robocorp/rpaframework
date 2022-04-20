# import pytest
from RPA.Windows import Windows

#
# Problem with pytest
# https://github.com/pywinauto/pywinauto/issues/858
#
# @pytest.fixture
# def library():
#     library = Windows()
#     return library

library = Windows(locators_path="tests/python/locators.json")


def test_do_some_calculations():  # (library):
    try:
        library.windows_run("calc.exe")
        library.control_window("name:Calculator")
        library.click("CLEAR_BUTTON")
        library.send_keys(keys="96+4=")
        result = library.get_attribute("id:CalculatorResults", "Name")
        print(result)
        buttons = library.get_elements('type:Group and name:"Number pad" > type:Button')
        for button in buttons:
            print(button)
    finally:
        library.close_current_window()


if __name__ == "__main__":
    test_do_some_calculations()
