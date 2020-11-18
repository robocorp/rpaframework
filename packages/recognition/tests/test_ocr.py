import logging
import pytest
from pathlib import Path

from RPA.recognition import ocr
from RPA.core.geometry import Region


IMAGES = Path(__file__).resolve().parent / "images"
DATA = {
    "Standard": ("source.png", "Standard"),
    "Calculator": ("source.png", "Calculator"),
}


@pytest.mark.parametrize("image, text", DATA.values(), ids=DATA.keys())
def test_find_ocr(image, text):
    matches = ocr.find(image=IMAGES / image)
    words = [match["text"] for match in matches]
    assert text in words
