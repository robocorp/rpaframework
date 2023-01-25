from contextlib import contextmanager
from typing import Any, List, Optional, Tuple, Union

from RPA.core.types import is_list_like  # type: ignore

from RPA.Assistant.types import Element, Options


def to_options(
    opts: Options, default: Optional[str] = None
) -> Tuple[List[str], Optional[str]]:
    """Convert keyword argument for multiple options into
    a list of strings.

    Also handles default option validation.
    """
    if isinstance(opts, str):
        opts = [opt.strip() for opt in opts.split(",")]
    elif is_list_like(opts):
        opts = [str(opt) for opt in opts]
    else:
        raise ValueError(f"Unsupported options type: {opts}")

    if not opts:
        return [], None

    if default is None:
        default = opts[0]

    if default not in opts:
        raise ValueError(f"Default '{default}' is not in available options")

    return opts, default


def optional_str(val: Any) -> Optional[str]:
    """Convert value to string, but keep NoneType"""
    return str(val) if val is not None else val


def optional_int(val: Any) -> Optional[int]:
    """Convert value to int, but keep NoneType"""
    return int(val) if val is not None else val


def int_or_auto(val: Any) -> Union[int, str]:
    """Convert value to int or 'AUTO' literal"""
    if isinstance(val, int):
        return val

    try:
        return int(val)
    except ValueError:
        pass

    height = str(val).strip().upper()
    if height == "AUTO":
        return height

    raise ValueError("Value not integer or AUTO")


def is_input(element: Element) -> bool:
    """Check if an element is an input"""
    return element["type"].startswith("input-")


def is_submit(element: Element) -> bool:
    """Check if an element is a submit button."""
    return element["type"] == "submit"


@contextmanager
def button_lock(event, lock_object, flet_update):
    """Acquire lock, early abort if not available, disable button and acquire lock if available."""
    # check if lock is open
    lock_status = lock_object.acquire(blocking=False)
    try:
        # early abort if unable to lock
        if not lock_status:
            return
        event.control.disabled = True
        flet_update()
        yield lock_status
    finally:
        lock_object.release()
        event.control.disabled = False
        flet_update()
