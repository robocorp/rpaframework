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


def get_win_version() -> str:
    """Windows only utility which returns the current Windows major version."""
    # Windows terminal `ver` command is bugged, until that's fixed, check by build
    #  number. (the same applies for `platform.version()`)
    version_parts = platform.version().split(".")
    major = version_parts[0]
    if major == "10" and int(version_parts[2]) >= 22000:
        major = "11"

    return major
