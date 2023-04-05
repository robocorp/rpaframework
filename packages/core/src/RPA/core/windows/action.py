from pathlib import Path
from typing import Union

from RPA.core.vendor.deco import keyword as method
from RPA.core.windows.context import ActionNotPossible, WindowsContext
from RPA.core.windows.locators import Locator


class ActionMethods(WindowsContext):
    """Keywords for performing desktop actions."""

    @method
    def screenshot(self, locator: Locator, filename: Union[str, Path]) -> str:
        # Saves the control image from the provided element.
        item = self.ctx.get_element(locator).item
        meth = "CaptureToImage"
        capture_to_image = getattr(item, meth, None)
        if not capture_to_image:
            raise ActionNotPossible(
                f"Element found with {locator!r} does not have the {meth!r}"
                " attribute"
            )

        item.SetFocus()
        filepath = str(Path(filename).expanduser().resolve())
        capture_to_image(filepath)
        return filepath
