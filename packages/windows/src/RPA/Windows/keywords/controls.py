from RPA.Windows.keywords import keyword, LibraryContext
from RPA.Windows import utils

if utils.is_windows():
    import uiautomation as auto
# from typing import List, Dict, Optional


class ControlKeywords(LibraryContext):
    """Keywords for handling Control objects"""

    @keyword
    def get_control(self, control_type, search_depth=3, **kwargs):
        result = None
        if control_type.lower() == "control":
            result = auto.Control(searchDepth=search_depth, **kwargs)
        else:
            control_element = getattr(self.ctx.window, control_type)
            result = control_element(searchDepth=search_depth, **kwargs)
        # self.logger.info("Get control result: %s" % result)
        return result

    def debug_control(self, target=None, max_depth=2, encoding="utf-8", level="info"):
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

    def output_control(self, control):
        # self.logger.info(dir(control))
        self.ctx.logger.info(control.AriaProperties)
        self.ctx.logger.info(control.AutomationId)
