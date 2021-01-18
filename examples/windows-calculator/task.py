""" Windows Calculator robot. """
import logging
import sys
from time import sleep

from RPA.Desktop.Windows import Windows

library = None
stdout = logging.StreamHandler(sys.stdout)

logging.basicConfig(
    level=logging.DEBUG,
    format="[{%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    handlers=[stdout],
)

LOGGER = logging.getLogger(__name__)


def result_should_be(expected):
    element = library.get_element("CalculatorResults")
    value = int(element["rich_text"].replace("Display is ", ""))
    LOGGER.info("Got %s value, expected value %s" % (value, expected))
    assert value == expected


def using_mouse():
    library.mouse_click("One")
    library.mouse_click("Plus")
    library.mouse_click("Five")
    library.mouse_click("Equals")
    result_should_be(6)


def using_keys():
    library.send_keys("320{+}480{=}")
    result_should_be(800)


def open_navigation(navigation_item):
    library.wait_for_element("Open Navigation")
    library.mouse_click("Open Navigation")
    library.refresh_window()
    library.mouse_click(navigation_item)
    library.refresh_window()


def main():
    library.open_executable("calc.exe", "Calculator")
    open_navigation("Standard Calculator")
    controls, elements = library.get_window_elements()
    LOGGER.info("Printing elements")
    for elem in elements:
        LOGGER.info(elem)
    LOGGER.info("Printing controls")
    for ctrl in controls:
        LOGGER.info(ctrl)
    using_mouse()
    library.mouse_click("Clear")
    using_keys()
    open_navigation("Date Calculation Calculator")
    sleep(1)


def minimize_maximize(windowtitle):
    library.minimize_dialog()
    sleep(1)
    library.restore_dialog()
    sleep(1)
    library.minimize_dialog()
    sleep(1)
    library.restore_dialog(windowtitle)


if __name__ == "__main__":
    library = Windows()
    try:
        main()
        minimize_maximize("Calculator")
        open_navigation("Standard Calculator")
        library.mouse_click("Clear")
        sleep(3)
    finally:
        library.close_all_applications()
