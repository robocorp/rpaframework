from pathlib import Path
from typing import Union
from RPA.Windows.keywords import (
    ActionNotPossible,
    keyword,
    LibraryContext,
)
from RPA.Windows import utils

if utils.is_windows():
    import uiautomation as auto
    from uiautomation.uiautomation import Control


class ControlKeywords(LibraryContext):
    """Keywords for handling Control objects"""

    def __init__(self, ctx):
        super().__init__(ctx)
        self.control_anchor = None

    @keyword
    def set_control_anchor(self, locator: Union[str, Control]):
        """Set control anchor to specified Control object.

        All following Control accesses will use this anchor Control
        as a "parent" object. Specific use case could be setting
        anchor to TableControl object and then getting column data
        belonging to that TableControl object.

        To release anchor call ``Clear Control Anchor`` keyword.

        :param locator: string locator or Control object

        Example:

        .. code-block:: robotframework

            Set Control Anchor  type:Table name:Orders depth:16
            FOR  ${row}  IN RANGE  200
                ${number}=  Get Item Value   name:number row ${row}
                Exit For Loop If   $number == ${EMPTY}
                ${sum}=  Get Item Value   name:sum row ${row}
                Log   Order number:${number} has sum:{sum}
            END
            Clear Control Anchor
        """
        self.control_anchor = self.ctx.get_control(locator)

    @keyword
    def clear_control_anchor(self):
        """Clears control anchor set by ``Set Control Anchor``"""
        self.control_anchor = None

    @keyword
    def print_control_tree(
        self,
        locator: Union[str, Control] = None,
        max_depth: int = 8,
        encoding: str = "utf-8",
        capture_image_folder: str = None,
        log_as_warnings: bool = False,
    ):
        """Print Control object tree

        :param locator: string locator or Control object
        :param max_depth: level , defaults to 8
        :param encoding: defaults to "utf-8"
        :param capture_image_folder: if None images are not captured
        :param log_as_warnings: if set log messages are visible on the console
        """
        index = 1

        def GetFirstChild(control):
            return control.GetFirstChildControl()

        def GetNextSibling(control):
            return control.GetNextSiblingControl()

        target = self.ctx.get_control(locator)
        image_folder = (
            Path(capture_image_folder).resolve() if capture_image_folder else None
        )
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
            if image_folder:
                capture_filename = f"{control.ControlType}_{index}.png"
                # TODO. exception handling
                control.CaptureToImage(str(image_folder / capture_filename))
                control_as_text += f" [{capture_filename}]"
            if log_as_warnings:
                self.ctx.logger.warning(f"{' ' * depth * 4}{control_as_text}")
            else:
                self.ctx.logger.info(f"{' ' * depth * 4}{control_as_text}")
            index += 1

    @keyword
    def get_control_attribute(self, locator: Union[str, Control], attribute: str):
        """Get attribute of Control object matching locator.

        :param locator: string locator or Control object
        :param attribute: name of the attribute to get

        Example:

        .. code-block:: robotframework

            ${value}=   Get Control Attribute   type:Edit name:firstname   GetValue
        """
        # TODO. Add examples
        control = self.ctx.get_control(locator)
        if hasattr(control, attribute):
            attr = getattr(control, attribute, None)
            return attr() if callable(attr) else str(attr)
        else:
            raise ActionNotPossible(
                "Control '%s' does not have '%s' attribute" % (locator, attribute)
            )
