import os
from typing import Dict, Union
import psutil


IS_WINDOWS = os.name == "nt"


def get_process_list() -> Dict:
    """Get process list.

    Returns dictionary mapping process id to process name
    """
    process_list = {}
    for proc in psutil.process_iter():
        process_list[proc.pid] = proc.name()
    return process_list


def is_numeric(value: Union[int, float]) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    else:
        return float(value).is_integer()
