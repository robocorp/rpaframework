import mock
import pytest
from pathlib import Path
from RPA.core import webdriver


VERSION_STRINGS = (
    (None, None),
    ("not-a-version", None),
    ("22.0.1", None),
    ("79.29.1.0", "79.29.1"),
    ("81.22.122.03", "81.22.122"),
)


def as_factory(func):
    return lambda *args, **kwargs: func


@pytest.fixture
def manager_mock():
    manager = mock.Mock()
    manager.link_path = "mock/link/path"
    manager.get_driver_filename.return_value = "mockdriver.bin"
    return manager


@pytest.fixture
def multiname_manager_mock():
    manager = mock.Mock()
    manager.link_path = "mock/link/path"
    manager.get_driver_filename.return_value = ["first.bin", "second.bin"]
    return manager


def test_driver_path_no_download(manager_mock):
    path = webdriver._driver_path(as_factory(manager_mock), download=False)
    assert path == Path("mock/link/path", "mockdriver.bin")


def test_driver_path_download(manager_mock):
    path = webdriver._driver_path(as_factory(manager_mock), download=True)
    assert path == Path(webdriver.DRIVER_DIR, "mockdriver.bin")


def test_driver_path_multiple(multiname_manager_mock):
    path = webdriver._driver_path(as_factory(multiname_manager_mock), download=False)
    assert path == Path("mock/link/path", "first.bin")

    path = webdriver._driver_path(as_factory(multiname_manager_mock), download=True)
    assert path == Path(webdriver.DRIVER_DIR, "first.bin")


@pytest.mark.parametrize("system", ["Windows", "Linux", "Darwin"])
@pytest.mark.parametrize("output,expected", VERSION_STRINGS)
@mock.patch("RPA.core.webdriver._run_command")
@mock.patch("RPA.core.webdriver.platform")
def test_chrome_version(mock_platform, mock_run, system, output, expected):
    mock_platform.system.return_value = system

    mock_run.return_value = output
    result = webdriver._chrome_version()
    assert result == expected


@mock.patch("RPA.core.webdriver._run_command")
@mock.patch("RPA.core.webdriver.platform")
def test_chrome_version_unknown_system(mock_platform, mock_run):
    mock_platform.system.return_value = "atari2600"
    result = webdriver._chrome_version()
    assert result == None


@pytest.mark.parametrize("output,expected", VERSION_STRINGS)
@mock.patch("RPA.core.webdriver._run_command")
def test_chromedriver_version(mock_run, output, expected):
    mock_run.return_value = output
    result = webdriver._chromedriver_version("path/to/driver")
    assert result == expected
    mock_run.assert_called_once_with(["path/to/driver", "--version"])
