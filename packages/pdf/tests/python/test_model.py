import PyPDF2
import pytest

from . import (
    library,
    temp_filename,
    TestFiles,
)

# TODO: add tests to cover more conditions


def test_convert(library):
    library.convert(TestFiles.vero_pdf)
    first_paragraph = library.active_pdf_document.pages[1].content[0]
    second_paragraph = library.active_pdf_document.pages[1].content[1]
    assert library.active_pdf_document
    assert first_paragraph.text == "ILMOITA VERKOSSA"
    assert second_paragraph.text == "vero.fi/omavero"


def test_get_input_fields(library):
    fields = library.get_input_fields(TestFiles.vero_pdf)

    assert len(fields) == 65
    assert fields["Puhelinnumero"]["value"] == ""
    assert isinstance(fields["Puhelinnumero"]["rect"], list)


def test_get_input_fields_replace_none_values(library):
    fields = library.get_input_fields(TestFiles.vero_pdf, replace_none_value=True)
    assert fields["Puhelinnumero"]["value"] == "Puhelinnumero"


def test_set_field_value(library):
    fields = library.get_input_fields(TestFiles.vero_pdf)
    new_number = "+358-55-12322121312"

    assert fields["Puhelinnumero"]["value"] == ""

    library.set_field_value("Puhelinnumero", new_number)

    assert fields["Puhelinnumero"]["value"] == new_number


@pytest.mark.xfail(reason="Known issue: PDF won't show as having fields after saving")
def test_save_field_values_fields_exist(library):
    new_number = "12313123"
    new_date = "01.04.2021"

    with temp_filename() as tmp_file:
        library.open_pdf(TestFiles.vero_pdf)
        library.set_field_value("Puhelinnumero", new_number)
        library.set_field_value("Paivays", new_date)
        library.save_field_values(output_path=tmp_file)
        fields = library.get_input_fields(tmp_file)

        assert fields["Puhelinnumero"] == "12313123"
        assert fields["Paivays"] == "01.04.2021"


@pytest.mark.xfail(reason="Known issue: Field values won't show in text body")
def test_save_field_values_text_exists(library):
    new_number = "12313123"
    new_date = "01.04.2021"

    with temp_filename() as tmp_file:
        library.open_pdf(TestFiles.vero_pdf)
        library.set_field_value("Puhelinnumero", new_number)
        library.set_field_value("Paivays", new_date)
        library.save_field_values(output_path=tmp_file)
        text = library.get_text_from_pdf(tmp_file)

        assert new_number in text[2]
        assert new_date in text[2]


@pytest.mark.xfail(reason="Known issue: PDF won't show as having fields after saving")
def test_save_field_values_multiple_updates_in_one_operation(library):
    new_fields = {
        "Puhelinnumero": "12313123",
        "Paivays": "01.04.2021",
    }
    with temp_filename() as tmp_file:
        library.save_field_values(
            source_path=TestFiles.vero_pdf, output_path=tmp_file, newvals=new_fields
        )
        fields = library.get_input_fields(tmp_file)

        assert fields["Puhelinnumero"] == "12313123"
        assert fields["Paivays"] == "01.04.2021"


def test_dump_pdf_as_xml(library):
    xml = library.dump_pdf_as_xml(TestFiles.invoice_pdf)

    assert '<?xml version="1.0" encoding="utf-8" ?>' in xml
