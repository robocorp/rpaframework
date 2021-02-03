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


@pytest.fixture
def manager_mock():
    manager = mock.Mock()
    manager.download_root = "mock/download/path"
    manager.get_driver_filename.return_value = "mockdriver.bin"
    return manager


@pytest.fixture
def multiname_manager_mock():
    manager = mock.Mock()
    manager.download_root = "mock/download/path"
    manager.get_driver_filename.return_value = ["first.bin", "second.bin"]
    return manager


def test_link_paths_single(manager_mock):
    paths = webdriver._link_paths(manager_mock)
    assert paths == [Path("mock/download/path/mockdriver.bin")]


def test_link_paths_multiple(multiname_manager_mock):
    paths = webdriver._link_paths(multiname_manager_mock)
    assert paths == [
        Path("mock/download/path/first.bin"),
        Path("mock/download/path/second.bin"),
    ]


def test_cache_path_single(manager_mock):
    webdriver._to_manager = to_manager = mock.Mock()
    to_manager.return_value = manager_mock

    path = webdriver.cache("some-browser")
    assert to_manager.called_once_with("some-browser")
    assert path is None


def test_cache_path_multiple(multiname_manager_mock):
    webdriver._to_manager = to_manager = mock.Mock()
    to_manager.return_value = multiname_manager_mock

    path = webdriver.cache("AValue")
    assert to_manager.called_once_with("Avalue")
    assert path is None
