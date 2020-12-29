import os
from pathlib import Path

import pytest
from RPA.PDF import PDF

RESOURCE_DIR = Path(__file__).resolve().parent / ".." / "resources"
TEMP_DIR = Path(__file__).resolve().parent / ".." / "temp"

IMAGESANDTEXT_PDF = RESOURCE_DIR / "imagesandtext.pdf"
INVOICE_PDF = RESOURCE_DIR / "invoice.pdf"
VERO_PDF = RESOURCE_DIR / "vero.pdf"
PYTEST_PDF = RESOURCE_DIR / "18467.pdf"
LOREMIPSUM_PDF = RESOURCE_DIR / "LoremIpsum.pdf"
ENCRYPTED_PDF = RESOURCE_DIR / "encrypted.pdf"


@pytest.fixture(scope="session", autouse=True)
def setup(request):
    os.makedirs(TEMP_DIR, exist_ok=True)


@pytest.fixture
def library():
    return PDF()


def test_page_count(library):
    assert library.get_number_of_pages(INVOICE_PDF) == 1
    assert library.get_number_of_pages(VERO_PDF) == 2
    assert library.get_number_of_pages(PYTEST_PDF) == 9


def test_page_info(library):
    info = library.get_info(PYTEST_PDF)
    assert info["Pages"] == 9
    assert not info["Encrypted"]
    assert not info["Fields"]
    info = library.get_info(VERO_PDF)
    assert info["Fields"]
    assert info["Pages"] == 2


def test_get_text_from_all_pages(library):
    text = library.get_text_from_pdf(LOREMIPSUM_PDF)
    assert len(text) == 1, "text should be parsed from 1 pages"
    assert len(text[1]) == 3622
    text = library.get_text_from_pdf(VERO_PDF)
    assert len(text) == 2, "text should be parsed from 2 pages"
    assert "Muualle lomakkeeseen kirjoittamaasi tietoa ei käsitellä." in text[2]


def test_get_text_from_specific_page(library):
    text = library.get_text_from_pdf(PYTEST_PDF, pages=[7])
    assert "Plugins for Web Development" in text[7]


def test_set_anchor_to_element(library):
    library.open_pdf_document(INVOICE_PDF)
    result = library.set_anchor_to_element("text:due date")
    assert result
    result = library.set_anchor_to_element("text:due to the date")
    assert not result


def test_get_value_from_anchor_by_default_from_right(library):
    library.open_pdf_document(INVOICE_PDF)
    invoice_number = library.get_value_from_anchor("text:invoice number")
    order_number = library.get_value_from_anchor("text:order number")
    invoice_date = library.get_value_from_anchor("text:invoice date")
    due_date = library.get_value_from_anchor("text:due date")
    total_due = library.get_value_from_anchor("text:total due")
    assert invoice_number.text == "INV-3337"
    assert order_number.text == "12345"
    assert invoice_date.text == "January 25, 2016"
    assert due_date.text == "January 31, 2016"
    assert total_due.text == "$93.50"


def test_get_value_from_anchor_from_left(library):
    library.open_pdf_document(INVOICE_PDF)
    invoice_label = library.get_value_from_anchor("text:INV-3337", direction="left")
    assert invoice_label.text == "Invoice Number"


def test_get_from_anchor_from_bottom(library):
    library.open_pdf_document(INVOICE_PDF)
    service = library.get_value_from_anchor("text:service", direction="bottom")
    assert "Web Design" in service.text


def test_get_from_anchor_from_top(library):
    library.open_pdf_document(INVOICE_PDF)
    item = library.get_value_from_anchor("text:Tax", direction="top")
    assert item.text == "Sub Total"


def test_extract_pages_from_pdf(library):
    pages = [7, 8]
    target_pdf = TEMP_DIR / "extracted.pdf"
    library.extract_pages_from_pdf(PYTEST_PDF, target_pdf, pages)
    assert library.get_number_of_pages(target_pdf) == 2
    text = library.get_text_from_pdf(target_pdf)
    assert "Plugins for Web Development" in text[1]


def test_rotating(library):
    target_pdf = TEMP_DIR / "rotated.pdf"
    library.page_rotate(1, VERO_PDF, target_pdf)
    # TODO. Assert


def test_get_pdf_xml_dump(library):
    library.open_pdf_document(INVOICE_PDF)
    xml = library.dump_pdf_as_xml()
    assert '<?xml version="1.0" encoding="utf-8" ?>' in xml


def test_get_input_fields(library):
    fields = library.get_input_fields(VERO_PDF)
    assert fields["Puhelinnumero"]["value"] == ""
    assert isinstance(fields["Puhelinnumero"]["rect"], list)
    fields = library.get_input_fields(VERO_PDF, replace_none_value=True)
    assert fields["Puhelinnumero"]["value"] == "Puhelinnumero"


@pytest.mark.skip(reason="known issue of reading fields of already updated pdf")
def test_update_field_values(library):
    update_fields = {"Puhelinnumero": "10-1231233", "Paivays": "01.01.2020"}
    target_pdf = TEMP_DIR / "values_updated.pdf"

    fields = library.get_input_fields(VERO_PDF)
    assert fields["Puhelinnumero"]["value"] == ""

    library.update_field_values(VERO_PDF, target_pdf, update_fields)
    fields = library.get_input_fields(target_pdf)
    assert fields["Puhelinnumero"]["value"] == update_fields["Puhelinnumero"]
    assert fields["Paivays"]["value"] == update_fields["Paivays"]


def test_set_field_value(library):
    target_pdf = TEMP_DIR / "copy_of_vero.pdf"
    library.open_pdf_document(VERO_PDF)
    library.set_field_value("Puhelinnumero", "+358-55-12322121312")
    library.set_field_value("Paivays", "31.12.2020")
    library.save_pdf(VERO_PDF, target_pdf)


def test_get_texts_matching_regexp(library):
    library.open_pdf_document(INVOICE_PDF)
    item = library.get_value_from_anchor(
        "text:Invoice Number", direction="right", regexp="INV-\\d{4}"
    )
    assert item.text == "INV-3337"


def test_get_texts_from_area(library):
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
    library.open_pdf_document(INVOICE_PDF)
    items = library.get_value_from_anchor(
        "coords:345,645,520,725", direction="box", only_closest=False
    )
    assert len(items) == len(expected)
    for item in items:
        assert item.text in expected
