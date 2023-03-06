import pytest
from RPA.Assistant import Assistant
from RPA.Assistant.types import Icon, Location


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


def test_column(assistant: Assistant):
    assistant.open_column()
    assistant.add_text("miscallenous text")
    assistant.close_column()


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


def test_center_without_absolute_dimensions(assistant: Assistant):
    with pytest.raises(ValueError) as excinfo:
        assistant.open_stack(width=512, height=512)
        assistant.open_container(location=Location.Center)

    assert "Cannot determine centered position without static width and height" in str(
        excinfo.value
    )


def manual(assistant: Assistant):
    def print_controls():
        print(assistant._client.page.controls)

    assistant.open_navbar("nav")
    assistant.add_icon(Icon.Failure)
    assistant.add_button("test_button", print, "test")
    assistant.add_button("test_button", print, "test")
    assistant.add_button("print_controls", print_controls)
    assistant.add_button("clear dialog", assistant.clear_dialog)
    assistant.add_icon(Icon.Success)
    assistant.close_navbar()
    for i in range(5):

        # assistant.open_stack()

        assistant.open_container(40, 0, background_color="red500")
        assistant.open_row()

        assistant.open_stack()
        assistant.add_heading("column 1")
        assistant.open_container(left=0)
        assistant.add_text("asd")
        assistant.close_container()
        assistant.open_container(left=100, background_color="green500")
        assistant.add_text("testing 1")
        assistant.close_container()
        assistant.open_container(left=5, top=20, background_color="blue500")
        assistant.add_text("testing 2")
        assistant.close_container()
        assistant.close_stack()

        assistant.open_column()
        assistant.add_heading("column 2")
        assistant.add_text("testing 3")
        assistant.add_text("testing 4")
        assistant.close_column()
        assistant.close_row()
        assistant.close_container()

        # assistant.close_stack()
    assistant.run_dialog()


if __name__ == "__main__":
    manual(Assistant())
