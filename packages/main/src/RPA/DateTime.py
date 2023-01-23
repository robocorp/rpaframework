from datetime import date as datetime_date

import logging
from typing import Union, List

import pendulum as pdl
from pendulum.parsing.exceptions import ParserError
from pendulum.datetime import DateTime as PendulumDateTime
from pendulum import timezone

from robot.api.deco import keyword, library
import holidays

parsing_error_message = """Could not parse date '%s'.

You can use `Create Datetime` keyword to construct valid
date object by giving datetime as string and corresponding
date format. See https://pendulum.eustace.io/docs/#tokens for
valid tokens for the date format.
"""

DTFormat = Union[str, datetime_date, PendulumDateTime]


@library(scope="GLOBAL", doc_format="REST")
class DateTime:
    """Library for handling different operations for date and time
    handling especially in business days and holiday contexts.

    Utilizing pendulum and holidays packages.

    Library is by default using days from Monday to Friday as business
    days, but that can be changed by giving list of weekdays to
    ``Set Business Days`` keyword. A weekday is given as a integer, the
    0 for Sunday and 6 for Saturday.

    Some dates containing for example month names in English (en), but the
    locale of the library can be changed with keyword ``Set Locale`` or
    for specific keyword if that has a ``locale`` parameter.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.BUSINESS_DAYS = [1, 2, 3, 4, 5]  # Monday - Friday

    @keyword
    def set_locale(self, locale_name: str):
        previous = pdl.get_locale()
        pdl.set_locale(locale_name)
        return previous

    @keyword
    def set_business_days(self, days: List[int]) -> List:
        previous = self.BUSINESS_DAYS
        self.BUSINESS_DAYS = days
        return previous

    @keyword
    def time_difference(
        self,
        start_date: DTFormat,
        end_date: DTFormat,
        timezone: str = None,
    ):
        """Compare 2 dates and get the time difference.

        Returned dictionary contains following properties:

            - end_date_is_greater, `True` if end_date is more recent
            than start_date, otherwise `False`
            - days, time difference in days
            - hours, time difference in hours (in addition to the days)
            - minutes, time difference in minutes (in addition to the hours)
            - seconds, time difference in seconds (in addition to the minutes)
        """
        if isinstance(start_date, str):
            start_d = self._parse_datetime_string_to_pendulum_datetime(
                start_date, timezone=timezone
            )
        else:
            start_d = start_date
        if isinstance(end_date, str):
            end_d = self._parse_datetime_string_to_pendulum_datetime(
                end_date, timezone=timezone
            )
        else:
            end_d = end_date

        diff = end_d - start_d
        modifier_for_seconds = 1 if diff.seconds >= 0 else -1
        return {
            "end_date_is_later": end_d > start_d,
            "years": diff.years,
            "months": diff.months,
            "days": diff.days,
            "hours": diff.hours,
            "minutes": diff.minutes,
            "seconds": diff.seconds
            if abs(diff.seconds) <= 60
            else abs(diff.seconds) % 60 * modifier_for_seconds,
        }

    @keyword
    def create_datetime(
        self,
        date_string: str,
        date_format_in: str = None,
        timezone: str = None,
        date_format_out: str = None,
    ):
        """This keyword tries to construct valid datetime
        object from given date string and its expected date
        format.

        See https://pendulum.eustace.io/docs/#tokens for
        valid tokens for the date format. Tokens are
        used to form correct date_format.

        :param date_string: for example. "22 May 19"
        :param date_format: for example. "DD MMM YY"
        :param timezone: default timezone is "UTC"

        :return: datetime object which can be used
        with `Time Difference` keyword
        """
        result = None
        if date_format_in:
            result = pdl.from_format(date_string, date_format_in, tz=timezone)
        else:
            result = self._parse_datetime_string_to_pendulum_datetime(
                date_string, timezone=timezone
            )
        return result.format(date_format_out) if date_format_out else result

    @keyword
    def time_now(self, timezone: str = None):
        """Return current datetime

        :param timezone: optional, for example. "America/Boston"
        :return: current datetime as an object
        """
        return pdl.now(tz=timezone)

    def _parse_datetime_string_to_pendulum_datetime(
        self, date_string: DTFormat, timezone: str = None
    ):
        arguments = {"text": date_string, "strict": False}
        if timezone:
            arguments["tz"] = timezone
        try:
            result = pdl.parse(**arguments)
            return result
        except ParserError as err:
            raise ValueError(parsing_error_message % date_string) from err

    @keyword
    def time_difference_in_months(
        self,
        start_date: DTFormat,
        end_date: DTFormat,
    ):
        diff = self.time_difference(start_date, end_date)
        diff["months"] += diff["years"] * 12
        return diff

    @keyword
    def return_previous_business_day(
        self,
        given_date: DTFormat,
        country: str = None,
        return_format: str = "YYYY-MM-DD",
        locale: str = None,
    ):
        return self._return_business_day(given_date, country, return_format, locale, -1)

    @keyword
    def return_next_business_day(
        self,
        given_date: DTFormat,
        country: str = None,
        return_format: str = "YYYY-MM-DD",
        locale: str = None,
    ):
        return self._return_business_day(given_date, country, return_format, locale, 1)

    def _return_business_day(
        self,
        given_date: DTFormat,
        country: str = None,
        return_format: str = None,
        locale: str = None,
        direction: int = -1,
    ):
        pass

        if isinstance(given_date, str):
            given_dt = pdl.parse(given_date, strict=False)
        else:
            given_dt = given_date
        previous_dt = given_dt
        while True:
            is_business_day = False
            previous_dt = previous_dt.add(days=direction)
            prev_day = pdl.date(previous_dt.year, previous_dt.month, previous_dt.day)
            if previous_dt.day_of_week in self.BUSINESS_DAYS:
                is_business_day = True
            if country and is_business_day:
                is_business_day = prev_day not in holidays.country_holidays(country)
            if is_business_day:
                break

        if return_format:
            return previous_dt.format(fmt=return_format, locale=locale)
        else:
            return previous_dt

    def add_time_to_date(self):
        """Keyword from original DateTime library

        :raises NotImplementedError: _description_
        """
        raise NotImplementedError

    def add_time_to_time(self):
        """Keyword from original DateTime library

        :raises NotImplementedError: _description_
        """
        raise NotImplementedError

    def convert_date(self):
        """Keyword from original DateTime library

        :raises NotImplementedError: _description_
        """
        raise NotImplementedError

    def convert_time(self):
        """Keyword from original DateTime library

        :raises NotImplementedError: _description_
        """
        raise NotImplementedError

    def get_current_date(self):
        """Keyword from original DateTime library

        :raises NotImplementedError: _description_
        """
        raise NotImplementedError

    def subtract_date_from_date(self):
        """Keyword from original DateTime library

        :raises NotImplementedError: _description_
        """
        raise NotImplementedError

    def substract_time_from_date(self):
        """Keyword from original DateTime library

        :raises NotImplementedError: _description_
        """
        raise NotImplementedError

    def subtract_time_from_time(self):
        """Keyword from original DateTime library

        :raises NotImplementedError: _description_
        """
        raise NotImplementedError

    @keyword
    def first_business_day_of_the_month(self, date: DTFormat, country: str = None):
        if isinstance(date, str):
            given_dt = pdl.parse(date, strict=False)
        else:
            given_dt = date
        year, current_month = given_dt.year, given_dt.month
        day = 2
        for _ in range(32):
            day_to_check = pdl.date(year, current_month, day)
            result = self.return_previous_business_day(
                day_to_check, country=country, return_format=None
            )
            if result.month == current_month:
                return result
            else:
                day += 1

    @keyword
    def last_business_day_of_the_month(self, date: DTFormat, country: str = None):
        if isinstance(date, str):
            given_dt = pdl.parse(date, strict=False)
        else:
            given_dt = date
        year, current_month = given_dt.year, given_dt.month
        day = 1
        for _ in range(32):
            try:
                if day == 1:
                    next_month = given_dt.set(day=1).add(months=1)
                    day_to_check = pdl.date(next_month.year, next_month.month, day)
                    day = 31
                else:
                    day_to_check = pdl.date(year, current_month, day)
                result = self.return_previous_business_day(
                    day_to_check, country=country, return_format=None
                )
                if result.month == current_month:
                    return result
                else:
                    day -= 1
            except ValueError:
                day -= 1

    def order_list_of_datetimes(self, dates: List[DTFormat]) -> List:
        raise NotImplementedError

    @keyword(name="is time ${time1} < ${time2}")
    def _rfw_is_time_before_than(self, time1: DTFormat, time2: DTFormat):
        return self.is_time_before_than(time1, time2)

    @keyword(name="is time ${time1} > ${time2}")
    def _rfw_is_time_after_than(self, time1: DTFormat, time2: DTFormat):
        return not self.is_time_before_than(time1, time2)

    @keyword
    def is_time_before_than(self, time1: DTFormat, time2: DTFormat):
        diff = self.time_difference(time1, time2)
        return diff["end_date_is_later"]
