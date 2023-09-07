import unittest.mock as mock

import pytest
from webdriver_manager.core.os_manager import ChromeType

from RPA.core import webdriver

from . import RESULTS_DIR


@pytest.fixture(autouse=True, scope="module")
def disable_caching():
    with mock.patch(
        "webdriver_manager.core.driver_cache.DriverCacheManager.find_driver",
        new=mock.Mock(return_value=None),
    ):
        yield


# Tests with different Chrome versions, which trigger different download approaches.
@pytest.mark.parametrize("version_override", [None, "114.0.5735.198", "115.0.5790.110"])
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
