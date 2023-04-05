from typing import List, Optional

from RPA.core.windows.locators import (
    Locator,
    LocatorMethods,
    MatchObject,
    WindowsElement,
)

from RPA.Windows import utils
from RPA.Windows.keywords import keyword
from RPA.Windows.keywords.context import with_timeout

if utils.IS_WINDOWS:
    import uiautomation as auto
    from uiautomation import Control


class LocatorKeywords(LocatorMethods):
    """Keywords for handling Windows locators."""

    # NOTE(cmin764): Timeout is automatically set to `None` in the upper calls by the
    #  `with_timeout` decorator, so we alter the behaviour (context timeout setting)
    #  on the first call only.

    @keyword
    @with_timeout
    def get_element(
        self,
        locator: Optional[Locator] = None,
        search_depth: int = 8,
        root_element: Optional[WindowsElement] = None,
        timeout: Optional[float] = None,
    ) -> WindowsElement:
        """Get a Control Windows element defined by the locator.

        The returned element can be used instead of a locator string for other keywords
        accepting the `locator` parameter.
        Keyword ``Get Attribute`` can be used to read element attribute values.

        If `locator` is `None`, then the returned element will be in this priority:

            1. `root_element` if provided.
            2. Anchor element if that has been previously set with ``Set Anchor``.
            3. Current active window if that has been set with ``Control Window``.
            4. Last resort is the "Desktop" element.

        :param locator: Locator as a string or as an element object.
        :param search_depth: How deep the element search will traverse. (default 8)
        :param root_element: Will be used as search root element object if provided.
        :param timeout: After how many seconds (float) to give up on search. (see
            keyword ``Set Global Timeout``)
        :returns: The identified `WindowsElement` object.

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Set Text Into Notepad Window
                Windows Run    Notepad
                Control Window      subname:Notepad
                ${element} =    Get Element    regex:"Text (E|e)ditor"
                Set Value    ${element}    note to myself

        **Example: Python**

        .. code-block:: python

            from RPA.Windows import Windows

            lib = Windows()
            lib.windows_run("calc.exe")
            one_btn = lib.get_element("Calculator > path:2|3|2|8|2")
            lib.close_window("Calculator")
        """
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
                # Every newly found matching element will inherit the offset set in the
                #  original initially found element.
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
        def get_first_child(ctrl: Control) -> Control:
            return ctrl.GetFirstChildControl()

        def get_next_sibling(ctrl: Control) -> Control:
            return ctrl.GetNextSiblingControl()

        def compare(ctrl: Control, _) -> bool:
            element = WindowsElement(ctrl, locator)
            return initial_element.is_sibling(element)

        # Take all the elements (no matter their level) starting from a parent as
        #  search tree root.
        parent_locator: Optional[str] = None
        locator_str: Optional[str] = WindowsElement.norm_locator(locator)
        if locator_str:
            branches = locator_str.rsplit(MatchObject.TREE_SEP, 1)
            if len(branches) == 2:
                # Full locator's parent becomes the root for the search.
                parent_locator = branches[0]
        top_element = self.get_element(
            # If the locator doesn't have a parent (null `parent_locator`) then simply
            #  rely on the resulting root resolution: root > anchor > window > Desktop.
            parent_locator,
            search_depth,
            root_element,
            timeout,
        )
        # Explore the entire subtree of elements starting from the resulted root above
        #  and keep only the ones matching the strategies in the last locator branch.
        tree_generator = auto.WalkTree(
            top_element.item,
            getFirstChild=get_first_child,
            getNextSibling=get_next_sibling,
            yieldCondition=compare,
            includeTop=not locator,
            maxDepth=search_depth,
        )
        elements = []
        for control, _ in tree_generator:
            element = WindowsElement(control, locator)
            # Every newly found matching element will inherit the offset set in the
            #  original initially found element.
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
        For more details on the rest of parameters, take a look at the ``Get Element``
        keyword.

        :param locator: Locator as a string or as an element object.
        :param search_depth: How deep the element search will traverse. (default 8)
        :param root_element: Will be used as search root element object if provided.
        :param timeout: After how many seconds (float) to give up on search. (see
            keyword ``Set Global Timeout``)
        :param siblings_only: Filter for elements on the same level as the initially
            found one. Turn it off for a global search. (`True` by default)
        :returns: A list of matching `WindowsElement` objects.

        **Example: Robot Framework**

        .. code-block:: robotframework

            *** Tasks ***
            Get Headers On Same Level
                Set Anchor      id:DataGrid
                @{elements} =   Get Elements    type:HeaderItem
                FOR    ${element}    IN    @{elements}
                    Log To Console    ${element.name}
                END

            Get All Calculator Buttons Matching Expression
                Windows Run    Calc
                Control Window    subname:Calc
                @{buttons} =    Get Elements    class:Button regex:.*o.*
                ...     siblings_only=${False}
                Log List    ${buttons}
                ${length} =     Get Length      ${buttons}
                Log To Console      Number of buttons: ${length}
        """
        initial_element = self.get_element(locator, search_depth, root_element, timeout)

        if siblings_only:
            return self._search_siblings(initial_element, locator=locator)

        return self._search_globally(
            initial_element,
            locator=locator,
            search_depth=search_depth,
            root_element=root_element,
            timeout=timeout,
        )
