from typing import Any
from RPA.Desktop.keywords import LibraryContext, keyword


def to_key(key: str) -> Any:
    """Convert key string to correct enum value."""
    # pylint: disable=C0415
    from pynput.keyboard import Key, KeyCode

    if isinstance(key, (Key, KeyCode)):
        return key

    value = str(key).lower().strip()

    # Check for modifier or function key, e.g. ctrl or f4
    try:
        return Key[value]
    except KeyError:
        pass

    # Check for individual character
    if len(value) == 1:
        try:
            return KeyCode.from_char(value)
        except ValueError:
            pass

    raise ValueError(f"Invalid key: {key}")


class KeyboardKeywords(LibraryContext):
    """Keywords for sending inputs through an (emulated) keyboard."""

    def __init__(self, ctx):
        super().__init__(ctx)
        try:
            # pylint: disable=C0415
            from pynput.keyboard import Controller

            self._keyboard = Controller()
            self._error = None
        except ImportError as exc:
            self._error = exc

    @keyword
    def type_text(self, text: str, *modifiers: str, enter: bool = False) -> None:
        """Type text one letter at a time.

        :param text:       Text to write
        :param modifiers:  Modifier or functions keys held during typing
        :param enter:      Press Enter / Return key after typing text

        Example:

        .. code-block:: robotframework

            Type text    this text will be uppercase    shift
        """
        if self._error:
            raise self._error

        keys = [to_key(key) for key in modifiers]

        with self._keyboard.pressed(*keys):
            self._keyboard.type(text)

        if enter:
            self.press_keys("enter")

    @keyword
    def press_keys(self, *keys: str) -> None:
        """Press multiple keys down simultaneously.

        :param keys: Keys to press

        Example:

        .. code-block:: robotframework

            Press keys    ctrl  alt  delete

            Press keys    ctrl  a
            Press keys    ctrl  c
            ${all_text}=  Get clipboard value
            Log    Text box content was: ${all_text}
        """
        if self._error:
            raise self._error

        keys = [to_key(key) for key in keys]
        self.logger.info("Pressing keys: %s", ", ".join(str(key) for key in keys))

        for key in keys:
            self._keyboard.press(key)

        for key in reversed(keys):
            self._keyboard.release(key)

    @keyword
    def type_text_into(
        self, locator: str, text: str, clear: bool = False, enter: bool = False
    ) -> None:
        """Type text at the position indicated by given locator.

        :param locator: Locator of input element
        :param text:    Text to write
        :param clear:   Clear element before writing
        :param enter:      Press Enter / Return key after typing text

        Example:

        .. code-block:: robotframework

            Type text into    LoginForm.Name      Marky Mark
            Type text into    LoginForm.Password  ${PASSWORD}
        """
        if self._error:
            raise self._error

        self.ctx.click(locator)

        if clear:
            self.press_keys("ctrl", "a")
            self.press_keys("delete")

        self.type_text(text, enter=enter)
