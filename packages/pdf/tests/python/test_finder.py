import pytest

from . import (
    library,
    temp_filename,
    TestFiles,
)

# TODO: add tests to cover more conditions


@pytest.mark.parametrize(
    "locator, expected",
    [
        ("text:due date", True),
        ("text:this doesn't exists", False),
    ],
)
def test_set_anchor_to_element(library, locator, expected):
    library.open_pdf(TestFiles.invoice_pdf)
    result = library.set_anchor_to_element(locator)

    assert result is expected


def test_find_text_default_right(library):
    library.open_pdf(TestFiles.invoice_pdf)
    invoice_number = library.find_text("text:invoice number")
    order_number = library.find_text("text:order number")
    invoice_date = library.find_text("text:invoice date")
    due_date = library.find_text("text:due date")
    total_due = library.find_text("text:total due")

    assert invoice_number.text == "INV-3337"
    assert order_number.text == "12345"
    assert invoice_date.text == "January 25, 2016"
    assert due_date.text == "January 31, 2016"
    assert total_due.text == "$93.50"


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
