from time import sleep
import RPA.Assistant
from RPA.Assistant.types import Icon, VerticalLocation, WindowLocation


assistant = RPA.Assistant.Assistant()


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


import re


def validate_email(email):
    # E-mail specification is complicated, this matches that the e-mail has
    # at least one character before and after the @ sign, and at least one
    # character after the dot.
    regex = r"^.+@.+\..+"
    valid = re.match(regex, email)
    if not valid:
        return "Invalid email address"


def sleepy_print(arg):
    """used for testing is the button disabling working"""
    sleep(1)
    print(arg)


def manual():
    assistant.add_date_input("my_date", label="My Date")
    assistant.add_button(
        "python button",
        sleepy_print,
        "sleepy print output (should appear after ~1s sleep)",
    )
    assistant.add_button("robot button", "Log", "asd")
    assistant.add_next_ui_button("different form button", next_ui)
    assistant.add_heading("Heading test")
    assistant.add_text("Test")
    assistant.add_link("https://robocorp.com")
    assistant.add_icon(Icon.Failure)
    assistant.add_icon(Icon.Warning)
    assistant.add_icon(Icon.Success)

    assistant.add_flet_icon(icon="check_circle_rounded", color="FF00FF", size=48)

    assistant.add_text_input(
        "txt_input",
        placeholder="field with validation",
        required=True,
        validation=length_greater_3,
    )
    assistant.add_password_input("pw_input")
    assistant.add_checkbox("checkbox", "test_checkbox")
    assistant.add_file_input("file", file_type="pdf,png,jpg")
    assistant.add_hidden_input("Hidden", "value")
    assistant.add_text("Percentage slider")
    assistant.add_slider(
        name="percentage",
        slider_min=0,
        slider_max=100,
        steps=100,
        default=80,
        decimals=1,
    )
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
    assistant.add_text("List python files")
    assistant.add_files("src/**/*.py")
    assistant.add_image(
        "https://robocorp.com/assets/home/global-purple.svg", width=256, height=256
    )
    assistant.add_submit_buttons(["second submit"], "second submit")

    # assistant.clear_dialog()
    # assistant.add_icon(Icon.Failure)
    assistant.add_button(
        "clear elements",
        lambda: assistant.clear_dialog(),
        location=VerticalLocation.Right,
    )

    assistant.add_text_input(
        "txt_input_2", placeholder="placeholder", minimum_rows=2, maximum_rows=3
    )
    assistant.add_text_input("email", label="Email", validation=validate_email)

    results = assistant.run_dialog(location=WindowLocation.TopLeft, timeout=180)
    print(results)


if __name__ == "__main__":
    manual()
