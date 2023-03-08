from time import sleep

import pytest
from RPA.Assistant import Assistant
from RPA.Assistant.types import PageNotOpenError


def test_set_title_no_page_open(assistant: Assistant):
    with pytest.raises(PageNotOpenError) as excinfo:
        assistant.set_title("test")
    assert "Set title called when page is not open" in str(excinfo.value)


def test_flet_update_no_page_open(assistant: Assistant):
    with pytest.raises(PageNotOpenError) as excinfo:
        assistant.refresh_dialog()
    assert "No page open when update_elements was called" in str(excinfo.value)


def test_duplicate_name_fails(assistant: Assistant):
    with pytest.raises(ValueError) as excinfo:
        assistant.add_text_input("one")
        assistant.add_text_input("one")
    assert "already in use" in str(excinfo.value)


def test_different_names_work(assistant: Assistant):
    assistant.add_text_input("one")
    assistant.add_text_input("two")
    assistant.add_text_input("three")
