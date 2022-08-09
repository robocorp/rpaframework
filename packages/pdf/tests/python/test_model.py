import re

import pytest

from . import (
    # noqa
    library,  # for the fixture to work
    temp_filename,
    TestFiles,
)


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
    assert fields["Puhelinnumero"]["value"] == ""
    assert isinstance(fields["Puhelinnumero"]["rect"], tuple)


def test_get_input_fields_replace_none_values(library):
    fields = library.get_input_fields(TestFiles.vero_pdf, replace_none_value=True)
    assert fields["Puhelinnumero"]["value"] == "Puhelinnumero"


def test_set_field_value(library):
    fields = library.get_input_fields(TestFiles.vero_pdf)
    new_number = "+358-55-12322121312"

    assert fields["Puhelinnumero"]["value"] == ""

    library.set_field_value("Puhelinnumero", new_number)

    assert fields["Puhelinnumero"]["value"] == new_number


def test_set_field_value_encoding(library):
    fields = library.get_input_fields(TestFiles.foersom_pdf, encoding="utf-16")
    name_field = "Given Name Text Box"
    assert not fields[name_field]["value"]

    new_name = "Mark"
    library.set_field_value(name_field, new_name)
    assert fields[name_field]["value"] == new_name

    with temp_filename(suffix=".pdf") as tmp_file:
        library.save_field_values(output_path=tmp_file, use_appearances_writer=True)
        library.switch_to_pdf(tmp_file)
        with pytest.raises(KeyError):
            # This output can't retrieve fields after save anymore.
            library.get_input_fields()
        content = library.active_pdf_document.fileobject.read()
        assert new_name.encode() in content


def test_set_field_value_checkbox(library):
    fields = library.get_input_fields(TestFiles.alianz_pdf)
    checkbox_name = "VeroeffentlichungInst"
    assert fields[checkbox_name]["value"].name == "Off"

    library.set_field_value(checkbox_name, "Yes")  # ticks it
    with temp_filename(suffix=".pdf") as tmp_file:
        library.save_field_values(output_path=tmp_file)
        library.switch_to_pdf(tmp_file)
        with pytest.raises(KeyError):
            # This output can't retrieve fields after save anymore.
            library.get_input_fields()
        content = library.active_pdf_document.fileobject.read()
        assert re.search(rf"{checkbox_name}[^>]+Yes".encode(), content)


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
