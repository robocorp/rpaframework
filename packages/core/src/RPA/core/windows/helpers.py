import platform
from typing import Dict

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    import psutil


def get_process_list() -> Dict:
    """Get process list.

    Returns dictionary mapping process id to process name
    """
    return {proc.pid: proc.name() for proc in psutil.process_iter()}
