""" An example robot. """
import logging
import os
from pathlib import Path
import sys
from time import sleep

from RPA.Desktop.Windows import Windows
from variables import CURRENT_DATE, CURRENT_TIME, CASH_IN, ON_US, NOT_US


application_path = Path(os.getenv("UIDEMO_EXE"))

library = None
stdout = logging.StreamHandler(sys.stdout)

logging.basicConfig(
    level=logging.DEBUG,
    format="[{%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    handlers=[stdout],
)

LOGGER = logging.getLogger(__name__)


def set_slider_value(locator, slidervalue):
    element, _ = library.find_element(locator)
    LOGGER.debug(dir(element))
    if element and len(element) == 1:
        target_element = element[0]
    else:
        raise ValueError("Did not find unique element")
    left, top, right, bottom = library._get_element_coordinates(target_element)
    width = right - left
    middle = top + int((bottom - top) / 2)
    point = left + int(width * slidervalue)
    library.mouse_click_coords(point, middle)


def do_the_application_login():
    library.open_executable(r"%s" % application_path, "UiDemo")
    library.type_into("user", "admin")
    library.type_into("pass", "password")
    library.mouse_click("name:'Log In' and type:Button")
    library.open_dialog("UIDemo")


def click_transactions():
    library.mouse_click("name:'Split Deposit' and type:RadioButton")
    library.mouse_click("name:Withdrawal and type:RadioButton")
    library.mouse_click("name:Deposit and type:RadioButton")


def click_configurations():
    library.mouse_click("name:'Use Cash Count' and type:CheckBox", focus="topleft")
    library.mouse_click("name:'Use Both' and type:RadioButton", focus="topleft")
    library.mouse_click("name:'Use Amount' and type:RadioButton", focus="topleft")
    library.mouse_click("name:'Use Piece Count' and type:RadioButton", focus="topleft")
    library.mouse_click(
        "name:'Reverse Denomination' and type:CheckBox", focus="topleft"
    )
    library.mouse_click("name:'Eliminate $2' and type:CheckBox", focus="topleft")


def click_settings():
    library.mouse_click("name:GraphLabel and type:CheckBox")
    library.mouse_click("name:TrainingTip and type:CheckBox")
    library.mouse_click("name:EnableAdditional and type:CheckBox")
    library.mouse_click("name:ChangeTItle and type:CheckBox")
    library.mouse_click("name:ShowExcluding and type:CheckBox")


def type_cash(cash_in, on_us_check, not_on_us_check):
    library.type_into(CASH_IN, cash_in)
    library.type_into(ON_US, on_us_check)
    library.type_into(NOT_US, not_on_us_check)


def main():
    do_the_application_login()
    currentdate = library.get_text(CURRENT_DATE)
    currenttime = library.get_text(CURRENT_TIME)
    LOGGER.info(f"CURRENT DATE: {currentdate['children_texts']}")
    LOGGER.info(f"CURRENT TIME: {currenttime['children_texts']}")

    click_transactions()
    click_configurations()
    library.minimize_dialog()
    sleep(3)
    library.restore_dialog()
    type_cash(500, 300, 100)
    click_settings()

    set_slider_value("id:uiScaleSlider and type:Slider", 0.2)
    sleep(5)
    winlist = library.get_window_list()
    for w in winlist:
        LOGGER.info(w)
    library.refresh_window()
    set_slider_value("id:uiScaleSlider ad type:Slider", 0.5)
    sleep(5)
    LOGGER.info("Done.")


if __name__ == "__main__":
    library = Windows()
    try:
        main()
    finally:
        library.close_all_applications()
