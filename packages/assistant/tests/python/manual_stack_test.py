from RPA.Assistant import Assistant
from RPA.Assistant.types import Location


assistant = Assistant()


def open_stack_layout():
    assistant.open_stack(width=512, height=512)
    assistant.open_container(width=72, height=72, location=Location.Center)
    assistant.add_heading("Stack")
    assistant.close_container()

    for value, loc in Location.__members__.items():
        assistant.open_container(
            width=72, height=72, location=loc, background_color="gray500"
        )
        assistant.add_text(value)
        assistant.close_container()

    assistant.close_stack()
    # The elements can go multiline and wider, so the 512 size stack doesn't quite fit
    # into a 512x512 dialog.
    assistant.run_dialog(width=512 + 60, height=512 + 60)


if __name__ == "__main__":
    open_stack_layout()
