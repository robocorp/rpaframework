import pytest
from RPA.Assistant import Assistant
from RPA.Assistant.types import Icon


def test_rows(assistant: Assistant):
    assistant.open_row()
    assistant.add_date_input("my_date", label="My Date")
    assistant.add_text("miscallenous text")
    assistant.close_row()


def test_container(assistant: Assistant):
    assistant.open_container()
    assistant.add_text("miscallenous text")
    assistant.close_container()


def test_top_bar(assistant: Assistant):
    assistant.open_navbar()
    assistant.add_text("miscallenous text")
    assistant.add_text("other text")
    assistant.close_navbar()


def test_container_multiple_content(assistant: Assistant):
    # with pytest.raises(ValueError):
    with pytest.raises(ValueError) as excinfo:
        assistant.open_container()
        assistant.add_text("test")
        assistant.add_text("test 2")
        assistant.close_container()

    assert "Attempting to place two content in one Container" in str(excinfo.value)


def test_empty_closing(assistant: Assistant):
    with pytest.raises(ValueError) as excinfo:
        assistant.close_row()
    assert "Cannot close Row, no open layout" in str(excinfo.value)


def test_double_navbar(assistant: Assistant):
    with pytest.raises(ValueError) as excinfo:
        assistant.open_navbar()
        assistant.open_navbar()
    assert "Only one navigation may be defined at a time" in str(excinfo.value)


def test_mixed_closing(assistant: Assistant):
    with pytest.raises(ValueError) as excinfo:
        assistant.open_container()
        assistant.close_row()

    assert "Cannot close" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        assistant.open_row()
        assistant.close_container()

    assert "Cannot close" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        assistant.open_navbar()
        assistant.close_container()

    assert "Cannot close" in str(excinfo.value)
