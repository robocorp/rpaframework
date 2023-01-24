import os
import platform
from pathlib import Path


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
