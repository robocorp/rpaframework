import pytest
from RPA.Dialogs import Dialogs


@pytest.mark.skip(reason="problem with github actions")
@pytest.mark.parametrize(
    "keyword,expected",
    [
        ("add_title", ["title"]),
        ("add_text_input", ["label", "name"]),
        ("add_hidden_input", ["label", "element_id", "name", "value"]),
        ("add_file_input", ["label", "element_id", "name", "filetypes"]),
        ("add_dropdown", ["label", "element_id", "options"]),
        ("add_submit", ["name", "buttons"]),
        ("add_checkbox", ["label", "element_id", "options"]),
        ("add_textarea", ["name"]),
        ("add_text", ["value"]),
        ("add_radio_buttons", ["element_id", "options"]),
    ],
)
def test_keywords_without_required_params(keyword, expected):
    lib = Dialogs()
    dom_func = getattr(lib, keyword, None)
    with pytest.raises(TypeError) as exc:
        dom_func()
    exception_values = str(exc.value).split(":")[-1]
    for e in expected:
        assert e in exception_values
