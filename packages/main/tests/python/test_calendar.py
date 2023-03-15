import pytest
from RPA.Calendar import Calendar


@pytest.fixture
def library():
    return Calendar()


def test_returning_holidays(library):
    holidays = library.return_holidays(2023, "FI")
    for date, holiday_name in holidays.items():
        print(f"{date} is {holiday_name}")
    assert len(holidays) == 15


@pytest.mark.freeze_time("2023-03-09")
def test_set_locale_spanish(library):
    library.set_locale("es")
    now = library.time_now(
        timezone="Europe/Helsinki", return_format="dddd DD MMMM YYYY"
    )
    assert now == "jueves 09 marzo 2023"


@pytest.mark.freeze_time("2023-03-09")
def test_set_locale_english(library):
    library.set_locale("en")
    now = library.time_now(
        timezone="Europe/Helsinki", return_format="dddd DD MMMM YYYY"
    )
    assert now == "Thursday 09 March 2023"
