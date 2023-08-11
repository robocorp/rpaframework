import re

import pytest

from . import library  # for the fixture to work
from . import TestFiles, temp_filename  # noqa


def _escape_string(value: str) -> str:
    to_escape = {"."}
    values = []
    for char in value:
        if char in to_escape:
            char = "\\\\" + oct(ord(char)).replace("o", "")
        values.append(char)
    return "".join(values)


def assert_field_value(lib, name, value):
    value = _escape_string(value)
    content = lib.active_pdf_document.fileobject.read()
    assert re.search(rf"{name}[^>]+{value}".encode(), content)


@pytest.mark.parametrize(
    "trim,text",
    [
        (True, "ILMOITA VERKOSSA\nvero.fi/omavero"),
        (False, "ILMOITA VERKOSSA\nvero.fi/omavero\n"),
    ],
)
def test_convert(library, trim, text):
    library.convert(TestFiles.vero_pdf, trim=trim)
    assert (
        len(library.active_pdf_document.has_converted_pages)
        == library.get_number_of_pages()
    )

    first_paragraph = library.active_pdf_document.get_page(1).content[0]
    assert first_paragraph.text == text

    # A secondary conversion wouldn't be triggered on already converted PDF files.
    library.convert(TestFiles.vero_pdf, trim=not trim)  # reverse trimming flag
    first_paragraph = library.active_pdf_document.get_page(1).content[0]
    assert first_paragraph.text == text  # still getting the same expected text


def test_get_input_fields(library):
    fields = library.get_input_fields(TestFiles.vero_pdf)

    assert len(fields) == 65
    assert fields["Puhelinnumero"]["value"] == None
    assert isinstance(fields["Puhelinnumero"]["rect"], tuple)


def test_get_input_fields_replace_none_values(library):
    fields = library.get_input_fields(TestFiles.vero_pdf, replace_none_value=True)
    assert fields["Puhelinnumero"]["value"] == "Puhelinnumero"


def test_set_field_value(library):
    fields = library.get_input_fields(TestFiles.vero_pdf)
    new_number = "+358-55-12322121312"

    assert fields["Puhelinnumero"]["value"] == None

    library.set_field_value("Puhelinnumero", new_number)

    assert fields["Puhelinnumero"]["value"] == new_number


def test_set_field_value_encoding(library):
    fields = library.get_input_fields(TestFiles.foersom_pdf, encoding="utf-16")

    name_field = "Given Name Text Box"
    assert not fields[name_field]["value"]
    new_name = "Mark"
    library.set_field_value(name_field, new_name)
    assert fields[name_field]["value"] == new_name

    driving_field = "Driving License Check Box"
    assert fields[driving_field]["value"].name == "Off"  # unchecked
    new_driving = "/Yes"
    library.set_field_value(driving_field, new_driving)  # checks it

    color_field = "Favourite Colour List Box"
    assert fields[color_field]["value"] == "Red"
    new_color = "Black"
    library.set_field_value(color_field, new_color)

    with temp_filename(suffix=".pdf") as tmp_file:
        library.save_field_values(output_path=tmp_file, use_appearances_writer=True)
        library.switch_to_pdf(tmp_file)
        # Fields can still be retrieved even after the PDF is saved.
        new_fields = library.get_input_fields()
        assert new_fields[name_field]["value"] == new_name
        assert new_fields[driving_field]["value"] == new_driving
        assert new_fields[color_field]["value"] == new_color


def test_set_field_value_checkbox(library):
    fields = library.get_input_fields(TestFiles.alianz_pdf)
    checkbox_name = "VeroeffentlichungInst"
    value_obj = fields[checkbox_name]["value"]
    assert value_obj.name == "Off"  # checkbox not checked yet

    # Tick the checkbox and save the new state of it.
    library.set_field_value(checkbox_name, "/Yes")

    with temp_filename(suffix=".pdf") as tmp_file:
        library.save_field_values(output_path=tmp_file, use_appearances_writer=True)
        library.switch_to_pdf(tmp_file)
        new_fields = library.get_input_fields()
        assert new_fields[checkbox_name]["value"] == "/Yes"
        assert_field_value(library, checkbox_name, "Yes")


@pytest.mark.parametrize("set_fields", [False, True])
def test_save_field_values_fields_exist(library, set_fields):
    library.open_pdf(TestFiles.vero_pdf)
    to_insert = {
        "Puhelinnumero": "12313123",  # new number
        "Paivays": "01.04.2021",  # new date
    }

    with temp_filename(suffix="-fields.pdf") as tmp_file:
        if set_fields:
            # Keep non-empty values, because null fields will fail the saving.
            existing_fields = library.get_input_fields(replace_none_value=True)
            for name, value in to_insert.items():
                library.set_field_value(name, value)
                assert existing_fields[name]["value"] == value
            library.save_field_values(output_path=tmp_file)
        else:
            # There are no fields retrieved at all this time.
            library.save_field_values(output_path=tmp_file, newvals=to_insert)

        library.switch_to_pdf(tmp_file)
        for name, value in to_insert.items():
            assert_field_value(library, name, value)


def test_dump_pdf_as_xml(library):
    head = '<?xml version="1.0" encoding="utf-8" ?>'
    xml = library.dump_pdf_as_xml(TestFiles.invoice_pdf)  # get non-empty output
    assert xml.count(head) == 1

    xml = library.dump_pdf_as_xml(TestFiles.invoice_pdf)  # no double output
    assert xml.count(head) == 1


def test_convert_after_line_margin_is_set(library):
    library.set_convert_settings(line_margin=0.00000001)
    library.convert(TestFiles.vero_pdf)
    assert library.active_pdf_document

    page = library.active_pdf_document.get_page(1)
    first_paragraph, second_paragraph = page.content[0], page.content[1]
    assert first_paragraph.text == "ILMOITA VERKOSSA"
    assert second_paragraph.text == "vero.fi/omavero"
