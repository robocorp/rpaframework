import pytest
from RPA.Assistant import Assistant


def test_rows(assistant: Assistant):
    assistant.open_row()
    print(assistant._client._container_stack)
    assistant.add_date_input("my_date", label="My Date")
    assistant.add_text(
        "python button",
    )
    print(assistant._client._container_stack)
    assistant.close_row()
    print(assistant._client._container_stack)


def test_container_one_content(assistant: Assistant):
    # with pytest.raises(ValueError):
    with pytest.raises(ValueError) as excinfo:
        assistant.open_container()
        assistant.add_text("test")
        assistant.add_text("test 2")
        assistant.close_container()

    assert "Attempting to place two content in one Container" in str(excinfo.value)


def test_empty_closing(assistant: Assistant):
    with pytest.raises(ValueError):
        assistant.close_row()


def test_mixed_closing(assistant: Assistant):
    with pytest.raises(ValueError) as excinfo:
        assistant.open_container()
        assistant.close_row()

    assert "Cannot close" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        assistant.open_row()
        assistant.close_container()

    assert "Cannot close" in str(excinfo.value)
