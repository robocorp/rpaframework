"""Probe for issue #1379: does ``offset:x,y`` click where it should?

Run on a Windows machine with ``rpaframework-windows`` installed::

    uv run python tests/manual/offset_click_probe.py

The script opens Calculator and, for a series of offsets, measures where the
cursor really lands after ``Click`` compared to the element centre plus the
offset. It then checks that an offset reaching the neighbouring button ("5"
to "6") really presses that button, both with a string locator and with an
element returned by ``Get Element``. Nothing is mocked; failures print the
raw rectangles so they can be pasted into the issue.
"""

from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass
from importlib.metadata import version

import uiautomation as auto

from RPA.Windows import Windows

OFFSETS = [(0, 0), (40, 0), (-40, 0), (0, 25), (120, 0), (-120, -30)]
RESULTS = "id:CalculatorResults"


@dataclass
class Check:
    name: str
    expected: object
    actual: object

    @property
    def ok(self) -> bool:
        return self.expected == self.actual


def environment() -> None:
    print("rpaframework-windows", version("rpaframework-windows"))
    print("uiautomation", version("uiautomation"))
    try:
        awareness = ctypes.c_int()
        ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
        print("process DPI awareness", awareness.value, "(0=unaware 1=system 2=per-monitor)")
    except (AttributeError, OSError) as err:
        print("DPI awareness unavailable:", err)
    print("monitors", auto.GetMonitorsRect())
    print("screen", auto.GetScreenSize())


def rect_of(element) -> tuple[int, int, int, int, int, int]:
    rect = element.item.BoundingRectangle
    return rect.left, rect.top, rect.right, rect.bottom, rect.xcenter(), rect.ycenter()


def clear(lib: Windows) -> None:
    """Reset the display; Escape works whether the button reads C or CE."""
    lib.send_keys(keys="{Esc}")


def display(lib: Windows) -> str:
    return lib.get_attribute(RESULTS, "Name").replace("Display is ", "").strip()


def main() -> int:
    environment()
    lib = Windows()
    lib.set_wait_time(0.3)
    lib.set_mouse_movement(False)
    checks: list[Check] = []

    lib.windows_run("calc.exe", wait_time=2.0)
    lib.control_window("name:Calculator")
    try:
        # 1. Geometry: cursor position after click == centre + offset.
        for dx, dy in OFFSETS:
            clear(lib)
            elem = lib.get_element(f"id:num5Button offset:{dx},{dy}")
            left, top, right, bottom, cx, cy = rect_of(elem)
            lib.click(elem)
            landed = auto.GetCursorPos()
            checks.append(Check(f"cursor after offset:{dx},{dy}", (cx + dx, cy + dy), landed))
            print(
                f"offset {dx:>5},{dy:<4} rect=({left},{top},{right},{bottom}) "
                f"centre=({cx},{cy}) expected={(cx + dx, cy + dy)} landed={landed}"
            )

        # 2. Semantics: an offset spanning to the "6" button must press "6".
        five = lib.get_element("id:num5Button")
        six = lib.get_element("id:num6Button")
        dx = six.item.BoundingRectangle.xcenter() - five.item.BoundingRectangle.xcenter()
        dy = six.item.BoundingRectangle.ycenter() - five.item.BoundingRectangle.ycenter()
        print(f"distance from '5' centre to '6' centre: {dx},{dy}")

        clear(lib)
        lib.click(f"id:num5Button offset:{dx},{dy}")
        checks.append(Check("string locator with offset presses '6'", "6", display(lib)))

        clear(lib)
        elem = lib.get_element(f"id:num5Button offset:{dx},{dy}")
        lib.click(elem)
        checks.append(Check("Get Element + Click keeps offset, presses '6'", "6", display(lib)))

        clear(lib)
        lib.click("id:num5Button")
        checks.append(Check("no offset presses '5'", "5", display(lib)))
    finally:
        lib.close_current_window()

    print()
    print(f"{'check':<50} {'expected':<16} {'actual':<16} result")
    for check in checks:
        print(
            f"{check.name:<50} {str(check.expected):<16} {str(check.actual):<16} "
            f"{'ok' if check.ok else 'FAIL'}"
        )
    failed = sum(not check.ok for check in checks)
    print(f"\n{len(checks) - failed} ok, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
