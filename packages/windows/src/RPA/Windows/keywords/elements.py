import inspect
from pathlib import Path
from typing import List, Union
from RPA.Windows.keywords import (
    ActionNotPossible,
    keyword,
    LibraryContext,
)
from RPA.Windows import utils

if utils.is_windows():
    import uiautomation as auto
    from uiautomation.uiautomation import Control


class ElementKeywords(LibraryContext):
    """Keywords for handling Control elements"""

    @keyword
    def set_anchor(self, locator: Union[str, Control]):
        """Set anchor to an element specified by the locator.

        All following keywords using locators will use this element
        as an root element. Specific use case could be setting
        anchor to TableControl element and then getting column data
        belonging to that TableControl element.

        To release anchor call ``Clear Anchor`` keyword.

        :param locator: string locator or Control element

        Example:

        .. code-block:: robotframework

            Set Anchor  type:Table name:Orders depth:16
            FOR  ${row}  IN RANGE  200
                ${number}=  Get Value   name:number row ${row}
                Exit For Loop If   $number == ${EMPTY}
                ${sum}=  Get Value   name:sum row ${row}
                Log   Order number:${number} has sum:{sum}
            END
            Clear Anchor
        """
        self.ctx.anchor_element = self.ctx.get_element(locator)

    @keyword
    def clear_anchor(self):
        """Clears control anchor set by ``Set Anchor``"""
        self.ctx.anchor_element = None

    @keyword
    def print_tree(
        self,
        locator: Union[str, Control] = None,
        max_depth: int = 8,
        encoding: str = "utf-8",
        capture_image_folder: str = None,
        log_as_warnings: bool = False,
    ):
        """Print Control element tree.

        Windows application structure can contain multilevel element
        structure. Understanding this structure is important for
        creating locators.

        This keyword can be used to output application element structure
        starting with the element defined by the `locator`.

        :param locator: string locator or Control element
        :param max_depth: level , defaults to 8
        :param encoding: defaults to "utf-8"
        :param capture_image_folder: if None images are not captured
        :param log_as_warnings: if set log messages are visible on the console
        """
        index = 1

        def GetFirstChild(element):
            return element.GetFirstChildControl()

        def GetNextSibling(element):
            return element.GetNextSiblingControl()

        target = self.ctx.get_element(locator)
        image_folder = (
            Path(capture_image_folder).resolve() if capture_image_folder else None
        )
        for element, depth in auto.WalkTree(
            target,
            getFirstChild=GetFirstChild,
            getNextSibling=GetNextSibling,
            includeTop=True,
            maxDepth=max_depth,
        ):
            element_as_text = (
                str(element).encode(encoding) if encoding else str(element)
            )
            if image_folder:
                capture_filename = f"{element.ControlType}_{index}.png"
                # TODO. exception handling
                element.CaptureToImage(str(image_folder / capture_filename))
                element_as_text += f" [{capture_filename}]"
            if log_as_warnings:
                self.ctx.logger.warning(f"{' ' * depth * 4}{element_as_text}")
            else:
                self.ctx.logger.info(f"{' ' * depth * 4}{element_as_text}")
            index += 1

    @keyword
    def get_attribute(self, locator: Union[str, Control], attribute: str):
        """Get attribute value of the element defined by the locator.

        :param locator: string locator or Control element
        :param attribute: name of the attribute to get

        Example:

        .. code-block:: robotframework

            ${value}=   Get Attribute
            ...  locator=type:Edit name:firstname
            ...  attribute=AutomationId
        """
        # TODO. Add examples
        element = self.ctx.get_element(locator)
        attr = getattr(element, attribute, None)
        if not attr:
            raise ActionNotPossible(
                'Element "%s" does not have "%s" attribute' % (locator, attribute)
            )
        if callable(attribute):
            raise ActionNotPossible(
                'Can\'t access attribute "%s" of element "%s"' % (attribute, locator)
            )
        return str(attr)

    @keyword
    def list_attributes(self, locator: Union[str, Control]) -> List:
        """List all element attributes.

        :param locator: string locator or Control element
        """
        element = self.ctx.get_element(locator)
        element_attributes = [e for e in dir(element) if not e.startswith("_")]
        attributes = []

        for e in element_attributes:
            if not inspect.ismethod(e):
                attributes.append(str(e))
