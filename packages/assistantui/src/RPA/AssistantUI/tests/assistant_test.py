import RPA.AssistantUI
from RPA.AssistantUI.dialog_types import Icon

assistant = RPA.AssistantUI.AssistantUI()
assistant.add_heading("Heading test")
assistant.add_text("Test")
assistant.add_link("https://robocorp.com")
assistant.add_icon(Icon.Failure)
assistant.add_icon(Icon.Warning)
assistant.add_icon(Icon.Success)
assistant.add_text_input("txt_input", placeholder="placeholder")
assistant.add_password_input("pw_input")
assistant.add_checkbox("checkbox", "test_checkbox")


assistant.add_image(
    "https://robocorp.com/assets/home/global-purple.svg", width=256, height=256
)

# not implemented yet
"""
assistant.clear_elements()
assistant.add_file()
assistant.add_files()
assistant.add_file_input()
assistant.add_drop_down()
assistant.add_date_input()
assistant.add_radio_buttons()
assistant.add_dialog_next_page_button()
assistant.add_submit_buttons()

assistant.show_dialog()
assistant.wait_dialog()
assistant.wait_all_dialogs()
assistant.close_dialog()
assistant.close_all_dialogs()
assistant.wait_dialogs_as_completed()

"""
assistant.run_dialog()
# FIXME: enable extracting of data from dialog
