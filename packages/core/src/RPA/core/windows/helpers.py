from typing import Dict
import platform

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    import psutil


def get_process_list() -> Dict:
    """Get process list.

    Returns dictionary mapping process id to process name
    """
    return {proc.pid: proc.name() for proc in psutil.process_iter()}


def is_numeric(value):
    try:
        float(value)
    except ValueError:
        return False
    else:
        return float(value).is_integer()
