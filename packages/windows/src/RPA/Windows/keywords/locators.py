from typing import List, Optional

from RPA.core.windows.locators import (
    Locator,
    LocatorMethods,
    WindowsElement,
)

from RPA.Windows.keywords import keyword
from RPA.Windows.keywords.context import with_timeout


class LocatorKeywords(LocatorMethods):
    """Keywords for handling Windows locators"""

    @keyword
    @with_timeout
    def get_element(
        self,
        locator: Optional[Locator] = None,
        search_depth: int = 8,
        root_element: Optional[WindowsElement] = None,
        timeout: Optional[float] = None,  # pylint: disable=unused-argument
    ) -> WindowsElement:
        """Get Control element defined by the locator.

        Returned element can be used instead of a locator string for
        keywords accepting `locator`.

        Keyword ``Get Attribute`` can be used to read element attribute values.

        If `locator` is *None* then returned `element` will be in order of preference:

            1. anchor element if that has been set with `Set Anchor`
            2. current active window if that has been set with `Control Window`
            3. final option is the `Desktop`

        :param locator: locator as a string or as an element
        :param search_depth: how deep the element search will traverse (default 8)
        :param root_element: can be used to set search root element
        :param timeout: float value in seconds, see keyword
         ``Set Global Timeout``
        :return: WindowsElement object

        Example:

        .. code-block:: robotframework

            ${element}=    Get Element    name:'Text Editor*
            Set Value   ${element}  note to myself
        """
        # NOTE(cmiN): Explicitly set timeout to `None` in the upper call, so we alter
        #  the behaviour (context timeout setting) here only.
        return super().get_element(
            locator=locator,
            search_depth=search_depth,
            root_element=root_element,
            timeout=None,
        )

    @keyword
    @with_timeout
    def get_elements(
        self,
        locator: Optional[Locator] = None,
        search_depth: int = 8,
        root_element: Optional[WindowsElement] = None,
        timeout: Optional[float] = None,  # pylint: disable=unused-argument
    ) -> List[WindowsElement]:
        """Get list of elements matching locator.

        :param locator: locator as a string or as an element
        :param search_depth: how deep the element search will traverse (default 8)
        :param root_element: can be used to set search root element
        :param timeout: float value in seconds, see keyword
         ``Set Global Timeout``
        :return: list of WindowsElement objects

        Example:

        .. code-block:: robotframework

            Set Anchor    id:DataGrid
            ${elements}=    Get Elements    type:HeaderItem
            FOR    ${el}    IN    @{elements}
                Log To Console    ${el.Name}
            END
        """
        elements = []
        initial_window_element = window_element = self.get_element(
            locator, search_depth, root_element
        )
        elements.append(initial_window_element)
        while True:
            next_element = window_element.item.GetNextSiblingControl()
            if next_element:
                window_element = WindowsElement(next_element, locator)
                if initial_window_element.is_sibling(window_element):
                    elements.append(window_element)
            else:
                break
        return elements
