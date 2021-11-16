from typing import Union
from RPA.Windows.keywords import (
    ActionNotPossible,
    keyword,
    LibraryContext,
    WindowControlError,
)
from RPA.Windows import utils

if utils.is_windows():
    import uiautomation as auto
    from uiautomation.uiautomation import Control


class ControlKeywords(LibraryContext):
    """Keywords for handling Control objects"""

    @keyword
    def print_control_tree(
        self, target=None, max_depth=2, encoding="utf-8", level="info"
    ):
        """[summary]

        :param target: [description], defaults to None
        :param max_depth: [description], defaults to 2
        :param encoding: [description], defaults to "utf-8"
        :param level: [description], defaults to "info"
        """
        index = 1

        def GetFirstChild(control):
            return control.GetFirstChildControl()

        def GetNextSibling(control):
            return control.GetNextSiblingControl()

        # auuto.GetRootControl()
        target = target or self.ctx.window
        for control, depth in auto.WalkTree(
            target,
            getFirstChild=GetFirstChild,
            getNextSibling=GetNextSibling,
            includeTop=True,
            maxDepth=max_depth,
        ):
            control_as_text = (
                str(control).encode(encoding) if encoding else str(control)
            )
            if level == "info":
                self.ctx.logger.info(f"{' ' * depth * 4}{control_as_text}")
            else:
                self.ctx.logger.warning(f"{' ' * depth * 4}{control_as_text}")
            # control.CaptureToImage(f"{control.ControlType}_{index}.png")
            index += 1

    @keyword
    def get_control_attribute(self, locator: Union[str, Control], attribute: str):
        """Get attribute of Control object matching locator.

        :param locator: string locator or Control object
        :param attribute: name of the attribute to get
        """
        control = locator
        if isinstance(locator, str):
            try:
                control = self.ctx.get_control(locator)
            except Exception as err:
                raise WindowControlError(str(err)) from err
        if hasattr(control, attribute):
            attr = getattr(control, attribute, None)
            return attr() if callable(attr) else str(attr)
        else:
            raise ActionNotPossible(
                "Control '%s' does not have '%s' attribute" % (locator, attribute)
            )
