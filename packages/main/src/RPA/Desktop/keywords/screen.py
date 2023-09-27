import base64
import os
from itertools import count
from io import BytesIO
from pathlib import Path
from typing import Optional, Union, List, Dict

import mss
from PIL import Image
from robot.api import logger as robot_logger
from robot.running.context import EXECUTION_CONTEXTS

from RPA.core.geometry import Point, Region
from RPA.core.locators import LocatorType
from RPA.Desktop import utils
from RPA.Desktop.keywords import LibraryContext, keyword
from RPA.Robocorp.utils import get_output_dir

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


def _monitor_to_region(monitor: Dict) -> Region:
    """Convert mss monitor to Region instance."""
    return Region.from_size(
        monitor["left"], monitor["top"], monitor["width"], monitor["height"]
    )


def displays() -> List[Region]:
    """Returns list of display regions, without combined virtual display."""
    with mss.mss() as sct:
        return [_monitor_to_region(monitor) for monitor in sct.monitors[1:]]


def grab(region: Optional[Region] = None) -> Image.Image:
    """Take a screenshot of either the full virtual display,
    or a cropped area of the given region.
    """

    with mss.mss() as sct:
        display = _monitor_to_region(sct.monitors[0])

        if region is not None:
            try:
                region = region.clamp(display)
                screenshot = sct.grab(region.as_tuple())
            except ValueError as err:
                raise ValueError("Screenshot region outside display bounds") from err
        else:
            # First monitor is combined virtual display of all monitors
            screenshot = sct.grab(display.as_tuple())

    return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")


def log_image(image: Image.Image, size=1024):
    """Embed image into Robot Framework log."""
    if EXECUTION_CONTEXTS.current is None:
        return

    image = image.copy()
    image.thumbnail((int(size), int(size)), Image.ANTIALIAS)

    buf = BytesIO()
    image.save(buf, format="PNG")
    content = base64.b64encode(buf.getvalue()).decode("utf-8")

    robot_logger.info(
        '<img alt="screenshot" class="rpaframework-desktop-screenshot" '
        f'src="data:image/png;base64,{content}" >',
        html=True,
    )


class ScreenKeywords(LibraryContext):
    """Keywords for reading screen information and content."""

    @keyword
    def take_screenshot(
        self,
        path: Optional[str] = None,
        locator: Optional[LocatorType] = None,
        embed: bool = True,
    ) -> str:
        """Take a screenshot of the whole screen, or an element
        identified by the given locator.

        :param path: Path to screenshot. The string ``{index}`` will be replaced with
            an index number to avoid overwriting previous screenshots.
        :param locator: Element to crop screenshot to
        :param embed: Embed screenshot into Robot Framework log
        """
        if locator is not None:
            element = self.ctx.wait_for_element(locator)
            if not isinstance(element, Region):
                raise ValueError("Locator must resolve to a region")
            image = grab(element)
        else:
            image = grab()

        if path is None:
            dirname = get_output_dir(default=Path.cwd())
            path = dirname / "desktop-screenshot-{index}.png"

        path: Path = _create_unique_path(path).with_suffix(".png")
        os.makedirs(path.parent, exist_ok=True)

        image.save(path)
        self.logger.info("Saved screenshot as '%s'", path)

        if embed:
            log_image(image)

        return str(path)

    @keyword
    def get_display_dimensions(self) -> Region:
        """Returns the dimensions of the current virtual display,
        which is the combined size of all physical monitors.
        """
        with mss.mss() as sct:
            return _monitor_to_region(sct.monitors[0])

    @keyword
    def highlight_elements(self, locator: LocatorType):
        """Draw an outline around all matching elements."""
        if not utils.is_windows():
            raise NotImplementedError("Not supported on non-Windows platforms")

        matches = self.ctx.find_elements(locator)

        for match in matches:
            if isinstance(match, Region):
                _draw_outline(match)
            elif isinstance(match, Point):
                # TODO: Draw a circle instead?
                region = Region(match.x - 5, match.y - 5, match.x + 5, match.y + 5)
                _draw_outline(region)
            else:
                raise TypeError(f"Unknown location type: {match}")

    @keyword
    def define_region(self, left: int, top: int, right: int, bottom: int) -> Region:
        """
        Return a new ``Region`` with the given dimensions.

        :param left: Left edge coordinate.
        :param top: Top edge coordinate.
        :param right: Right edge coordinate.
        :param bottom: Bottom edge coordinate.

        Usage examples:

        .. code-block:: robotframework

            ${region}=  Define Region  10  10  50  30

        .. code-block:: python

            region = desktop.define_region(10, 10, 50, 30)

        """
        return Region(left, top, right, bottom)

    @keyword
    def move_region(self, region: Region, left: int, top: int) -> Region:
        """
        Return a new ``Region`` with an offset from the given region.

        :param region: The region to move.
        :param left: Amount of pixels to move left/right.
        :param top: Amount of pixels to move up/down.

        Usage examples:

        .. code-block:: robotframework

            ${region}=          Find Element  ocr:"Net Assets"
            ${moved_region}=    Move Region  ${region}  500  0

        .. code-block:: python

            region = desktop.find_element('ocr:"Net Assets"')
            moved_region = desktop.move_region(region, 500, 0)

        """
        return region.move(left, top)

    @keyword
    def resize_region(
        self,
        region: Region,
        left: int = 0,
        top: int = 0,
        right: int = 0,
        bottom: int = 0,
    ) -> Region:
        """
        Return a resized new ``Region`` from a given region.

        Extends edges the given amount outward from the center,
        i.e. positive left values move the left edge to the left.

        :param region: The region to resize.
        :param left: Amount of pixels to resize left edge.
        :param top: Amount of pixels to resize top edge.
        :param right: Amount of pixels to resize right edge.
        :param bottom: Amount of pixels to resize bottom edge.

        Usage examples:

        .. code-block:: robotframework

            ${region}=          Find Element  ocr:"Net Assets"
            ${resized_region}=  Resize Region  ${region}  bottom=10

        .. code-block:: python

            region = desktop.find_element('ocr:"Net Assets"')
            resized_region = desktop.resize_region(region, bottom=10)
        """
        return region.resize(left, top, right, bottom)
