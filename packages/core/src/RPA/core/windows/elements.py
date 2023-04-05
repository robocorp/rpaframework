from pathlib import Path
from typing import Dict, List, Optional

from RPA.core.vendor.deco import keyword as method
from RPA.core.windows.context import WindowsContext
from RPA.core.windows.helpers import IS_WINDOWS
from RPA.core.windows.locators import Locator, MatchObject, WindowsElement

if IS_WINDOWS:
    import uiautomation as auto
    from uiautomation.uiautomation import Control


StructureType = Dict[int, List[WindowsElement]]


class ElementMethods(WindowsContext):
    """Keywords for listing Windows GUI elements."""

    @staticmethod
    def _add_child_to_tree(
        control: "Control",
        structure: StructureType,
        *,
        locator: Optional[str],
        depth: int,
        path: str,
    ):
        # Adds current control child as element in the flattened tree structure.
        if locator and path:
            control_locator = f"{locator} > path:{path}"
        elif path:
            control_locator = f"path:{path}"
        else:
            control_locator = locator
        control.robocorp_click_offset = None
        element = WindowsElement(control, control_locator)
        structure.setdefault(depth, []).append(element)

    @method
    def print_tree(
        self,
        locator: Optional[Locator] = None,
        max_depth: int = 8,
        capture_image_folder: Optional[str] = None,
        log_as_warnings: Optional[bool] = False,
        return_structure: bool = False,
    ) -> Optional[StructureType]:
        # Cache how many brothers are in total given a child. (to know child position)
        brothers_count: Dict[int, int] = {}
        # Current path in the tree as children positions. (to compute the path locator)
        children_stack: List[int] = [-1] * (max_depth + 1)
        # Flattened tree of elements by depth level (to return the object if wanted).
        structure: StructureType = {}

        def get_children(ctrl: Control) -> List[Control]:
            children = ctrl.GetChildren()
            children_count = len(children)
            for child in children:
                brothers_count[hash(child)] = children_count
            return children

        target_elem = self.ctx.get_element(locator)
        locator: Optional[str] = WindowsElement.norm_locator(target_elem)
        root_ctrl = target_elem.item
        brothers_count[hash(root_ctrl)] = 1  # the root is always singular here

        image_idx = 1
        image_folder: Optional[Path] = None
        if capture_image_folder:
            image_folder = Path(capture_image_folder).expanduser().resolve()
            image_folder.mkdir(parents=True, exist_ok=True)

        control_log = {
            None: self.logger.debug,
            False: self.logger.info,
            True: self.logger.warning,
        }[log_as_warnings]

        for control, depth, children_remaining in auto.WalkTree(
            root_ctrl,
            getChildren=get_children,
            includeTop=True,
            maxDepth=max_depth,
        ):
            control_str = str(control)

            if image_folder:
                element = WindowsElement(control, locator)
                capture_filename = f"{control.ControlType}_{image_idx}.png"
                image_path = image_folder / capture_filename
                try:
                    self.ctx.screenshot(element, image_path)
                except Exception as exc:  # pylint: disable=broad-except
                    self.logger.warning(
                        "Couldn't capture into %r due to: %s", image_path, exc
                    )
                else:
                    control_str += f"    Image: {capture_filename}"
                image_idx += 1

            space = " " * depth * 4
            child_pos = brothers_count[hash(control)] - children_remaining
            children_stack[depth] = child_pos
            path = MatchObject.PATH_SEP.join(
                str(pos) for pos in children_stack[1 : depth + 1]
            )
            control_log(f"{space}{depth}-{child_pos}. {control_str}    Path: {path}")

            if return_structure:
                self._add_child_to_tree(
                    control,
                    structure,
                    locator=locator,
                    depth=depth,
                    path=path,
                )

        return structure if return_structure else None
