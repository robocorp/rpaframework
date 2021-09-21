try:
    from contextlib import nullcontext as does_not_raise
except ImportError:
    from contextlib import ExitStack as does_not_raise
from datetime import date, datetime
from pathlib import Path

import pytest
from RPA.Dialogs import Dialogs


RESOURCES = Path(__file__).parent / "resources"


@pytest.fixture
def library():
    return Dialogs()


def test_add_heading(library):
    library.add_heading("Example Heading")
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "heading",
        "value": "Example Heading",
        "size": "medium",
    }


def test_add_text(library):
    library.add_text("Example Text")
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "text",
        "value": "Example Text",
        "size": "medium",
    }


def test_add_link(library):
    library.add_link("https://google.com")
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "link",
        "value": "https://google.com",
        "label": None,
    }


def test_add_image_url(library):
    library.add_image("https://example.com/image.png")
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "image",
        "value": "https://example.com/image.png",
        "width": None,
        "height": None,
    }


def test_add_image_local(library):
    path = str(RESOURCES / "cat.jpeg")
    library.add_image(path)
    assert len(library.elements) == 1

    element = library.elements[0]
    assert element["type"] == "image"
    assert element["value"] == path


def test_add_file(library):
    library.add_file(str(RESOURCES / "file1.txt"))
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "file",
        "value": str(RESOURCES / "file1.txt"),
        "label": None,
    }


def test_add_files(library):
    library.add_files("not-a-file")
    assert len(library.elements) == 0

    library.add_files(str(RESOURCES / "*.txt"))
    assert len(library.elements) == 2

    element = library.elements[0]
    assert element["type"] == "file"
    assert element["label"] == None

    path = Path(element["value"])
    assert path.exists()
    assert path.name in ("file1.txt", "file2.txt")


def test_add_icon(library):
    library.add_icon("success")
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "icon",
        "variant": "success",
        "size": 48,
    }


def test_add_text_input(library):
    library.add_text_input(name="input-field")
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "input-text",
        "name": "input-field",
        "placeholder": None,
        "rows": None,
        "label": None,
    }


def test_add_password_input(library):
    library.add_password_input("password-field")
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "input-password",
        "name": "password-field",
        "placeholder": None,
        "label": None,
    }


def test_add_hidden_input(library):
    library.add_hidden_input("hidden-field", "some value I guess?")
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "input-hidden",
        "name": "hidden-field",
        "value": "some value I guess?",
    }


def test_add_file_input(library):
    library.add_file_input("file-field")
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "input-file",
        "name": "file-field",
        "source": None,
        "destination": None,
        "file_type": None,
        "multiple": False,
        "label": None,
    }


def test_add_drop_down(library):
    library.add_drop_down("dropdown-field", options=[])
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "input-dropdown",
        "name": "dropdown-field",
        "options": [],
        "default": None,
        "label": None,
    }


@pytest.mark.parametrize(
    "default,expect",
    [
        ("2021-09-6", does_not_raise()),
        ("2021-09-06", does_not_raise()),
        ("2021-09-33", pytest.raises(ValueError)),
        ("2021-13-06", pytest.raises(ValueError)),
        (None, does_not_raise()),  # uses the current date as default
        (datetime.utcnow(), does_not_raise()),
        (datetime.utcnow().date(), does_not_raise()),
        (True, pytest.raises(ValueError)),  # unexpected value
    ]
)
@pytest.mark.freeze_time("2021-09-06")
def test_add_date_input(library, default, expect):
    with expect:
        library.add_date_input(
            "datepicker-field", default=default, label="My Date Picker"
        )

    py_date_format = "%Y-%m-%d"
    default = default or "2021-09-06"  # for the current date case
    if isinstance(default, date):
        default = default.strftime(py_date_format)

    elems_count = len(library.elements)
    assert elems_count in (0, 1)
    if elems_count:
        assert library.elements[0] == {
            "type": "input-datepicker",
            "name": "datepicker-field",
            "_format": py_date_format,
            "format": "yyyy-MM-dd",
            "default": default,
            "label": "My Date Picker",
        }


def test_add_radio_buttons(library):
    library.add_radio_buttons("radio-field", options=[])
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "input-radio",
        "name": "radio-field",
        "options": [],
        "default": None,
        "label": None,
    }


def test_add_checkbox(library):
    library.add_checkbox("checkbox-field", "Checkbox value")
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "input-checkbox",
        "name": "checkbox-field",
        "label": "Checkbox value",
        "default": False,
    }


def test_add_submit_buttons(library):
    library.add_submit_buttons(buttons=[])
    assert len(library.elements) == 1
    assert library.elements[0] == {
        "type": "submit",
        "buttons": [],
        "default": None,
    }


def test_clear_elements(library):
    library.add_heading("Whatever")
    library.add_heading("Whatever")
    library.add_heading("Whatever")
    library.add_heading("Whatever")
    assert len(library.elements) == 4

    library.clear_elements()
    assert len(library.elements) == 0
