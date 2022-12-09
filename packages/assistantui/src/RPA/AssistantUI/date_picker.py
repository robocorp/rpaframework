from flet import Dropdown, UserControl, Container, Row, Icon
from flet.dropdown import Option
from flet.icons import CALENDAR_MONTH
from datetime import datetime


class DatePicker(UserControl):
    def __init__(self):
        self.day_dropdown = Dropdown(
            options=[Option(day) for day in range(1, 32)],
            width=50,
        )

        self.month_dropdown = Dropdown(
            options=[Option(month) for month in range(1, 13)],
            width=50,
        )

        self.year_dropdown = Dropdown(
            options=[Option(year) for year in range(1900, 2100)],
            width=100,
        )

        self.view = Container(
            content=Row(
                [
                    Icon(
                        CALENDAR_MONTH,
                    ),
                    self.day_dropdown,
                    self.month_dropdown,
                    self.year_dropdown,
                ],
                alignment="center",
            ),
            padding=10,
        )

        super().__init__(self)

    def build(self):
        return self.view

    def get_date(self) -> datetime.date:
        date = datetime.date(
            year=int(self.year_dropdown.value),
            month=int(self.month_dropdown.value),
            day=int(self.day_dropdown.value),
        )
        return date
