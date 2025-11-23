import base64
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

from RPA.core.vendor.deco import keyword as method
from RPA.core.windows.context import COMError, WindowsContext
from RPA.core.windows.helpers import IS_WINDOWS, get_process_list

# Define placeholder objects
auto = None
win32api = None
win32con = None
win32gui = None
win32process = None
win32ui = None

if IS_WINDOWS:
    import uiautomation as auto  # pylint: disable=import-error
    import win32api  # pylint: disable=import-error
    import win32con  # pylint: disable=import-error
    import win32gui  # pylint: disable=import-error
    import win32process  # pylint: disable=import-error
    import win32ui  # pylint: disable=import-error


class WindowMethods(WindowsContext):
    """Keywords for handling the Windows GUI windows"""

    @staticmethod
    def get_icon(
        filepath: Optional[str], icon_save_directory: Optional[str] = None
    ) -> Optional[str]:
        if not filepath:
            return None  # no file path to save the icon from

        # TODO: Get icons of different sizes.
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

    @staticmethod
    def get_fullpath(pid: int) -> str:
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        return win32process.GetModuleFileNameEx(handle, 0)

    def _get_window_rectangle(self, win, pid: int) -> Optional[List]:
        """Get bounding rectangle for a window.

        Args:
            win: Window control object
            pid: Process ID for logging
        Returns:
            Rectangle as [left, top, right, bottom] or None if error
        """
        try:
            rect = win.BoundingRectangle
            return (
                [rect.left, rect.top, rect.right, rect.bottom] if rect else [None] * 4
            )
        except (COMError, Exception) as err:  # pylint: disable=broad-except
            self.logger.debug(
                "Skipping window (PID: %s) due to COM error accessing BoundingRectangle: %s",
                pid,
                err,
            )
            return None

    def _get_window_name(
        self, pid: int, fullpath: Optional[str], process_list: Dict
    ) -> Optional[str]:
        """Get window name from process list or file path.

        Args:
            pid: Process ID
            fullpath: Full path to executable
            process_list: Dictionary mapping PID to process name
        Returns:
            Window name or None
        """
        name = process_list.get(pid)
        if not name and fullpath:
            name = Path(fullpath).name
        return name

    def _get_window_icon(
        self, fullpath: Optional[str], icon_save_directory: Optional[str], pid: int
    ) -> Optional[str]:
        """Get icon string for a window.

        Args:
            fullpath: Full path to executable
            icon_save_directory: Directory to save icon
            pid: Process ID for logging
        Returns:
            Base64 encoded icon string or None
        """
        try:
            return self.get_icon(fullpath, icon_save_directory)
        except Exception as err:  # pylint: disable=broad-except
            self.logger.debug("Failed to get icon for window (PID: %s): %s", pid, err)
            return None

    def _build_window_info(
        self,
        win,
        pid: int,
        name: Optional[str],
        fullpath: Optional[str],
        handle: int,
        icon_string: Optional[str],
        rectangle: List,
    ) -> Optional[Dict]:
        """Build window info dictionary.

        Args:
            win: Window control object
            pid: Process ID
            name: Window name
            fullpath: Full path to executable
            handle: Window handle
            icon_string: Base64 encoded icon string
            rectangle: Bounding rectangle
        Returns:
            Window info dictionary or None if error
        """
        try:
            return {
                "title": win.Name,
                "pid": pid,
                "name": name,
                "path": fullpath,
                "handle": handle,
                "icon": icon_string,
                "automation_id": win.AutomationId,
                "control_type": win.ControlTypeName,
                "class_name": win.ClassName,
                "rectangle": rectangle,
                "keyboard_focus": win.HasKeyboardFocus,
                "is_active": handle == auto.GetForegroundWindow(),
                "object": win,
            }
        except (COMError, Exception) as err:  # pylint: disable=broad-except
            self.logger.debug(
                "Skipping window (PID: %s) due to COM error accessing properties: %s",
                pid,
                err,
            )
            return None

    def _process_single_window(
        self, win, icons: bool, icon_save_directory: Optional[str], process_list: Dict
    ) -> Optional[Dict]:
        """Process a single window and return its info.

        Args:
            win: Window control object
            icons: Whether to include icons
            icon_save_directory: Directory to save icons
            process_list: Dictionary mapping PID to process name
        Returns:
            Window info dictionary or None if processing fails
        """
        try:
            pid = win.ProcessId
        except (COMError, Exception) as err:  # pylint: disable=broad-except
            self.logger.debug(
                "Skipping window due to COM error accessing ProcessId: %s", err
            )
            return None

        try:
            fullpath = None
            try:
                fullpath = self.get_fullpath(pid)
            except Exception as err:  # pylint: disable=broad-except
                self.logger.info("Open process error in `List Windows`: %s", err)

            try:
                handle = win.NativeWindowHandle
            except (COMError, Exception) as err:  # pylint: disable=broad-except
                self.logger.debug(
                    "Skipping window (PID: %s) due to COM error accessing NativeWindowHandle: %s",
                    pid,
                    err,
                )
                return None

            icon_string = None
            if icons:
                icon_string = self._get_window_icon(fullpath, icon_save_directory, pid)

            rectangle = self._get_window_rectangle(win, pid)
            if rectangle is None:
                return None

            name = self._get_window_name(pid, fullpath, process_list)
            info = self._build_window_info(
                win, pid, name, fullpath, handle, icon_string, rectangle
            )
            if info is None:
                return None

            if icons and not icon_string:
                self.logger.info(
                    "Icon for %s returned empty", info.get("title", "unknown")
                )
            return info
        except (COMError, Exception) as err:  # pylint: disable=broad-except
            self.logger.debug(
                "Skipping window (PID: %s) due to COM error: %s", pid, err
            )
            return None

    @method
    def list_windows(
        self,
        icons: bool = False,
        icon_save_directory: Optional[str] = None,
    ) -> List[Dict]:
        try:
            windows = auto.GetRootControl().GetChildren()
        except (COMError, Exception) as err:  # pylint: disable=broad-except
            # Handle COM threading errors (e.g., 0x8001010d) gracefully
            self.logger.warning(
                "Failed to get root control children in `List Windows`: %s", err
            )
            return []

        process_list = get_process_list() if self.ctx.list_processes else {}
        win_list = []
        try:
            for win in windows:
                info = self._process_single_window(
                    win, icons, icon_save_directory, process_list
                )
                if info:
                    win_list.append(info)
        except (COMError, Exception) as err:  # pylint: disable=broad-except
            # Catch COM errors that occur during iteration itself
            self.logger.warning(
                "Error during window iteration in `List Windows`: %s. Returning partial list.",
                err,
            )
        return win_list
