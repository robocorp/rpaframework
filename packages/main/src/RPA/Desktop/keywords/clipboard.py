import pyperclip
from RPA.Desktop import utils
from RPA.Desktop.keywords import LibraryContext, keyword


class ClipboardKeywords(LibraryContext):
    """Keywords for interacting with the system clipboard."""

    @keyword
    def copy_to_clipboard(self, locator) -> str:
        """Read value to system clipboard from given input element.

        :param locator: Locator for element
        :returns:       Current clipboard value

        Example:

        .. code-block:: robotframework

            ${value}=    Copy to clipboard    ResultPage.Counter
            Log    Copied text: ${value}
        """
        if utils.is_macos():
            self.ctx.click(locator, "triple click")
            self.ctx.press_keys("cmd", "c")
        else:
            self.ctx.click(locator, "triple click")
            self.ctx.press_keys("ctrl", "c")
        return self.get_clipboard_value()

    @keyword
    def paste_from_clipboard(self, locator) -> None:
        """Paste value from system clipboard into given element.

        :param locator: Locator for element

        Example:

        .. code-block:: robotframework

            Copy to clipboard       coordinates:401,198
            Paste from clipboard    coordinates:822,710
        """
        match = self.ctx.find_element(locator)
        text = pyperclip.paste()
        self.ctx.click(match)

        self.ctx.type_text(str(text))

    @keyword
    def clear_clipboard(self) -> None:
        """Clear the system clipboard."""
        pyperclip.copy("")

    @keyword
    def get_clipboard_value(self) -> str:
        """Read current value from system clipboard.

        Example:

        .. code-block:: robotframework

            Copy to clipboard       coordinates:401,198
            ${text}=    Get clipboard value
            Log    We just copied '${text}'
        """
        return pyperclip.paste()

    @keyword
    def set_clipboard_value(self, text: str) -> None:
        """Write given value to system clipboard.

        Example:

        .. code-block:: robotframework

            Set clipboard value     This is some text.
            Paste from clipboard    coordinates:822,710
        """
        if not isinstance(text, str):
            self.logger.debug(f"Non-string input value {text} for clipboard")
        pyperclip.copy(str(text))
