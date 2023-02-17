from time import sleep
import RPA.Assistant
from RPA.Assistant.types import Icon, Location
import pytest


pytest.skip("until we have non-blocking assistant UI tests", allow_module_level=True)


def next_ui(results):
    assistant.clear_dialog()
    assistant.add_heading("the 2nd ui")
    assistant.add_text(str(results))
    assistant.add_text_input(
        "txt_input", placeholder="placeholder", validation=length_greater_3
    )
    assistant.add_next_ui_button("the 3rd ui", third_ui)
    assistant.refresh_dialog()


def third_ui(results):
    assistant.clear_dialog()
    assistant.add_heading("the 3rd ui")
    assistant.add_text(str(results))
    assistant.add_text_input(
        "txt_input", placeholder="placeholder", validation=length_greater_3
    )
    assistant.add_next_ui_button("the 2nd ui", next_ui)
    assistant.refresh_dialog()


def length_greater_3(value):
    if len(value) <= 3:
        return "Length should be greater than 3"


def sleepy_print(arg):
    """used for testing is the button disabling working"""
    sleep(1)
    print(arg)


assistant = RPA.Assistant.Assistant()
assistant.add_date_input("my_date", label="My Date")
assistant.add_button(
    "python button", sleepy_print, "sleepy print output (should appear after ~1s sleep)"
)
assistant.add_button("robot button", "Log", "asd")
assistant.add_next_ui_button("different form button", next_ui)
assistant.add_heading("Heading test")
assistant.add_text("Test")
assistant.add_link("https://robocorp.com")
assistant.add_icon(Icon.Failure)
assistant.add_icon(Icon.Warning)
assistant.add_icon(Icon.Success)
assistant.add_text_input(
    "txt_input", placeholder="placeholder", required=True, validation=length_greater_3
)
assistant.add_password_input("pw_input")
assistant.add_checkbox("checkbox", "test_checkbox")
assistant.add_file_input("file", file_type="pdf,png,jpg")
assistant.add_hidden_input("Hidden", "value")
assistant.add_text("Percentage slider")
assistant.add_slider(name="percentage", slider_min=0, slider_max=0, steps=100)
# assistant.add_file(path="/Users/kerkko/Downloads/image.png", label="File")

assistant.add_radio_buttons(
    name="user_type_radio",
    options="Admin,Maintainer,Operator",
    default="Operator",
    label="User type",
)
assistant.add_drop_down(
    name="user_type_dropdown",
    options="Admin,Maintainer,Operator",
    default="Operator",
    label="User type",
)


# assistant.add_dialog_next_page_button("Next page")

assistant.add_text_input("txt_input_2", placeholder="placeholder")
assistant.add_text("List python files")
assistant.add_files("**/*.py")
assistant.add_image(
    "https://robocorp.com/assets/home/global-purple.svg", width=256, height=256
)
assistant.add_submit_buttons(["second submit"], "second submit")

# assistant.clear_dialog()
# assistant.add_icon(Icon.Failure)

results = assistant.ask_user(location=Location.TopLeft, timeout=180)
print(results)
