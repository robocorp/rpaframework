import unittest.mock as mock

import pytest

from RPA.core import webdriver

from . import RESULTS_DIR


@pytest.mark.parametrize("version_override", [None, "114.0.5735.198", "115.0.5790.110"])
# Disables caching.
@mock.patch(
    "webdriver_manager.core.driver_cache.DriverCacheManager.find_driver",
    new=mock.Mock(return_value=None),
)
def test_chrome_download(version_override):
    driver_target = "RPA.core.webdriver.ChromeDriver"
    with mock.patch(driver_target, wraps=webdriver.ChromeDriver) as MockChromeDriver:
        if version_override:
            mock_get_version = mock.Mock(return_value=version_override)
            MockChromeDriver.get_browser_version_from_os = mock_get_version

        path = webdriver.download("Chrome", root=RESULTS_DIR)
        assert "chromedriver" in path
