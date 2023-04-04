import inspect
from typing import List, Optional

from RPA.core.windows.elements import ElementMethods, StructureType
from RPA.core.windows.locators import Locator

from RPA.Windows.keywords import ActionNotPossible, keyword


class ElementKeywords(ElementMethods):
    """Keywords for handling Control elements"""

    @keyword
    def set_anchor(
        self,
        locator: Locator,
        timeout: Optional[float] = None,
    ) -> None:
        """Set anchor to an element specified by the locator.

        All following keywords using locators will use this element
        as a root element. Specific use case could be setting
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
        return_structure: bool = False,
    ) -> Optional[StructureType]:
        """Print a tree of control elements.

        A Windows application structure can contain multilevel element structure.
        Understanding this structure is crucial for creating locators. (based on
        controls' details and their parent-child relationship)

        This keyword can be used to output logs of application's element structure,
        starting with the element defined by the provided `locator` as root. Switch
        the `return_structure` parameter to `True` to get a tree of elements returned
        as well. (off by default to save memory)

        - The printed structure displays a tree prefixed with "depth" - "position" so
          you know how deep (0 means root) in the tree you are and on what position
          (1-indexed) the child you're looking for is.
        - The returned structure is a dictionary with all the children flattened per
          depth level. Additionally, these `WindowsElement` objects contain a relevant
          locator composed of "root > path" which will help to identify the element in
          the tree.

        Portal example:
        https://robocorp.com/portal/robot/robocorp/example-windows-element-path

        :param locator: The root of the tree to output.
        :param max_depth: Maximum depth level. (defaults to 8)
        :param capture_image_folder: If set, controls' images will be captured in this
            path.
        :param log_as_warnings: Enables highlighted logs (at the beginning of the log
            file as warnings) and increases visibility in the output console.
        :param return_structure: A flattened tree with all the elements collated by
            level will be returned if this is enabled.
        :returns: Optionally a dictionary of children per depth level when
            `return_structure` is enabled.

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Display Element Structure
                ${tree} =   Print Tree      Calculator > path:2|3|2|8
                ...     return_structure=${True}
                Log To Console      ${tree}

        **Example: Python**

        .. code-block:: python

            from RPA.Windows import Windows

            lib = Windows()
            tree = lib.print_tree("Calculator > path:2|3|2|8", return_structure=True)
            print(tree)
        """
        return super().print_tree(
            locator=locator,
            max_depth=max_depth,
            capture_image_folder=capture_image_folder,
            log_as_warnings=log_as_warnings,
            return_structure=return_structure,
        )

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
