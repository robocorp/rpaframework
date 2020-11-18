import base64
import os
from itertools import count
from io import BytesIO
from pathlib import Path
from typing import Optional, Union, List, Dict

import mss
from mss.screenshot import ScreenShot
from PIL import Image
from robot.api import logger as robot_logger
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

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


def _create_unique_path(template: Union[Path, str]) -> Path:
    """Creates a unique path from template with `{index}` placeholder."""
    template = str(template)

    if "{index}" not in template:
        return Path(template)

    for index in count(1):
        path = Path(str(template).format(index=index))
        if not path.is_file():
            return path

    raise RuntimeError("Failed to generate unique path")  # Should not reach here


def monitor_to_region(monitor: Dict) -> Region:
    """Convert mss monitor to Region instance."""
    return Region.from_size(
        monitor["left"], monitor["top"], monitor["width"], monitor["height"]
    )


def screenshot_to_image(screenshot: ScreenShot) -> Image:
    """Convert mss screenshot to PIL.Image instance."""
    return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")


def all_displays() -> List[Region]:
    """Returns list of display regions, without combined virtual display."""
    with mss.mss() as sct:
        return [monitor_to_region(monitor) for monitor in sct.monitors[1:]]


def take_screenshot(region: Optional[Region]) -> ScreenShot:
    """Take a screenshot of either the full virtual display,
    or a cropped region defined by the given locator.
    """
    with mss.mss() as sct:
        if region is not None:
            return sct.grab(region.as_tuple())
        else:
            # First monitor is combined virtual display of all monitors
            return sct.grab(sct.monitors[0])


class ScreenKeywords(LibraryContext):
    """Keywords for reading screen information and content."""

    @keyword
    def take_screenshot(
        self,
        path: Optional[str] = None,
        locator: Optional[str] = None,
        embed: bool = True,
    ) -> Path:
        """Take a screenshot of the whole screen, or an element
        identified by the given locator.

        :param path: Path to screenshot. The string ``{index}`` will be replaced with
            an index number to avoid overwriting previous screenshots.
        :param locator: Element to crop screenshot to
        :param embed: Embed screenshot into Robot Framework log
        """
        element = None
        if locator is not None:
            element = self.ctx.find_element(locator)
            if not isinstance(element, Region):
                raise ValueError(
                    "Take Screenshot only supports locators "
                    "that resolve to regions, not points."
                )

        if path is None:
            try:
                dirname = Path(BuiltIn().get_variable_value("${OUTPUT_DIR}"))
            except RobotNotRunningError:
                dirname = Path.cwd()
            path = dirname / "desktop-screenshot-{index}.png"

        path = _create_unique_path(path).with_suffix(".png")
        os.makedirs(path.parent, exist_ok=True)

        image = take_screenshot(element)
        mss.tools.to_png(image.rgb, image.size, output=path)
        self.logger.info("Saved screenshot as '%s'", path)

        if embed:
            self._embed_screenshot(image)

        return str(path)

    @keyword
    def get_display_dimensions(self) -> Region:
        """Returns the dimensions of the current virtual display,
        which is the combined size of all physical monitors.
        """
        with mss.mss() as sct:
            return monitor_to_region(sct.monitors[0])

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

    def _embed_screenshot(self, screenshot: ScreenShot, size=(1024, 1024)):
        """Embed screenshot as inline image in Robot Framework log."""
        image = screenshot_to_image(screenshot)
        image.thumbnail(size, Image.ANTIALIAS)

        buf = BytesIO()
        image.save(buf, format="PNG")
        content = base64.b64encode(buf.getvalue()).decode("utf-8")

        robot_logger.info(
            '<img alt="screenshot" class="rpaframework-desktop-screenshot" '
            f'src="data:image/png;base64,{content}" >',
            html=True,
        )
