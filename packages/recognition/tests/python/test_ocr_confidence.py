from RPA.core.geometry import Region
from RPA.recognition import ocr


def test_dict_lines_preserves_tesseract_confidence():
    data = {
        "level": [5, 5, 5],
        "text": ["Open", "New", "Ignored"],
        "conf": ["95.5", "73", "-1"],
        "block_num": [1, 1, 1],
        "par_num": [1, 1, 1],
        "line_num": [1, 1, 1],
        "left": [10, 30, 60],
        "top": [20, 20, 20],
        "width": [10, 20, 30],
        "height": [10, 10, 10],
        "word_num": [1, 2, 3],
    }

    result = ocr._dict_lines(data)

    assert result == [
        [
            {
                "text": "Open",
                "region": Region.from_size(10, 20, 10, 10),
                "ocr_confidence": 95.5,
            },
            {
                "text": "New",
                "region": Region.from_size(30, 20, 20, 10),
                "ocr_confidence": 73.0,
            },
            {
                "text": "Ignored",
                "region": Region.from_size(60, 20, 30, 10),
                "ocr_confidence": None,
            },
        ]
    ]


def test_match_lines_returns_average_ocr_confidence():
    lines = [
        [
            {
                "text": "Open",
                "region": Region.from_size(10, 20, 10, 10),
                "ocr_confidence": 95.5,
            },
            {
                "text": "New",
                "region": Region.from_size(30, 20, 20, 10),
                "ocr_confidence": 73.0,
            },
        ]
    ]

    result = ocr._match_lines(lines, "Open New", 100)

    assert result == [
        {
            "text": "Open New",
            "region": Region.from_size(10, 20, 40, 10),
            "confidence": 100.0,
            "ocr_confidence": 84.25,
        }
    ]
