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
            logger.info("Autodetected headless environment!")
    headless = headless or int(os.getenv("RPA_HEADLESS_MODE", "0"))
    return bool(headless)
