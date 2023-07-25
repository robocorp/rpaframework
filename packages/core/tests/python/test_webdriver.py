import mock
import pytest

from RPA.core import webdriver

from . import RESULTS_DIR


def _test_chrome_download():
    path = webdriver.download("Chrome", root=RESULTS_DIR)
    assert "chromedriver" in path


@pytest.mark.parametrize("version_override", [None, "114.0.5735.198"])
@mock.patch(
    "webdriver_manager.core.driver_cache.DriverCacheManager.find_driver",
    new=mock.Mock(return_value=None),
)  # disable caching
def test_chrome_download(version_override):
    if not version_override:
        _test_chrome_download()
        return

    get_version_location = "RPA.core.webdriver.ChromeDriver.get_browser_version_from_os"
    with mock.patch(get_version_location) as get_version:
        get_version.return_value = version_override
        _test_chrome_download()
