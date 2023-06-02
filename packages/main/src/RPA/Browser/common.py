import functools
import inspect
import logging
import os
import platform
from typing import Union


AUTO = "AUTO"
logger = logging.getLogger(__name__)


def get_headless_state(headless: Union[bool, str] = AUTO) -> bool:
    """Parse argument for headless mode."""
    if str(headless).strip().lower() == AUTO.lower():
        # If in Linux and with no valid display, we can assume we are in a
        #  container which doesn't support UI.
        headless = platform.system() == "Linux" and not (
            os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        )
        if headless:
            logger.info("Auto-detected headless environment!")
    headless = headless or int(os.getenv("RPA_HEADLESS_MODE", "0"))
    return bool(headless)


def auto_headless(super_func):
    """Automatically handles the headless switch in a keyword."""
    signature = inspect.signature(super_func)
    default_headless = signature.parameters["headless"].default

    @functools.wraps(super_func)
    def wrapper(*args, **kwargs):
        headless = kwargs.pop("headless", default_headless)
        headless = get_headless_state(headless)
        return super_func(*args, headless=headless, **kwargs)

    return wrapper
