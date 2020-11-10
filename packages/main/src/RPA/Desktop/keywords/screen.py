import os
from pathlib import Path
from typing import Optional, List, Dict

import mss
from PIL import Image

from RPA.core.geometry import Point, Region
from RPA.Desktop import utils
from RPA.Desktop.keywords import LibraryContext, keyword

if utils.is_windows():
    import ctypes
    from pywinauto import win32structures
    from pywinauto import win32defines
    from pywinauto import win32functions


def _draw_outline(region: Region):
    """Win32-based outline drawing for region."""
    brush_struct = win32structures.LOGBRUSH()
    brush_struct.lbStyle = win32defines.BS_NULL
    brush_struct.lbHatch = win32defines.HS_DIAGCROSS

    brush = win32functions.CreateBrushIndirect(ctypes.byref(brush_struct))
    pen = win32functions.CreatePen(win32defines.PS_SOLID, 2, 0x0000FF)
    dc = win32functions.CreateDC("DISPLAY", None, None, None)

    try:
        win32functions.SelectObject(dc, brush)
        win32functions.SelectObject(dc, pen)
        win32functions.Rectangle(
            dc, region.left, region.top, region.right, region.bottom
        )
    finally:
        win32functions.DeleteObject(brush)
        win32functions.DeleteObject(pen)
        win32functions.DeleteDC(dc)


def get_displays() -> List[Dict[str, int]]:
    """ Returns list of mss displays, without the 1st virtual display"""
    with mss.mss() as sct:
        monitors = sct.monitors
        del monitors[0]
        return monitors


def region_from_mss_monitor(disp) -> Region:
    return Region.from_size(disp["left"], disp["top"], disp["width"], disp["height"])


class ScreenKeywords(LibraryContext):
    """Keywords for reading screen information and content."""

    @keyword
    def take_screenshot(
        self,
        path: Optional[str] = None,
        locator: Optional[str] = None,
    ) -> None:
        """Take a screenshot of the whole screen, or an element
        identified by the given locator.

        :param path: Name of screenshot
        :param locator:  Element to crop screenshot to
        """
        with mss.mss() as sct:
            if locator is not None:
                # TODO: ensure we always get a region, not a point.
                # sct.grab requires a 4-tuple as argument
                match = self.ctx.find_element(locator)
                if not isinstance(match, Region):
                    raise ValueError(
                        "Take Screenshot only supports locators"
                        "that resolve to regions, not points"
                    )
                image = sct.grab(match.as_tuple())
            else:
                # First monitor is combined virtual display of all monitors
                image = sct.grab(sct.monitors[0])

        if path is not None:
            path = Path(path).with_suffix(".png")

            os.makedirs(path.parent, exist_ok=True)
            mss.tools.to_png(image.rgb, image.size, output=path)

            self.logger.info("Saved screenshot as '%s'", path)

        # Convert raw mss screenshot to Pillow Image. Might be a bit slow.
        return Image.frombytes("RGB", image.size, image.bgra, "raw", "BGRX")

    @keyword
    def get_display_dimensions(self) -> Region:
        """Returns the dimensions of the current virtual display,
        which is the combined size of all physical monitors.
        """
        with mss.mss() as sct:
            disp = sct.monitors[0]
            return region_from_mss_monitor(disp)

    @keyword
    def highlight_elements(self, locator: str):
        """Draw an outline around all matching elements."""
        if not utils.is_windows():
            raise NotImplementedError("Not supported on non-Windows platforms")

        matches = self.ctx.find(locator)

        for match in matches:
            if isinstance(match, Region):
                _draw_outline(match)
            elif isinstance(match, Point):
                region = Region(match.x - 5, match.y - 5, match.x + 5, match.y + 5)
                _draw_outline(region)
            else:
                raise TypeError(f"Unknown location type: {match}")
