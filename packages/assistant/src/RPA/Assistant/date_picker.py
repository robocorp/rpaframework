from calendar import monthrange
from datetime import date, datetime

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
from flet.dropdown import Option
from flet.icons import ARROW_BACK_ROUNDED, ARROW_FORWARD_ROUNDED, CALENDAR_MONTH

# FIXME: This doesn't render the components properly so it can't be used right now
class DatePicker(UserControl):
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
        self.pb.value = Text(self.selected_date)
        self.update()

    def render_day_picker(self):
        element = []
        current_row = []
        number_of_days = monthrange(self.selected_year, self.selected_month)[1]
        for day in range(number_of_days):
            if day % 7 == 0 and day != 0:
                # element.append(PopupMenuItem(content=Row(current_row, alignment=MainAxisAlignment.SPACE_BETWEEN)))
                # self.body_element[0].content = Row(current_row, alignment=MainAxisAlignment.SPACE_BETWEEN)
                current_row = []
            else:
                current_row.append(
                    Container(content=Text(day + 1), on_click=self._select_day)
                )
        self.body_element[0].content = Row(
            [Container(Text("el"))], alignment=MainAxisAlignment.SPACE_BETWEEN
        )
        # self.body_element = element
        self.update()

    def __init__(self):
        # initialise default values
        self.selected_year = datetime.now().year
        self.selected_month = datetime.now().month
        self.selected_day = datetime.now().day
        self.selected_date = None
        self.months_list = (
            ("Jan", "Feb", "Mar", "Apr"),
            ("May", "Jun", "Jul", "Aug"),
            ("Sep", "Oct", "Nov", "Dec"),
        )
        self.header_element = [
            Container(content=Icon(ARROW_BACK_ROUNDED), on_click=self._year_decrement),
            Text(self.selected_year),
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
        super().__init__(self)

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
