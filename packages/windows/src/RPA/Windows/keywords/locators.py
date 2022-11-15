from typing import List, Optional

from RPA.core.windows.locators import (
    Locator,
    LocatorMethods,
    WindowsElement,
)

from RPA.Windows import utils
from RPA.Windows.keywords import keyword
from RPA.Windows.keywords.context import with_timeout

if utils.IS_WINDOWS:
    import uiautomation as auto
    from uiautomation import TreeNode


class LocatorKeywords(LocatorMethods):
    """Keywords for handling Windows locators"""

    @keyword
    @with_timeout
    def get_element(
        self,
        locator: Optional[Locator] = None,
        search_depth: int = 8,
        root_element: Optional[WindowsElement] = None,
        timeout: Optional[float] = None,
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

            ${element} =    Get Element    name:"RichEdit Control"
            Set Value    ${element}    note to myself
        """
        # NOTE(cmiN): Timeout is automatically set to `None` in the upper call by the
        #  `with_timeout` decorator, so we alter the behaviour (context timeout
        #  setting) at this level only.
        return super().get_element(
            locator=locator,
            search_depth=search_depth,
            root_element=root_element,
            timeout=timeout,
        )

    @classmethod
    def _search_siblings(
        cls, initial_element: WindowsElement, *, locator: Optional[Locator]
    ) -> List[WindowsElement]:
        elements = [initial_element]

        element = initial_element
        while True:
            next_control = element.item.GetNextSiblingControl()
            if not next_control:
                break

            element = WindowsElement(next_control, locator)
            if initial_element.is_sibling(element):
                element.item.robocorp_click_offset = (
                    initial_element.item.robocorp_click_offset
                )
                elements.append(element)

        return elements

    def _search_globally(
        self,
        initial_element: WindowsElement,
        *,
        locator: Optional[Locator],
        search_depth: int,
        root_element: Optional[WindowsElement],
        timeout: Optional[float],
    ) -> List[WindowsElement]:
        def get_first_child(ctrl: TreeNode) -> TreeNode:
            return ctrl.GetFirstChildControl()

        def get_next_sibling(ctrl: TreeNode) -> TreeNode:
            return ctrl.GetNextSiblingControl()

        def compare(ctrl: TreeNode, _) -> bool:
            element = WindowsElement(ctrl, locator)
            return initial_element.is_sibling(element)

        top_element = root_element or self.get_element(
            None, search_depth, root_element, timeout
        )
        tree_generator = auto.WalkTree(
            top_element.item,
            getFirstChild=get_first_child,
            getNextSibling=get_next_sibling,
            yieldCondition=compare,
            includeTop=True,
            maxDepth=search_depth,
        )
        elements = []
        for control, _ in tree_generator:
            element = WindowsElement(control, locator)
            element.item.robocorp_click_offset = (
                initial_element.item.robocorp_click_offset
            )
            elements.append(element)
        return elements

    @keyword
    @with_timeout
    def get_elements(
        self,
        locator: Optional[Locator] = None,
        search_depth: int = 8,
        root_element: Optional[WindowsElement] = None,
        timeout: Optional[float] = None,
        siblings_only: bool = True,
    ) -> List[WindowsElement]:
        """Get a list of elements matching the locator.

        By default, only the siblings (similar elements on the same level) are taken
        into account. In order to search globally, turn `siblings_only` off, but be
        aware that this will take more time to process.

        :param locator: Locator as a string or as an element object.
        :param search_depth: How deep the element search will traverse. (default 8)
        :param root_element: Will be used as search root element object if provided.
        :param timeout: After how many seconds (float) to give up on search. (see
            keyword ``Set Global Timeout``)
        :param siblings_only: Filter for elements on the same level as the initially
            found one. Turn it off for a global search. (`True` by default)
        :returns: A list of `WindowsElement` objects.

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Get Headers On Same Level
                Set Anchor      id:DataGrid
                @{elements} =   Get Elements    type:HeaderItem
                FOR    ${element}    IN    @{elements}
                    Log To Console    ${element.name}
                END
        """
        initial_element = self.get_element(
            locator, search_depth, root_element, timeout=timeout
        )

        if siblings_only:
            return self._search_siblings(initial_element, locator=locator)

        return self._search_globally(
            initial_element,
            locator=locator,
            search_depth=search_depth,
            root_element=root_element,
            timeout=timeout,
        )
