import pytest

from RPA.recognition import ocr


def _tesseract_data(words):
    """Build ``image_to_data`` style output for a single line of words."""
    count = len(words)
    return {
        "level": [5] * count,
        "text": list(words),
        "conf": ["95"] * count,
        "block_num": [1] * count,
        "par_num": [1] * count,
        "line_num": [1] * count,
        "left": [10 + 50 * index for index in range(count)],
        "top": [20] * count,
        "width": [40] * count,
        "height": [10] * count,
        "word_num": list(range(1, count + 1)),
    }


@pytest.mark.parametrize(
    "words",
    [
        (" ", "Open", "New"),
        ("Open", "", "New"),
        ("Open", "New", " "),
    ],
    ids=["blank-first", "blank-middle", "blank-last"],
)
def test_dict_lines_skips_blank_words(words):
    result = ocr._dict_lines(_tesseract_data(words))

    assert [[word["text"] for word in line] for line in result] == [["Open", "New"]]


def test_dict_lines_only_blank_words():
    assert ocr._dict_lines(_tesseract_data((" ", ""))) == []


def test_match_lines_after_blank_word():
    lines = ocr._dict_lines(_tesseract_data((" ", "Open", "New")))

    result = ocr._match_lines(lines, "Open New", 100)

    assert [match["text"] for match in result] == ["Open New"]
