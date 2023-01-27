# pylint: disable=missing-class-docstring
import logging
import platform
import time
from typing import Optional
from comtypes import COMError


if platform.system() == "Windows":
    # import win32com.client to fix order of imports in the SapGuiLibrary
    # pylint: disable=unused-import
    import win32com.client  # noqa: F401
    from SapGuiLibrary import SapGuiLibrary
else:
    logging.getLogger(__name__).warning(
        "RPA.SapGuiLibrary library works only on Windows platform"
    )

    class SapGuiLibrary:
        """Keywords are only available in Windows."""

        def __init__(self, *args, **kwargs):
            del args, kwargs


class SAP(SapGuiLibrary):
    __doc__ = (
        "This library wraps the upstream "
        "[https://frankvanderkuur.github.io/SapGuiLibrary.html|SapGuiLibrary]."
        "\n\n" + SapGuiLibrary.__doc__
    )

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

        if platform.system() != "Windows":
            self.logger.warning("SAP requires Windows dependencies to work.")

    def get_statusbar_type(self, window: Optional[str] = "wnd[0]") -> str:
        """Retrieves the messageType in the statusbar the given window.

        Takes screenshot on error.

        :param window: locator for the statusbar, default 'wnd[0]'
        :return: messageType of the /sbar element or empty string
        """
        return_value = ""
        try:
            return_value = self.session.findById(window + "/sbar").messageType
        except COMError as ex:
            self.take_screenshot()
            raise ValueError("Cannot find window with locator '%s'" % window) from ex
        return return_value

    def focus_and_click(self, element_id: str, wait_time: Optional[float] = None):
        """Set focus into the element and click it.

        Note. The default library wait time can be adjusted using `Set Explicit Wait`
        keyword. Library's `explicit_wait` will be used if `wait_time` parameter
        is not set.

        :param element_id: locator for the element
        :param wait_time: the wait time after the action
        """
        sleeptime = wait_time or self.explicit_wait
        self.set_focus(element_id)
        self.click_element(element_id)
        if sleeptime and sleeptime > 0:
            time.sleep(sleeptime)

    def focus_and_input_text(
        self, element_id: str, text: str, wait_time: Optional[float] = None
    ):
        """Set focus into the element and input text into it.

        Note. The default library wait time can be adjusted using `Set Explicit Wait`
        keyword. Library's `explicit_wait` will be used if `wait_time` parameter
        is not set.

        :param element_id: locator for the element
        :param text: text to be inputted
        :param wait_time: the wait time after the action
        """
        sleeptime = wait_time or self.explicit_wait
        self.set_focus(element_id)
        self.input_text(element_id, text)
        if sleeptime and sleeptime > 0:
            time.sleep(sleeptime)

    def generic_input_password(self, element_id, password):
        """Inserts the given password into the text field identified by locator.

        This keyword does NOT depend on the type of the element. Will set
        password to the element's 'text' attribute if possible.

        The password is not recorded in the log.

        :param element_id: locator for the element
        :param password: password to be inputted
        """
        self._generic_input(element_id, password, False)

    def generic_input_text(self, element_id, text):
        """Inserts the given text into the text field identified by locator.
        Use keyword `input password` to insert a password in a text field.

        This keyword does NOT depend on the type of the element. Will set
        text to the element's 'text' attribute if possible.

        :param element_id: locator for the element
        :param text: text to be inputted
        """
        self._generic_input(element_id, text)

    def get_element_type_of_object(self, element):
        """Returns the Sap element type for the given element.

        :param element: SAP element
        :return: type of the SAP element
        """
        try:
            return element.type
        except COMError as ex:
            self.take_screenshot()
            message = "Element does not have 'type' attribute: '%s'" % type(element)
            raise ValueError(message) from ex

    def _generic_input(self, element_id, text, log_text=True):
        element = self.session.findById(element_id)
        element_type = self.get_element_type_of_object(element)
        if hasattr(element, "text"):
            element.text = text
            self.session.findById(element_id).text = text
            if log_text:
                self.logger.info(
                    "Typing text '%s' into text field '%s'." % (text, element_id)
                )
            else:
                self.logger.info("Typing password into text field '%s'." % element_id)
            time.sleep(self.explicit_wait)
        else:
            self.take_screenshot()
            message = "Cannot set text for element type '%s'" % element_type
            raise ValueError(message)

    def generic_click_element(self, element_id, click_type="press"):
        """Performs a single click on a given element.

        Differs from `Click Element` keyword so that element type is ignored, instead
        `click_type` (either `press` or `select`) is performed on the element if
        possible.

        In case you want to change a value of an element like checkboxes of selecting
        an option in dropdown lists, use `select checkbox` or
        `select from list by label` instead.

        :param element_id: locator for the element
        :param click_type: either ``press`` (default) or ``select``
        """
        element = self.session.findById(element_id)
        element_type = self.get_element_type_of_object(element)
        if click_type.lower() == "select" and hasattr(element, "select"):
            element.select()
        if click_type.lower() == "press" and hasattr(element, "press"):
            element.press()
        else:
            self.take_screenshot()
            message = (
                "You cannot use '%s' on element type '%s', maybe use "
                "'select checkbox' instead?" % (click_type, element_type)
            )
            raise Warning(message)
        time.sleep(self.explicit_wait)

    def get_cell_value(self, table_id, row_num, col_id):
        """Returns the cell value for the specified cell.

        :param table_id: locator for the table element
        :param row_num: table row number
        :param col_id: table cell id
        :return: text in the specified cell
        """
        self.element_should_be_present(table_id)

        try:
            cellValue = self.session.findById(table_id).getCell(row_num, col_id).text
            return cellValue
        except COMError as ex:
            self.take_screenshot()
            message = "Cannot find Column_id '%s'." % col_id
            raise ValueError(message) from ex
