import logging
import pytest
from pathlib import Path

from PIL import Image
from pytesseract import TesseractNotFoundError

from RPA.recognition import ocr
from RPA.core.geometry import Region


IMAGES = Path(__file__).resolve().parent / "images"
DATA = {
    "Standard": ("source.png", "Standard"),
    "Calculator": ("source.png", "Calculator"),
    "gnucash_main_window": ("gnucash_main_screen.png", "New")
}

GNUCASH_MAIN_WINDOW = IMAGES / DATA["gnucash_main_window"][0]


@pytest.mark.parametrize(
    "arg",
    [
        GNUCASH_MAIN_WINDOW,
        Image.open(GNUCASH_MAIN_WINDOW)
    ]
)
def test_read(arg):
    output = ocr.read(arg)

    assert "File Edit View Actions Business Reports Tools Windows Help" in output
    assert "Save Close Open Edit New Delete" in output


def test_read_when_no_tesseract(monkeypatch):
    monkeypatch.setattr("pytesseract.pytesseract.tesseract_cmd", "totallynotatesseract.exe")

    expected_text = (
        "tesseract is not installed or not in PATH, "
        "see library documentation for installation instructions"
    )
    with pytest.raises(EnvironmentError) as err:
        _ = ocr.read(GNUCASH_MAIN_WINDOW)

    assert str(err.value) == expected_text


def test_find_when_no_tesseract(monkeypatch):
    monkeypatch.setattr("pytesseract.pytesseract.tesseract_cmd", "totallynotatesseract.exe")

    expected_text = (
        "tesseract is not installed or not in PATH, "
        "see library documentation for installation instructions"
    )
    with pytest.raises(EnvironmentError) as err:
        _ = ocr.find(GNUCASH_MAIN_WINDOW, "fail")

    assert str(err.value) == expected_text


@pytest.mark.parametrize("image, text", DATA.values(), ids=DATA.keys())
def test_find(image, text):
    matches = ocr.find(IMAGES / image, text)
    assert len(matches) == 1

    match = matches[0]
    assert match["text"] == text
    assert match["confidence"] == 100


def test_find_no_text():
    with pytest.raises(ValueError) as err:
        _ = ocr.find(GNUCASH_MAIN_WINDOW, "")

    assert str(err.value) == "Empty search string"


def test__iter_rows():
    data = {
        "conf": [-1, -1, -1],
        "level": [1, 2, 3],
        "page_num": [1, 1, 1],
        "text": ["A", "B", "C"]
    }
    expected = (
        {"conf": -1, "level": 1, "page_num": 1, "text": "A"},
        {"conf": -1, "level": 2, "page_num": 1, "text": "B"},
        {"conf": -1, "level": 3, "page_num": 1, "text": "C"}
    )
    result = tuple(ocr._iter_rows(data))

    assert result == expected


def test__match_lines():
    lines = [[
        {"text": "Open", "region": Region(left=1356, top=440, right=1417, bottom=473)},
        {"text": "Edit", "region": Region(left=1493, top=440, right=1536, bottom=473)},
        {"text": "New", "region": Region(left=1641, top=446, right=1690, bottom=464)},
        {"text": "Delete", "region": Region(left=1755, top=444, right=1831, bottom=464)}
    ]]

    expected = [{
        "text": "New",
        "region": Region(left=1641, top=446, right=1690, bottom=464),
        "confidence": 100.0
    }]
    result = ocr._match_lines(lines, "New", 100)

    assert result == expected
