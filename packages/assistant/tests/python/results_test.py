from typing import Dict, Any
import datetime

import pytest
from RPA.Assistant import Assistant


@pytest.fixture
def assistant() -> Assistant:
    assistant_lib = Assistant()
    return assistant_lib


def test_slider(assistant: Assistant):
    assistant.add_slider("slider", default=51)
    results = assistant._get_results()
    assert results.get("slider") == 51


def test_slider_str_default(assistant: Assistant):
    assistant.add_slider("slider", default="50.07")
    results = assistant._get_results()
    assert results.get("slider") == 50.07


def test_text_input(assistant: Assistant):
    assistant.add_text_input("txt_input", default="text")
    results = assistant._get_results()
    assert results.get("txt_input") == "text"


def test_dropdown(assistant: Assistant):
    assistant.add_drop_down("dropdown", options=["mark", "monkey"], default="monkey")
    results = assistant._get_results()
    assert results.get("dropdown") == "monkey"


def test_date_input_date(assistant: Assistant):
    test_date = datetime.date(1993, 4, 26)
    assistant.add_date_input("testdate", default=test_date)
    results = assistant._get_results()
    assert results.get("testdate") == test_date


def test_date_input_string(assistant: Assistant):
    assistant.add_date_input("birthdate", default="1993-04-26")
    results = assistant._get_results()
    assert results.get("birthdate") == datetime.date(1993, 4, 26)


def test_radio_input(assistant: Assistant):
    assistant.add_radio_buttons("radio", options="First,Second", default="Second")
    results = assistant._get_results()
    assert results.get("radio") == "Second"


def test_dotdict_access(assistant: Assistant):
    assistant.add_text_input("txt_input", default="text")
    results = assistant._get_results()
    assert results.txt_input == "text"
    assert results["txt_input"] == "text"
    assert results.get("txt_input") == "text"
