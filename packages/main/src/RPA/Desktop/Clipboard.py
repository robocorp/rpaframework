# pylint: disable=c-extension-no-member
import logging
import platform

import pyperclip as clipboard

if platform.system() == "Windows":
    import win32clipboard


class Clipboard:
    """*DEPRECATED!!* Use library RPA.Desktop's clipboard functionality instead.

    `Clipboard` is a library for managing clipboard - **copy** text to,
    **paste** text from, and **clear** clipboard contents.

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Desktop.Clipboard

        *** Tasks ***
        Clipping
            Copy To Clipboard   Text from Robot to clipboard
            ${var}=             Paste From Clipboard
            Clear Clipboard

    **Python**

    .. code-block:: python

        from RPA.Desktop.Clipboard import Clipboard

        clip = Clipboard()
        clip.copy_to_clipboard('Text from Python to clipboard')
        text = clip.paste_from_clipboard()
        print(f"clipboard had text: '{text}'")
        clip.clear_clipboard()
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def copy_to_clipboard(self, text):
        """*DEPRECATED!!* Use `RPA.Desktop` library's `Copy to Clipboard` instead.

        Copy text to clipboard

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
        """*DEPRECATED!!* Use `RPA.Desktop` library's `Paste from Clipboard` instead.

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
        """*DEPRECATED!!* Use `RPA.Desktop` library's `Clear Clipboard` instead.
        Clear clipboard contents"""
        self.logger.debug("clear_clipboard")
        if platform.system() == "Windows":
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.CloseClipboard()
        else:
            clipboard.copy("")
