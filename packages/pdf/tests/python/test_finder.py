import re

import pytest

from . import TestFiles, library


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
    result = library.set_anchor_to_element(locator, trim=trim, ignore_case=True)

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
    result = library.find_text(locator, trim=trim, ignore_case=True)

    assert result[0].neighbours[0] == expected


def test_find_text_left(library):
    library.open_pdf(TestFiles.invoice_pdf)
    invoice_label = library.find_text("text:INV-3337", direction="left")

    assert invoice_label[0].neighbours[0] == "Invoice Number"


def test_find_text_bottom(library):
    library.open_pdf(TestFiles.invoice_pdf)
    service = library.find_text("text:service", direction="bottom", ignore_case=True)

    assert "Web Design" in service[0].neighbours[0]


def test_find_text_top(library):
    library.open_pdf(TestFiles.invoice_pdf)
    items = library.find_text("text:Tax", direction="top")

    assert items[0].neighbours[0] == "Sub Total"


def test_find_text_matching_regexp(library):
    library.open_pdf(TestFiles.invoice_pdf)
    items = library.find_text(
        "text:Invoice Number", direction="right", regexp="INV-\\d{4}"
    )

    assert items[0].neighbours[0] == "INV-3337"


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
        "coords:345,645,520,725", direction="box", closest_neighbours=None
    )

    assert len(items[0].neighbours) == len(expected)
    for item in items[0].neighbours:
        assert item in expected


def test_find_text_box_not_found(library):
    library.open_pdf(TestFiles.invoice_pdf)
    items = library.find_text("text:Taxx", direction="box")

    assert not items


@pytest.mark.parametrize(
    "locator,direction,neighbour,expected_anchor,expected_neighbour",
    [
        ("Rate/Price", "down", 1, None, r"\$85.00"),
        ("Total", "right", 1, None, r"\$93.50"),
        ("Total", "up", 1, None, "Tax"),
        ("regex:.*Bank", "down", 1, "ANZ", "Payment.+Page 1/1$"),
        ("regex:Payment", "up", 1, "Payment", "ANZ Bank.+432$"),
        ("regex:To:", "up", 1, "Test Business", "From:.+slicedinvoices.com$"),
        ("regex:January 31", "left", 1, "2016", "Due Date"),
        ("Sub Total", "down", 3, None, r"\$8.50"),
    ],
)
def test_find_text(
    library, locator, direction, neighbour, expected_anchor, expected_neighbour
):
    library.open_pdf(TestFiles.invoice_pdf)
    matches = library.find_text(
        locator, pagenum=1, direction=direction, closest_neighbours=neighbour
    )
    assert matches, "no results found"
    match = matches[0]
    expected_anchor = expected_anchor or locator
    assert expected_anchor in match.anchor
    found_neighbour = match.neighbours[neighbour - 1]
    assert re.match(
        expected_neighbour, found_neighbour, flags=re.DOTALL
    ), f"doesn't match pattern {expected_neighbour}"


@pytest.mark.parametrize(
    "locator, ignore_case, expected_anchor",
    [
        ("text:Distance \n(mi)", False, "Distance \n(mi)"),
        ("subtext:Distance", False, "Distance \n(mi)"),
        ("subtext:name", False, None),
        ("subtext:name", True, "Cycle \nName"),
    ],
)
def test_find_text_subtext(library, locator, ignore_case, expected_anchor):
    library.open_pdf(TestFiles.camelot_table)
    matches = library.find_text(locator, ignore_case=ignore_case)
    if expected_anchor:
        assert matches, "no results found"
        match = matches[0]
        assert match.anchor == expected_anchor
    else:
        assert not matches, "shouldn't find results"
