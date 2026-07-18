"""Tests for RPA.Desktop.keywords.screen."""
from unittest.mock import MagicMock, patch

from RPA.core.geometry import Point, Region
from RPA.Desktop.keywords.screen import ScreenKeywords


def _make_keywords():
    return ScreenKeywords(MagicMock())


def test_highlight_elements_returns_regions():
    keywords = _make_keywords()
    region = Region(1, 2, 3, 4)
    keywords.ctx.find_elements.return_value = [region]

    with patch(
        "RPA.Desktop.keywords.screen.utils.is_windows", return_value=True
    ), patch("RPA.Desktop.keywords.screen._draw_outline") as draw_outline:
        result = keywords.highlight_elements("locator")

    assert result == [region]
    draw_outline.assert_called_once_with(region)


def test_highlight_elements_converts_points_to_regions():
    keywords = _make_keywords()
    point = Point(10, 20)
    keywords.ctx.find_elements.return_value = [point]

    with patch(
        "RPA.Desktop.keywords.screen.utils.is_windows", return_value=True
    ), patch("RPA.Desktop.keywords.screen._draw_outline") as draw_outline:
        result = keywords.highlight_elements("locator")

    assert result == [Region(5, 15, 15, 25)]
    draw_outline.assert_called_once_with(Region(5, 15, 15, 25))
