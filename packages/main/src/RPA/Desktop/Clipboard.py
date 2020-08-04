# pylint: disable=c-extension-no-member
import logging
import platform

import clipboard

if platform.system() == "Windows":
    import win32clipboard


class Clipboard:
    """RPA Framework library for cross platform clipboard management.

    Will use `win32` package on Windows and `clipboard` package on Linux and Mac.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def copy_to_clipboard(self, text):
        """Copy text to clipboard

        :param text: to copy
        """
        self.logger.debug("copy_to_clipboard")
        if platform.system() == "Windows":
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
            win32clipboard.CloseClipboard()
        else:
            clipboard.copy(text)

    def paste_from_clipboard(self):
        """Paste text from clipboard

        :return: text
        """
        self.logger.debug("paste_from_clipboard")
        if platform.system() == "Windows":
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT):
                text = win32clipboard.GetClipboardData()
            else:
                text = None
            win32clipboard.CloseClipboard()
            return text
        else:
            return clipboard.paste()

    def clear_clipboard(self):
        """Clear clipboard contents
        """
        self.logger.debug("clear_clipboard")
        if platform.system() == "Windows":
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.CloseClipboard()
        else:
            clipboard.copy("")
