import os
import platform
from pathlib import Path
from typing import Dict, List


def robocorp_home():
    """Get the absolute path to the user's Robocorp home folder.
    Prefers environment variable ROBOCORP_HOME, if defined.
    """
    env = os.getenv("ROBOCORP_HOME", "")

    if env.strip():
        path = Path(env)
    elif platform.system() == "Windows":
        path = Path.home() / "AppData" / "Local" / "robocorp"
    else:
        path = Path.home() / ".robocorp"

    return path.resolve()


def browser_preferences() -> Dict[str, List[str]]:
    """Get lists of browser preferences for OS.
    Prefers environment variable ROBOCORP_BROWSERS, if defined.
    """
    browsers = os.getenv("ROBOCORP_BROWSERS", "")
    if browsers:
        preferences = {
            "default": [
                browser.strip()
                for browser in os.getenv("ROBOCORP_BROWSERS", "").split(sep=",")
            ],
        }
    else:
        preferences = {
            "Windows": ["Chrome", "Firefox", "ChromiumEdge"],
            "Linux": ["Chrome", "Firefox", "ChromiumEdge"],
            "Darwin": ["Chrome", "Firefox", "ChromiumEdge", "Safari"],
            "default": ["Chrome", "Firefox"],
        }
    return preferences
