import platform
from typing import Dict, Optional

import psutil
from comtypes import COMError


def get_process_list() -> Dict:
    """Get process list.

    Returns dictionary mapping process id to process name
    """
    process_list = {}
    for proc in psutil.process_iter():
        process_list[proc.pid] = proc.name()
    return process_list


def is_numeric(value):
    try:
        float(value)
    except ValueError:
        return False
    else:
        return float(value).is_integer()


def is_windows():
    return platform.system() == "Windows"


def call_attribute_if_available(object_name, attribute_name):
    if hasattr(object_name, attribute_name):
        return getattr(object_name, attribute_name)()
    return None


def window_or_none(
    window, timeout: float = 5
) -> Optional["WindowsElement"]:  # noqa: F821
    if window and window.item:
        if hasattr(window.item, "Exists"):
            return window if window.item.Exists(maxSearchSeconds=timeout) else None

        try:
            window.item.BoundingRectangle
        except COMError:
            return None

        return window

    return None
