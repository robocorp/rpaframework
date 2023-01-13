from calendar import monthrange
from datetime import date, datetime
from typing import Optional

from flet import (
    Container,
    Icon,
    MainAxisAlignment,
    PopupMenuButton,
    PopupMenuItem,
    Row,
    Text,
    UserControl,
)
from flet.icons import ARROW_BACK_ROUNDED, ARROW_FORWARD_ROUNDED, CALENDAR_MONTH


# FIXME: This widget will be used once it will be capable of rendering the components
#  correctly. (#775)
class DatePicker(UserControl):
    """Date picking widget."""

    def __init__(self, *args, default: Optional[datetime] = None, **kwargs):
        # Set date to provided default or current date.
        default = default or datetime.now()
        self.selected_year = default.year
        self.selected_month = default.month
        self.selected_day = default.day
        self.selected_date = None
        self.months_list = (
            ("Jan", "Feb", "Mar", "Apr"),
            ("May", "Jun", "Jul", "Aug"),
            ("Sep", "Oct", "Nov", "Dec"),
        )
        self.header_element = [
            Container(content=Icon(ARROW_BACK_ROUNDED), on_click=self._year_decrement),
            Text(str(self.selected_year)),
            Container(
                content=Icon(ARROW_FORWARD_ROUNDED), on_click=self._year_increment
            ),
        ]
        self.body_element = []
        for row in self.months_list:
            temp = PopupMenuItem(
                content=Row(
                    [
                        Container(content=Text(i), on_click=self._select_month)
                        for i in row
                    ],
                    alignment=MainAxisAlignment.SPACE_BETWEEN,
                )
            )
            self.body_element.append(temp)

        super().__init__(*args, **kwargs)

    def _year_increment(self, e):
        self.selected_year += 1
        self.header_element[1].value = self.selected_year
        self.update()

    def _year_decrement(self, e):
        self.selected_year -= 1
        self.header_element[1].value = self.selected_year
        self.update()

    def _select_month(self, e):
        selected_month = e.control._Control__previous_children[0].value
        self.selected_month = sum(self.months_list, ()).index(selected_month) + 1
        self.header_element[0].content = None
        self.header_element[2].content = None
        self.header_element[1].value = selected_month
        self.render_day_picker()

    def _select_day(self, e):
        self.selected_day = e.control._Control__previous_children[0].value
        self.selected_date = date(
            year=int(self.selected_year),
            month=int(self.selected_month),
            day=int(self.selected_day),
        )
        self.pb.value = Text(str(self.selected_date))
        self.update()

    def render_day_picker(self):
        element = []
        current_row = []
        number_of_days = monthrange(self.selected_year, self.selected_month)[1]

        def _add_week():
            element.append(
                PopupMenuItem(
                    content=Row(current_row, alignment=MainAxisAlignment.SPACE_BETWEEN)
                )
            )
            current_row.clear()

        for day in range(1, number_of_days + 1):
            current_row.append(
                Container(content=Text(str(day)), on_click=self._select_day)
            )
            if not day % 7:
                # Week as row of days is complete.
                _add_week()

        if current_row:
            _add_week()

        self.body_element = element
        self.update()

    def render(self):
        self.pb = PopupMenuButton(
            icon=CALENDAR_MONTH,
            items=[
                # Top row for year display and selection
                PopupMenuItem(
                    content=Row(
                        self.header_element, alignment=MainAxisAlignment.SPACE_BETWEEN
                    )
                ),
                PopupMenuItem(),  # divider
                *self.body_element,
            ],
        )
        self.view = Container(content=self.pb)

    def build(self):
        self.render()
        return self.view
