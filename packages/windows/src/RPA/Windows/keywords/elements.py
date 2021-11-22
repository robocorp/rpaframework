import inspect
from pathlib import Path
from typing import List, Union
from RPA.Windows.keywords import (
    ActionNotPossible,
    keyword,
    LibraryContext,
)
from RPA.Windows import utils
from .locators import DEFAULT_SEARCH_TIMEOUT, WindowsElement

if utils.is_windows():
    import uiautomation as auto


class ElementKeywords(LibraryContext):
    """Keywords for handling Control elements"""

    @keyword
    def set_anchor(
        self,
        locator: Union[WindowsElement, str],
        timeout: float = DEFAULT_SEARCH_TIMEOUT,
    ):
        """Set anchor to an element specified by the locator.

        All following keywords using locators will use this element
        as an root element. Specific use case could be setting
        anchor to TableControl element and then getting column data
        belonging to that TableControl element.

        To release anchor call ``Clear Anchor`` keyword.

        :param locator: string locator or Control element
        :param timeout: timeout in seconds for element lookup (default 5.0)

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
        self.ctx.anchor_element = self.ctx.get_element(locator, timeout=timeout)

    @keyword
    def clear_anchor(self):
        """Clears control anchor set by ``Set Anchor``"""
        self.ctx.anchor_element = None

    @keyword
    def print_tree(
        self,
        locator: Union[WindowsElement, str] = None,
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
            return element.item.GetFirstChildControl()

        def GetNextSibling(element):
            return element.item.GetNextSiblingControl()

        target = self.ctx.get_element(locator)
        image_folder = (
            Path(capture_image_folder).resolve() if capture_image_folder else None
        )
        for element, depth in auto.WalkTree(
            target.item,
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
    def get_attribute(self, locator: Union[WindowsElement, str], attribute: str):
        """Get attribute value of the element defined by the locator.

        :param locator: string locator or Control element
        :param attribute: name of the attribute to get

        Example:

        .. code-block:: robotframework

            ${id}=   Get Attribute  type:Edit name:firstname   AutomationId
        """
        # TODO. Add examples
        element = self.ctx.get_element(locator)
        attr = hasattr(element.item, attribute)
        if not attr:
            raise ActionNotPossible(
                'Element "%s" does not have "%s" attribute' % (locator, attribute)
            )
        if callable(attr):
            raise ActionNotPossible(
                'Can\'t access attribute "%s" of element "%s"' % (attribute, locator)
            )
        return str(getattr(element.item, attribute))

    @keyword
    def list_attributes(self, locator: Union[WindowsElement, str]) -> List:
        """List all element attributes.

        :param locator: string locator or Control element
        """
        element = self.ctx.get_element(locator)
        element_attributes = [e for e in dir(element.item) if not e.startswith("_")]
        attributes = []

        for attr_name in element_attributes:
            attr = getattr(element.item, attr_name)
            if not inspect.ismethod(attr):
                attributes.append(attr_name)
        return attributes
