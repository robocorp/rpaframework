import pyperclip
from RPA.Desktop.keywords import LibraryContext, keyword


class ClipboardKeywords(LibraryContext):
    """Keywords for interacting with the system clipboard."""

    @keyword
    def copy_to_clipboard(self, locator):
        """Read value to system clipboard from given input element.

        Example:

        .. code-block:: robotframework

            ${value}=    Copy to clipboard    ResultPage.Counter
            Log    Copied text: ${value}

        :param locator: Locator for element
        :returns:       Current clipboard value
        """
        self.ctx.click(locator, "triple click")
        self.ctx.press_keys("ctrl", "c")
        return self.get_clipboard_value()

    @keyword
    def paste_from_clipboard(self, locator):
        """Paste value from system clipboard into given element.

        Example:

        .. code-block:: robotframework

            Copy to clipboard       coordinates:401,198
            Paste from clipboard    coordinates:822,710

        :param locator: Locator for element
        """
        match = self.find_element(locator)
        text = pyperclip.paste()
        self.ctx.click(match)
        self.ctx.type_text(text)

    @keyword
    def clear_clipboard(self):
        """Clear the system clipboard."""
        pyperclip.copy("")

    @keyword
    def get_clipboard_value(self):
        """Read current value from system clipboard.

        Example:

        .. code-block:: robotframework

            Copy to clipboard       coordinates:401,198
            ${text}=    Get clipboard value
            Log    We just copied '${text}'
        """
        return pyperclip.paste()

    @keyword
    def set_clipboard_value(self, text):
        """Write given value to system clipboard.

        Example:

        .. code-block:: robotframework

            Set clipboard value     This is some text.
            Paste from clipboard    coordinates:822,710
        """
        pyperclip.copy(text)
