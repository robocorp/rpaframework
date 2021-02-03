import logging
import os
import platform
import stat
from pathlib import Path
from typing import Any, Optional

from selenium import webdriver
from webdrivermanager import AVAILABLE_DRIVERS

from RPA.core.types import is_list_like
from RPA.core.robocorp import robocorp_home


LOGGER = logging.getLogger(__name__)

DRIVER_ROOT = robocorp_home() / "webdrivers"
DRIVER_PREFERENCE = {
    "Windows": ["Chrome", "Firefox", "Edge", "Ie", "Opera"],
    "Linux": ["Chrome", "Firefox", "Opera"],
    "Darwin": ["Chrome", "Safari", "Firefox", "Opera"],
    "default": ["Chrome", "Firefox"],
}


def start(browser: str, **options):
    """Start a webdriver with the given options."""
    browser = browser.strip()
    factory = getattr(webdriver, browser, None)

    if not factory:
        raise ValueError(f"Unsupported browser: {browser}")

    driver = factory(**options)
    return driver


def download(browser: str, root: Path = DRIVER_ROOT) -> Optional[Path]:
    """Download a webdriver binary for the given browser,
    and return the path to it. Attempts to use "compatible" mode
    to match browser and webdriver versions.
    """
    manager = _to_manager(browser, root)
    if manager.get_driver_filename() is None:
        return None

    os.makedirs(manager.download_root, exist_ok=True)
    _link_clean(manager)

    result = manager.download_and_install("compatible", show_progress_bar=False)
    if result is None:
        raise RuntimeError("Failed to extract webdriver from archive")

    path = result[0]
    if platform.system() != "Windows":
        _set_executable(path)

    LOGGER.debug("Downloaded webdriver to: %s", path)
    return path


def cache(browser: str, root: Path = DRIVER_ROOT) -> Optional[Path]:
    """Return path to given browser's webdriver, if binary
    exists in cache.
    """
    manager = _to_manager(browser, root)

    for path in _link_paths(manager):
        if path.exists():
            LOGGER.debug("Found cached webdriver: %s", path)
            return path

    return None


def _to_manager(browser: str, root: Path = DRIVER_ROOT):
    browser = browser.strip()
    factory = AVAILABLE_DRIVERS.get(browser.lower())

    if not factory:
        raise ValueError(f"Unsupported browser: {browser}")

    manager = factory(download_root=root, link_path=root)
    return manager


def _link_paths(manager: Any):
    names = manager.get_driver_filename()

    if names is None:
        return []

    if not is_list_like(names):
        names = [names]

    return [Path(manager.download_root) / name for name in names]


def _link_clean(manager: Any):
    for path in _link_paths(manager):
        if not path.exists():
            continue
        try:
            os.unlink(path)
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.debug("Failed to remove symlink: %s", exc)


def _set_executable(path: str) -> None:
    st = os.stat(path)
    os.chmod(
        path,
        st.st_mode | stat.S_IXOTH | stat.S_IXGRP | stat.S_IEXEC,
    )
