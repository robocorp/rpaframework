import inspect
from pathlib import Path
from typing import List, Optional

from RPA.core.windows.locators import Locator

from RPA.Windows import utils
from RPA.Windows.keywords import (
    ActionNotPossible,
    keyword,
    LibraryContext,
)

if utils.IS_WINDOWS:
    import uiautomation as auto
    from uiautomation import TreeNode


class ElementKeywords(LibraryContext):
    """Keywords for handling Control elements"""

    @keyword
    def set_anchor(
        self,
        locator: Locator,
        timeout: Optional[float] = None,
    ) -> None:
        """Set anchor to an element specified by the locator.

        All following keywords using locators will use this element
        as an root element. Specific use case could be setting
        anchor to TableControl element and then getting column data
        belonging to that TableControl element.

        To release anchor call ``Clear Anchor`` keyword.

        :param locator: string locator or Control element
        :param timeout: timeout in seconds for element lookup (default 10.0)

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
    def clear_anchor(self) -> None:
        """Clears control anchor set by ``Set Anchor``

        This means that all following keywords accessing elements
        will use active window or desktop as root element.
        """
        self.ctx.anchor_element = None

    @keyword
    def print_tree(
        self,
        locator: Optional[Locator] = None,
        max_depth: int = 8,
        capture_image_folder: Optional[str] = None,
        log_as_warnings: bool = False,
    ) -> None:
        """Print Control element tree.

        Windows application structure can contain multilevel element
        structure. Understanding this structure is important for
        creating locators.

        This keyword can be used to output application element structure
        starting with the element defined by the `locator`.

        :param locator: string locator or Control element
        :param max_depth: maximum depth level (defaults to 8)
        :param encoding: defaults to "utf-8"
        :param capture_image_folder: if None images are not captured
        :param log_as_warnings: if set log messages are visible on the console
        """

        def GetFirstChild(ctrl: TreeNode) -> TreeNode:
            return ctrl.GetFirstChildControl()

        def GetNextSibling(ctrl: TreeNode) -> TreeNode:
            return ctrl.GetNextSiblingControl()

        index = 1
        target_elem = self.ctx.get_element(locator)
        image_folder = None
        if capture_image_folder:
            image_folder = Path(capture_image_folder).expanduser().resolve()
            image_folder.mkdir(parents=True, exist_ok=True)
        control_log = self.logger.warning if log_as_warnings else self.logger.info

        for control, depth in auto.WalkTree(
            target_elem.item,
            getFirstChild=GetFirstChild,
            getNextSibling=GetNextSibling,
            includeTop=True,
            maxDepth=max_depth,
        ):
            control_str = str(control)
            if image_folder:
                capture_filename = f"{control.ControlType}_{index}.png"
                img_path = str(image_folder / capture_filename)
                try:
                    control.CaptureToImage(img_path)
                except Exception as exc:  # pylint: disable=broad-except
                    self.logger.warning(
                        "Couldn't capture into %r due to: %s", img_path, exc
                    )
                else:
                    control_str += f" [{capture_filename}]"
            control_log(" " * depth * 4 + control_str)
            index += 1

    @keyword
    def get_attribute(self, locator: Locator, attribute: str) -> str:
        """Get attribute value of the element defined by the locator.

        :param locator: string locator or Control element
        :param attribute: name of the attribute to get
        :return: value of attribute

        Example:

        .. code-block:: robotframework

            ${id}=   Get Attribute  type:Edit name:firstname   AutomationId
        """
        # TODO. Add examples
        element = self.ctx.get_element(locator)
        attr = hasattr(element.item, attribute)
        if not attr:
            raise ActionNotPossible(
                f"Element found with {locator!r} does not have {attribute!r} attribute"
            )
        if callable(attr):
            raise ActionNotPossible(
                f"Can't access attribute {attribute!r} of element {element!r}"
            )
        return str(getattr(element.item, attribute))

    @keyword
    def list_attributes(self, locator: Locator) -> List:
        """List all element attributes.

        :param locator: string locator or Control element
        :return: list of element attributes (strings)
        """
        element = self.ctx.get_element(locator)
        element_attributes = [e for e in dir(element.item) if not e.startswith("_")]
        attributes = []

        for attr_name in element_attributes:
            attr = getattr(element.item, attr_name)
            if not inspect.ismethod(attr):
                attributes.append(attr_name)
        return attributes
