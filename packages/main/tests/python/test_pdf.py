from pathlib import Path
import pytest
from RPA.PDF import PDF

RESOURCE_DIR = Path(__file__).resolve().parent / ".." / "resources"
TEMP_DIR = Path(__file__).resolve().parent / ".." / "temp"
imagesandtext_pdf = RESOURCE_DIR / "imagesandtext.pdf"
invoice_pdf = RESOURCE_DIR / "invoice.pdf"
vero_pdf = RESOURCE_DIR / "vero.pdf"
pytest_pdf = RESOURCE_DIR / "18467.pdf"
loremipsum_pdf = RESOURCE_DIR / "LoremIpsum.pdf"
encrypted_pdf = RESOURCE_DIR / "encrypted.pdf"


@pytest.fixture
def library():
    return PDF()


def test_page_count(library):
    assert library.get_number_of_pages(invoice_pdf) == 1
    assert library.get_number_of_pages(vero_pdf) == 2
    assert library.get_number_of_pages(pytest_pdf) == 9


def test_page_info(library):
    info = library.get_info(pytest_pdf)
    assert info["Pages"] == 9
    assert not info["Encrypted"]
    assert not info["Fields"]
    info = library.get_info(vero_pdf)
    assert info["Fields"]
    assert info["Pages"] == 2


def test_get_text_from_all_pages(library):
    text = library.get_text_from_pdf(loremipsum_pdf)
    assert len(text) == 1, "text should be parsed from 1 pages"
    assert len(text[1]) == 3622
    text = library.get_text_from_pdf(vero_pdf)
    assert len(text) == 2, "text should be parsed from 2 pages"
    assert "Muualle lomakkeeseen kirjoittamaasi tietoa ei käsitellä." in text[2]


def test_get_text_from_specific_page(library):
    text = library.get_text_from_pdf(pytest_pdf, pages=[7])
    assert "Plugins for Web Development" in text[7]


def test_set_anchor_to_element(library):
    library.open_pdf_document(invoice_pdf)
    result = library.set_anchor_to_element("text:due date")
    assert result
    result = library.set_anchor_to_element("text:due to the date")
    assert not result


def test_get_value_from_anchor_by_default_from_right(library):
    library.open_pdf_document(invoice_pdf)
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
    library.open_pdf_document(invoice_pdf)
    invoice_label = library.get_value_from_anchor("text:INV-3337", direction="left")
    assert invoice_label.text == "Invoice Number"


def test_get_from_anchor_from_bottom(library):
    library.open_pdf_document(invoice_pdf)
    service = library.get_value_from_anchor("text:service", direction="bottom")
    assert "Web Design" in service.text


def test_get_from_anchor_from_top(library):
    library.open_pdf_document(invoice_pdf)
    item = library.get_value_from_anchor("text:Tax", direction="top")
    assert item.text == "Sub Total"


def test_extract_pages_from_pdf(library):
    pages = [7, 8]
    target_pdf = TEMP_DIR / "extracted.pdf"
    library.extract_pages_from_pdf(pytest_pdf, target_pdf, pages)
    assert library.get_number_of_pages(target_pdf) == 2
    text = library.get_text_from_pdf(target_pdf)
    assert "Plugins for Web Development" in text[1]


def test_rotating(library):
    target_pdf = TEMP_DIR / "rotated.pdf"
    library.page_rotate(1, vero_pdf, target_pdf)
    # TODO. Assert


def test_get_pdf_xml_dump(library):
    library.open_pdf_document(invoice_pdf)
    xml = library.dump_pdf_as_xml()
    assert '<?xml version="1.0" encoding="utf-8" ?>' in xml


def test_get_input_fields(library):
    fields = library.get_input_fields(vero_pdf)
    assert fields["Puhelinnumero"]["value"] == ""
    assert isinstance(fields["Puhelinnumero"]["rect"], list)
    fields = library.get_input_fields(vero_pdf, replace_none_value=True)
    assert fields["Puhelinnumero"]["value"] == "Puhelinnumero"


@pytest.mark.skip(reason="known issue of reading fields of already updated pdf")
def test_update_field_values(library):
    update_fields = {"Puhelinnumero": "10-1231233", "Paivays": "01.01.2020"}
    target_pdf = TEMP_DIR / "values_updated.pdf"

    fields = library.get_input_fields(vero_pdf)
    assert fields["Puhelinnumero"]["value"] == ""

    library.update_field_values(vero_pdf, target_pdf, update_fields)
    fields = library.get_input_fields(target_pdf)
    assert fields["Puhelinnumero"]["value"] == update_fields["Puhelinnumero"]
    assert fields["Paivays"]["value"] == update_fields["Paivays"]


def test_set_field_value(library):
    target_pdf = TEMP_DIR / "copy_of_vero.pdf"
    library.open_pdf_document(vero_pdf)
    library.set_field_value("Puhelinnumero", "+358-55-12322121312")
    library.set_field_value("Paivays", "31.12.2020")
    library.save_pdf(vero_pdf, target_pdf)


def test_get_texts_matching_regexp(library):
    library.open_pdf_document(invoice_pdf)
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
    library.open_pdf_document(invoice_pdf)
    items = library.get_value_from_anchor(
        "coords:345,645,520,725", direction="box", only_closest=False
    )
    assert len(items) == len(expected)
    for item in items:
        assert item.text in expected
