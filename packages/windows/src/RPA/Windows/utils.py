from typing import Dict

import platform
import psutil


IS_WINDOWS = platform.system() == "Windows"


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


def call_attribute_if_available(object_name, attribute_name):
    if hasattr(object_name, attribute_name):
        return getattr(object_name, attribute_name)()
    return None
