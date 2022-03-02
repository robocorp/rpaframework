from typing import List, Dict, Optional
from pathlib import Path
from io import BytesIO
import base64
import logging

from PIL import Image

from .helpers import IS_WINDOWS, get_process_list


if IS_WINDOWS:
    import win32api
    import win32process
    import win32con
    import win32gui
    import win32ui
    import uiautomation as auto


LOGGER = logging.getLogger(__file__)


class Window:
    """Keywords for handling the Windows GUI windows"""

    def __init__(self):
        self.logger = logging.getLogger(__file__)

    @classmethod
    def get_icon(cls, filepath: str, icon_save_directory: Optional[str] = None) -> str:
        image_string = None
        executable_path = Path(filepath)
        ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)

        # TODO. Get different size icons
        small, large = win32gui.ExtractIconEx(filepath, 0, 10)
        if len(small) > 0:
            win32gui.DestroyIcon(small[0])

        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()

        hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
        hdc = hdc.CreateCompatibleDC()

        hdc.SelectObject(hbmp)

        if len(large) > 0:
            hdc.DrawIcon((0, 0), large[0])
            result_image_file = f"icon_{executable_path.name}.bmp"
            if icon_save_directory:
                result_image_file = Path(icon_save_directory) / result_image_file
                result_image_file = str(result_image_file.resolve())
            hbmp.SaveBitmapFile(hdc, result_image_file)
            with Image.open(result_image_file) as img:
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                image_string = base64.b64encode(buffered.getvalue())
            if not icon_save_directory:
                Path(result_image_file).unlink()
        return image_string

    def list_windows(
        self, icons: bool = False, icon_save_directory: Optional[str] = None
    ) -> List[Dict]:
        windows = auto.GetRootControl().GetChildren()
        process_list = get_process_list()
        win_list = []
        for win in windows:
            pid = win.ProcessId
            fullpath = None
            try:
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, pid)
                fullpath = win32process.GetModuleFileNameEx(handle, 0)
            except Exception as err:  # pylint: disable=broad-except
                self.logger.info("Open process error in `List Windows`: %s", str(err))

            info = {
                "title": win.Name,
                "pid": pid,
                "name": process_list[pid] if pid in process_list else None,
                "path": fullpath,
                "handle": win.NativeWindowHandle,
                "icon": self.get_icon(fullpath, icon_save_directory) if icons else None,
            }
            win_list.append(info)
        return win_list
