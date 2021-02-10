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

    assert library.active_pdf_document
    assert first_paragraph.text == "ILMOITA VERKOSSA\nvero.fi/omavero"


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


@pytest.mark.xfail(reason="known issue of reading fields of already updated pdf")
def test_update_field_values(library):
    update_fields = {"Puhelinnumero": "10-1231233", "Paivays": "01.01.2020"}

    with temp_filename() as tmp_file:
        original_fields = library.get_input_fields(TestFiles.vero_pdf)
        library.update_field_values(TestFiles.vero_pdf, tmp_file, update_fields)

        # FIXME: this returns None, but it shouldn't!
        updated_fields = library.get_input_fields(tmp_file)

        assert original_fields["Puhelinnumero"]["value"] == ""
        assert (
            updated_fields["Puhelinnumero"]["value"] == update_fields["Puhelinnumero"]
        )
        assert updated_fields["Paivays"]["value"] == update_fields["Paivays"]


def test_dump_pdf_as_xml(library):
    xml = library.dump_pdf_as_xml(TestFiles.invoice_pdf)

    assert '<?xml version="1.0" encoding="utf-8" ?>' in xml
