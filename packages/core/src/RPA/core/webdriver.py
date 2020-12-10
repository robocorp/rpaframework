import logging
import os
import platform
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any, List, Optional

from selenium import webdriver
from webdrivermanager import AVAILABLE_DRIVERS

from RPA.core.types import is_list_like


LOGGER = logging.getLogger(__name__)

DRIVER_DIR = Path(tempfile.gettempdir()) / "drivers"
DRIVER_PREFERENCE = {
    "Windows": ["Chrome", "Firefox", "Edge", "Ie", "Opera"],
    "Linux": ["Chrome", "Firefox", "Opera"],
    "Darwin": ["Chrome", "Safari", "Firefox", "Opera"],
    "default": ["Chrome", "Firefox"],
}

CHROME_VERSION_PATTERN = r"(\d+\.\d+.\d+)(\.\d+)"
CHROME_VERSION_COMMANDS = {
    "Windows": [
        [
            "reg",
            "query",
            r"HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon",
            "/v",
            "version",
        ],
        [
            "reg",
            "query",
            r"HKEY_CURRENT_USER\Software\Chromium\BLBeacon",
            "/v",
            "version",
        ],
    ],
    "Linux": [
        ["chromium", "--version"],
        ["chromium-browser", "--version"],
        ["google-chrome", "--version"],
    ],
    "Darwin": [
        ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"],
        ["/Applications/Chromium.app/Contents/MacOS/Chromium", "--version"],
    ],
}


def executable(browser: str, download: bool = False) -> Optional[str]:
    """Get path to webdriver executable, and download it if requested.

    :param browser: name of browser to get webdriver for
    :param download: download driver binaries if they don't exist
    """
    LOGGER.debug(
        "Webdriver initialization for '%s' (download: %s)",
        browser,
        download,
    )

    browser = browser.lower().strip()
    factory = AVAILABLE_DRIVERS.get(browser)
    if not factory:
        return None

    driver_path = _driver_path(factory, download)
    if driver_path is None:
        LOGGER.debug("Failed to get driver path for %s", browser)
        return None

    if driver_path.exists() and not download:
        LOGGER.debug("Attempting to use existing driver: %s", driver_path)
        return str(driver_path)
    elif driver_path.exists() and download:
        # TODO: Implement version check for all browsers
        if browser == "chrome":
            chrome_version = _chrome_version()
            driver_version = _chromedriver_version(driver_path)
            if chrome_version != driver_version:
                _download_driver(factory)
        else:
            LOGGER.debug(
                "Driver download skipped, because it exists at '%s'", driver_path
            )
        return str(driver_path)
    elif not driver_path.exists() and download:
        _download_driver(factory)
        return str(driver_path)
    else:
        LOGGER.debug("Attempting to use driver from PATH")
        return None


def start(name: str, **options):
    """Start a Selenium webdriver."""
    name = name.strip()
    try:
        factory = getattr(webdriver, name)
    except AttributeError as e:
        raise RuntimeError(f"'{name}' is not a valid driver name") from e

    driver = factory(**options)
    return driver


def _driver_path(factory: Any, download: bool) -> Optional[Path]:
    if platform.system() != "Windows":
        manager = factory(link_path="/usr/bin")
    else:
        manager = factory()

    driver_names = manager.get_driver_filename()

    if driver_names is None:
        return None

    if not is_list_like(driver_names):
        driver_names = [driver_names]

    primary_path = Path(DRIVER_DIR) / driver_names[0]
    if download or primary_path.exists():
        return primary_path

    for name in driver_names:
        temp_path = Path(DRIVER_DIR) / name
        if temp_path.exists():
            return temp_path

        link_path = Path(manager.link_path) / name
        if link_path.exists():
            return link_path

    return Path(manager.link_path) / driver_names[0]


def _chrome_version() -> Optional[str]:
    system = platform.system()
    commands = CHROME_VERSION_COMMANDS.get(system)

    if not commands:
        LOGGER.warning("Unsupported system: %s", system)
        return None

    for cmd in commands:
        output = _run_command(cmd)
        if not output:
            continue

        version = re.search(CHROME_VERSION_PATTERN, output)
        if not version:
            continue

        return version.group(1)

    return None


def _chromedriver_version(path: Path) -> Optional[str]:
    output = _run_command([str(path), "--version"])
    if not output:
        return None

    version = re.search(CHROME_VERSION_PATTERN, output)
    if not version:
        return None

    return version.group(1)


def _download_driver(factory: Any, version: str = None) -> None:
    path = str(DRIVER_DIR)
    manager = factory(download_root=path, link_path=path)

    try:
        if version:
            bin_path, _ = manager.download_and_install(version, show_progress_bar=False)
        else:
            bin_path, _ = manager.download_and_install(show_progress_bar=False)

        if platform.system() == "Darwin" and bin_path:
            # TODO: Required for linux also?
            _set_executable_permissions(bin_path)

        LOGGER.debug(
            "%s downloaded to %s",
            manager.get_driver_filename(),
            bin_path,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to download wedriver: {exc}") from exc


def _set_executable_permissions(path: str) -> None:
    st = os.stat(path)
    os.chmod(
        path,
        st.st_mode | stat.S_IXOTH | stat.S_IXGRP | stat.S_IEXEC,
    )


def _run_command(args: List[str]) -> Optional[str]:
    try:
        output = subprocess.check_output(args)
        return output.decode().strip()
    except (FileNotFoundError, subprocess.CalledProcessError) as err:
        LOGGER.debug("Command failed: %s", err)
        return None
