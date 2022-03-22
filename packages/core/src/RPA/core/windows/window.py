import base64
from pathlib import Path
from typing import Dict, List, Optional
from io import BytesIO

from PIL import Image

from RPA.core.windows.context import WindowsContext
from RPA.core.windows.helpers import IS_WINDOWS, get_process_list

if IS_WINDOWS:
    import win32api
    import win32con
    import win32gui
    import win32process
    import win32ui
    import uiautomation as auto


class WindowMethods(WindowsContext):
    """Keywords for handling the Windows GUI windows"""

    @staticmethod
    def get_icon(
        filepath: str, icon_save_directory: Optional[str] = None
    ) -> Optional[str]:
        if not filepath:
            return None  # no file path to save the icon into

        # TODO. Get different size icons
        small, large = win32gui.ExtractIconEx(filepath, 0, 10)
        if len(large) <= 0:
            return None  # no icon to extract

        if len(small) > 0:
            win32gui.DestroyIcon(small[0])  # get rid of the small one

        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
        hdc = hdc.CreateCompatibleDC()
        hdc.SelectObject(hbmp)
        hdc.DrawIcon((0, 0), large[0])

        executable_path = Path(filepath)
        icon_path = icon_name = f"icon_{executable_path.name}.bmp"
        if icon_save_directory:
            icon_path = str((Path(icon_save_directory) / icon_name).resolve())
        hbmp.SaveBitmapFile(hdc, icon_path)
        with Image.open(icon_path) as img:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            image_string = base64.b64encode(buffered.getvalue()).decode()
        if not icon_save_directory:
            Path(icon_path).unlink()
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
                handle = win32api.OpenProcess(
                    win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid
                )
                fullpath = win32process.GetModuleFileNameEx(handle, 0)
            except Exception as err:  # pylint: disable=broad-except
                self.logger.info("Open process error in `List Windows`: %s", str(err))
            icon_string = (
                self.get_icon(fullpath, icon_save_directory) if icons else None
            )
            info = {
                "title": win.Name,
                "pid": pid,
                "name": process_list[pid] if pid in process_list else None,
                "path": fullpath,
                "handle": win.NativeWindowHandle,
                "icon": icon_string,
            }
            if icons and not icon_string:
                self.logger.info("Icon for %s returned empty", win.Name)
            win_list.append(info)
        return win_list