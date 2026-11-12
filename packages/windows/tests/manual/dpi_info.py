"""Print the DPI facts that explain "the click landed somewhere else" reports.

Standard library only, so it runs with any Python on Windows::

    python dpi_info.py              # system DPI, monitors, this process' awareness
    python dpi_info.py Calculator   # plus the DPI awareness of windows whose title contains "Calculator"

Run it from a console on the desktop you automate, not from an SSH session:
a remote shell lives in a separate session with its own virtual display.

An application that is *unaware* or *system-aware* on a display scaled above
100 % is bitmap-stretched by Windows, so the rectangle it reports through UI
Automation can differ from the pixels drawn on screen; that is where offsets
and clicks drift. Compare the "window" lines with the monitor scale.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

user32 = ctypes.windll.user32
shcore = ctypes.windll.shcore

# DPI_AWARENESS_CONTEXT values are pointer-sized pseudo handles, so every call
# that takes or returns one needs explicit argtypes; a bare Python int would be
# passed as a 32-bit value and the call would silently fail.
user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
user32.AreDpiAwarenessContextsEqual.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.AreDpiAwarenessContextsEqual.restype = ctypes.c_bool
user32.GetWindowDpiAwarenessContext.argtypes = [wintypes.HWND]
user32.GetWindowDpiAwarenessContext.restype = ctypes.c_void_p
user32.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
user32.GetDpiForWindow.argtypes = [wintypes.HWND]
user32.GetDpiForWindow.restype = wintypes.UINT
user32.GetDpiForSystem.restype = wintypes.UINT
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

CONTEXTS = {
    -1: "unaware",
    -2: "system aware",
    -3: "per-monitor aware",
    -4: "per-monitor aware v2",
    -5: "unaware (GDI scaled)",
}
MDT_EFFECTIVE_DPI = 0


def context_name(ctx: int | None) -> str:
    """Translate a DPI_AWARENESS_CONTEXT handle into words."""
    if not ctx:
        return "unknown (no context)"
    for known, name in CONTEXTS.items():
        if user32.AreDpiAwarenessContextsEqual(ctx, ctypes.c_void_p(known).value):
            return name
    return f"unknown ({ctx:#x})"


def monitors() -> list[tuple[wintypes.RECT, int]]:
    found: list[tuple[wintypes.RECT, int]] = []
    proc = ctypes.WINFUNCTYPE(
        ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
    )

    def callback(hmon, _hdc, rect_ptr, _lparam):
        dpi_x, dpi_y = wintypes.UINT(), wintypes.UINT()
        shcore.GetDpiForMonitor(hmon, MDT_EFFECTIVE_DPI, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
        found.append((rect_ptr.contents, dpi_x.value))
        return 1

    user32.EnumDisplayMonitors(None, None, proc(callback), 0)
    return found


def windows_titled(fragment: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    proc = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if fragment.lower() in buf.value.lower():
                    hits.append((hwnd, buf.value))
        return 1

    user32.EnumWindows(proc(callback), 0)
    return hits


def main(argv: list[str]) -> int:
    # Make this process per-monitor aware so the numbers below are real pixels.
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4).value)
    system_dpi = user32.GetDpiForSystem()
    print(f"system DPI: {system_dpi} ({system_dpi * 100 // 96} %)")
    for i, (rect, dpi) in enumerate(monitors(), start=1):
        print(
            f"monitor {i}: ({rect.left},{rect.top})-({rect.right},{rect.bottom}) "
            f"{rect.right - rect.left}x{rect.bottom - rect.top} px, DPI {dpi} ({dpi * 100 // 96} %)"
        )
    print(f"this process: {context_name(user32.GetThreadDpiAwarenessContext())}")

    for fragment in argv[1:]:
        hits = windows_titled(fragment)
        if not hits:
            print(f'no visible window with "{fragment}" in its title')
        for hwnd, title in hits:
            ctx = user32.GetWindowDpiAwarenessContext(hwnd)
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            print(
                f'window "{title}": {context_name(ctx)}, DPI {user32.GetDpiForWindow(hwnd)}, '
                f"rect ({rect.left},{rect.top})-({rect.right},{rect.bottom})"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
