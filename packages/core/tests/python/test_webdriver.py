import platform
import re
import unittest.mock as mock
from pathlib import Path

import pytest
from webdriver_manager.core.os_manager import ChromeType

from RPA.core import webdriver

from . import RESULTS_DIR


@pytest.fixture(autouse=True, scope="module")
def disable_caching_enable_logging():
    with mock.patch(
        "webdriver_manager.core.driver_cache.DriverCacheManager.find_driver",
        new=mock.Mock(return_value=None),
    ), mock.patch("RPA.core.webdriver.suppress_logging"):
        yield


# Tests with different Chrome versions, which trigger different download approaches.
@pytest.mark.parametrize(
    "version_override",
    [
        None,  # whatever the system currently has
        "114.0.5735",  # solveable and requires solving
        "114.0.5735.198",  # solveable, not requiring solving, but non-existing
        "115.0.5790.110",  # non-solveable, not requiring solving
        "117.0.5938",  # non-solveable despite requiring solving
    ],
)
def test_chrome_download(version_override):
    get_version_target = "RPA.core.webdriver.ChromeDriver.get_browser_version_from_os"
    browser_type = (
        ChromeType.CHROMIUM if webdriver._is_chromium() else ChromeType.GOOGLE
    )
    get_version = lambda: webdriver._OPS_MANAGER.get_browser_version_from_os(
        browser_type
    )
    with mock.patch(get_version_target, wraps=get_version) as mock_get_version:
        if version_override:
            mock_get_version.return_value = version_override

        path = webdriver.download("Chrome", root=RESULTS_DIR)
        assert "chromedriver" in path


def test_firefox_download():
    path = webdriver.download("Firefox", root=RESULTS_DIR)
    assert "geckodriver" in path


def test_edge_download():
    path = webdriver.download("Edge", root=RESULTS_DIR)
    assert "msedgedriver" in path


def test_ie_download():
    path = webdriver.download("Ie", root=RESULTS_DIR)
    assert "IEDriverServer.exe" in path


@pytest.mark.parametrize("browser", ["Chrome", "Firefox", "Edge", "Ie"])
def test_get_browser_version(browser):
    version = webdriver.get_browser_version(browser)
    print(f"{browser}: {version}")


@pytest.mark.skipif(
    platform.system() != "Windows", reason="requires Windows with IE installed"
)
@pytest.mark.parametrize(
    "path", [None, r"C:\Program Files\Internet Explorer\iexplore.exe"]
)
def test_get_ie_version(path):
    version = webdriver.get_browser_version("Ie", path=path)
    assert re.match(r"\d+(\.\d+){3}$", version)  # 4 atoms in the version


@pytest.mark.skipif(
    platform.system() != "Darwin", reason="requires Mac with Chrome installed"
)
def test_get_chrome_version_path_mac():
    path = (
        Path("/Applications")
        / r"Google\ Chrome.app"
        / "Contents"
        / "MacOS"
        / r"Google\ Chrome"
    )
    version = webdriver.get_browser_version("Chrome", path=str(path))
    assert re.match(r"\d+(\.\d+){2,3}$", version)  # 3-4 atoms in the version
