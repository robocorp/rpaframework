"""Tests for RPA.Desktop.keywords.finder."""
import time
from unittest.mock import MagicMock, patch

import pytest

from RPA.core.geometry import Region
from RPA.Desktop.keywords import TimeoutException
from RPA.Desktop.keywords.finder import FinderKeywords


def _make_keywords():
    return FinderKeywords(MagicMock())


def test_wait_for_element_retries_until_found():
    keywords = _make_keywords()
    region = Region(1, 2, 3, 4)

    with patch.object(
        keywords, "find_elements", side_effect=[[], [], [region]]
    ) as find_elements:
        result = keywords.wait_for_element("locator", timeout=5, interval=0.01)

    assert result == region
    assert find_elements.call_count == 3


def test_wait_for_element_waits_for_timeout():
    keywords = _make_keywords()

    with patch.object(keywords, "find_elements", return_value=[]) as find_elements:
        start = time.time()
        with pytest.raises(TimeoutException, match="No matches found"):
            keywords.wait_for_element("locator", timeout=0.3, interval=0.05)
        duration = time.time() - start

    assert duration >= 0.3
    assert find_elements.call_count > 1


def test_wait_for_element_retries_multiple_matches():
    keywords = _make_keywords()
    first, second = Region(1, 2, 3, 4), Region(5, 6, 7, 8)

    with patch.object(
        keywords, "find_elements", side_effect=[[first, second], [first]]
    ) as find_elements:
        result = keywords.wait_for_element("locator", timeout=5, interval=0.01)

    assert result == first
    assert find_elements.call_count == 2
