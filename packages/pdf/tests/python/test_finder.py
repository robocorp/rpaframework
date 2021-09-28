import pytest

from . import (
    library,
    temp_filename,
    TestFiles,
)

# TODO: add tests to cover more conditions


@pytest.mark.parametrize(
    "locator, trim, expected",
    [
        ("text:due date", True, True),
        ("text:due date\n", False, True),
        ("text:this doesn't exists", True, False),
    ],
)
def test_set_anchor_to_element(library, locator, trim, expected):
    library.open_pdf(TestFiles.invoice_pdf)
    result = library.set_anchor_to_element(locator, trim=trim)

    assert result is expected


@pytest.mark.parametrize(
    "locator, trim, expected",
    [
        ("text:invoice number", True, "INV-3337"),
        ("text:order number", True, "12345"),
        ("text:invoice date", True, "January 25, 2016"),
        ("text:due date", True, "January 31, 2016"),
        ("text:total due", True, "$93.50"),
        ("text:invoice number\n", False, "INV-3337\n"),
    ],
)
def test_find_text_default_right(library, locator, trim, expected):
    library.open_pdf(TestFiles.invoice_pdf)
    result = library.find_text(locator, trim=trim)

    assert result.text == expected


def test_find_text_left(library):
    library.open_pdf(TestFiles.invoice_pdf)
    invoice_label = library.find_text("text:INV-3337", direction="left")

    assert invoice_label.text == "Invoice Number"


def test_find_text_bottom(library):
    library.open_pdf(TestFiles.invoice_pdf)
    service = library.find_text("text:service", direction="bottom")

    assert "Web Design" in service.text


def test_find_text_top(library):
    library.open_pdf(TestFiles.invoice_pdf)
    item = library.find_text("text:Tax", direction="top")

    assert item.text == "Sub Total"


def test_find_text_matching_regexp(library):
    library.open_pdf(TestFiles.invoice_pdf)
    item = library.find_text(
        "text:Invoice Number", direction="right", regexp="INV-\\d{4}"
    )

    assert item.text == "INV-3337"


def test_find_text_by_box_coordinates(library):
    expected = [
        "Invoice Number",
        "INV-3337",
        "Order Number",
        "12345",
        "Invoice Date",
        "January 25, 2016",
        "Due Date",
        "January 31, 2016",
        "Total Due",
        "$93.50",
    ]
    library.open_pdf(TestFiles.invoice_pdf)
    items = library.find_text(
        "coords:345,645,520,725", direction="box", only_closest=False
    )

    assert len(items) == len(expected)
    for item in items:
        assert item.text in expected


def test_find_text_box_not_found(library):
    library.open_pdf(TestFiles.invoice_pdf)
    item = library.find_text("text:Taxx", direction="box")

    assert not item
