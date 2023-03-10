from datetime import date as datetime_date
import logging
from typing import Union, List, Dict, Optional

import pendulum as pdl
from pendulum.parsing.exceptions import ParserError
from pendulum.datetime import DateTime as PendulumDateTime

from robot.api.deco import keyword, library
import holidays

parsing_error_message = """Could not parse date '%s'.

You can use `Create Time` keyword to construct valid
calendar object by giving date and time as string in corresponding
date format. See https://pendulum.eustace.io/docs/#tokens for
valid tokens for the date format.
"""

DTFormat = Union[str, datetime_date, PendulumDateTime]


@library(scope="GLOBAL", doc_format="REST")
class Calendar:
    """Library for handling different operations for date and time
    handling especially in business days and holiday contexts.

    Utilizing  `pendulum <https://pypi.org/project/pendulum/>`_ and
    `holidays <https://pypi.org/project/holidays/>`_ packages.

    Library is by default using days from Monday to Friday as business
    days, but that can be changed by giving list of weekdays to
    ``Set Business Days`` keyword. A weekday is given as a integer, the
    0 for Sunday and 6 for Saturday.

    Common country holidays are respected when getting next and previous
    business days, but custom holidays can be added into consideration
    using keyword ``Add Custom Holidays`` keyword.

    Some dates containing for example month names are in English (en), but
    the locale of the library can be changed with keyword ``Set Locale`` or
    for specific keyword if that has a ``locale`` parameter.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.BUSINESS_DAYS = [1, 2, 3, 4, 5]  # Monday - Friday
        self.custom_holidays = holidays.HolidayBase()

    @keyword
    def set_locale(self, locale_name: str) -> str:
        """Set locale globally for the library

        :param locale_name: name of the locale
        :return: name of the previous locale

        Python example.

        .. code-block:: python

            library = Calendar()
            library.set_locale("es")
            now = library.time_now(return_format="dddd DD MMMM YYYY")
            # now == "jueves 09 marzo 2023"
            library.set_locale("en")
            now = library.time_now(return_format="dddd DD MMMM YYYY")
            # now == "Thursday 09 March 2023"

        Robot Framework example.

        .. code-block:: robotframework

            Set Locale   es
            ${now}=  Time Now  return_format=dddd DD MMMM YYYY
            # ${now} == "jueves 09 marzo 2023"
            Set Locale   en
            ${now}=  Time Now  return_format=dddd DD MMMM YYYY
            # ${now} == "Thursday 09 March 2023"

        """
        previous = pdl.get_locale()
        pdl.set_locale(locale_name)
        return previous

    @keyword
    def reset_custom_holidays(self) -> None:
        """Reset custom holiday list into empty list."""
        self.custom_holidays = holidays.HolidayBase()

    @keyword
    def add_custom_holidays(self, days: Union[DTFormat, List[DTFormat]]) -> List:
        """Add a day or list of days which are considered as holidays
        in addition to country specific holidays when calculating

        :param days: string or list of dates to consider as holidays
        :return: list of current custom holidays

        Python example.

        .. code-block:: python

            library = Calendar()
            custom_holidays = library.add_custom_holidays("2023-03-08")
            # custom_holidays == ["2023-03-08"]
            custom_holidays = library.add_custom_holidays([
                "2023-03-09", "2023-03-10"
            ])
            # custom_holidays == ["2023-03-08", "2023-03-09", "2023-03-10"]

        Robot Framework example.

        .. code-block:: robotframework

            @{custom_holidays}=   Add Custom Holidays   2023-03-08
            # ${custom_holidays} == ["2023-03-08"]
            @{more_holidays}=   Create List   2023-03-09   2023-03-10
            @{custom_holidays}=   Add Custom Holidays   ${more_holidays}
            # ${custom_holidays} == ["2023-03-08", "2023-03-09", "2023-03-10"]

        """
        if isinstance(days, str):
            self.custom_holidays.append(days.split(","))
        else:
            self.custom_holidays.append(days)
        return self.custom_holidays

    @keyword
    def set_business_days(self, days: List[int]) -> List:
        """Set weekdays which are considered as business days
        for calculating previous and next business day.

        :param days: list of integers denoting weekdays
        :return: previous list of weekdays

        Python example.

        .. code-block:: python

            # set 4 day work week
            previous = Calendar().set_business_days([1,2,3,4])
            # previous == [1,2,3,4,5]

        Robot Framework example.

        .. code-block:: robotframework

            @{4days}=   Create List   1  2  3  4
            @{previous}=    Set Business Days  ${days}
            # ${previous} == [1,2,3,4,5]

        """
        previous = self.BUSINESS_DAYS
        self.BUSINESS_DAYS = days
        return previous

    @keyword
    def time_difference(
        self,
        start_date: Union[DTFormat, str],
        end_date: Union[DTFormat, str],
        start_timezone: Optional[str] = None,
        end_timezone: Optional[str] = None,
    ) -> Dict:
        """Compare 2 dates and get the time difference.

        Returned dictionary contains following properties:

            - end_date_is_later, `True` if end_date is more recent
              than start_date, otherwise `False`
            - years, time difference in years
            - months, time difference in months
            - days, time difference in days
            - hours, time difference in hours (in addition to the days)
            - minutes, time difference in minutes (in addition to the hours)
            - seconds, time difference in seconds (in addition to the minutes)

        :param start_date: starting date for the comparison
        :param end_date: ending date for the comparison
        :param start_timezone: timezone for the starting date, defaults to None
        :param end_timezone: timezone for the ending date, defaults to None
        :return: dictionary containing comparison result

        Python example.

        .. code-block:: python

            diff = Calendar().time_difference(
                "1975-05-22T18:00:00",
                "1975-05-22T22:45:30"
            )
            # diff['end_date_is_later'] == True
            # diff['days'] == 0
            # diff['hours'] == 4
            # diff['minutes'] == 45
            # diff['seconds'] == 30

        Robot Framework example.

        .. code-block:: robotframework

            &{diff}=    Time Difference  1975-05-22T18:00:00  1975-05-22T22:45:30
            # ${diff}[end_date_is_later] == True
            # ${diff}[days] == 0
            # ${diff}[hours] == 4
            # ${diff}[minutes] == 45
            # ${diff}[seconds] == 30

        """

        if isinstance(start_date, str):
            start_d = self._parse_datetime_string_to_pendulum_datetime(
                start_date, timezone=start_timezone
            )
        else:
            start_d = start_date
        if isinstance(end_date, str):
            end_d = self._parse_datetime_string_to_pendulum_datetime(
                end_date, timezone=end_timezone
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
    def create_time(
        self,
        date_string: str,
        date_format_in: Optional[str] = None,
        timezone: Optional[str] = None,
        date_format_out: Optional[str] = None,
    ) -> Union[PendulumDateTime, str]:
        """This keyword tries to construct valid calendar
        instance from given date string and its expected date
        format.

        See https://pendulum.eustace.io/docs/#tokens for
        valid tokens for the date format. Tokens are
        used to form correct date and time format.

        :param date_string: for example. "22 May 19"
        :param date_format_in: for example. "DD MMM YY"
        :param timezone: default timezone is "UTC"
        :param date_format_out: for example. "DD-MM-YY"
        :return: set datetime as an object or string
         if `date_format_out` has been set

        Python example.

        .. code-block:: python

            date = Calendar().create_time(
                "22 May 19",
                "DD MMM YY"
            )

        Robot Framework example.

        .. code-block:: robotframework

            ${date}=  Create Time
            ...  22 May 19
            ...  DD MMM YY

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
    def time_now(
        self,
        timezone: Optional[str] = None,
        return_format: str = "YYYY-MM-DD",
    ) -> PendulumDateTime:
        """Return current date and time

        :param timezone: optional, for example. "America/Boston"
        :param return_format: dates can be formatted for the resulting
         list, defaults to "YYYY-MM-DD"
        :return: current datetime as an object

        Python example.

        .. code-block:: python

            now = Calendar().time_now("Europe/Helsinki")

        Robot Framework example.

        .. code-block:: robotframework

            ${now}=  Time Now   Europe/Helsinki
        """
        now = pdl.now(tz=timezone)
        if return_format:
            now = now.format(return_format)
        return now

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
        start_timezone: Optional[str] = None,
        end_timezone: Optional[str] = None,
    ):
        """Return time difference of dates in months.

        :param start_date: the start date
        :param end_date: the end date
        :param start_timezone: timezone for the start date,
         defaults to None
        :param end_timezone: timezone for the end date,
         defaults to None
        :return: difference in months

        Python example.

        .. code-block:: python

            diff = Calendar().time_difference_in_months(
                "2022-05-21T22:00:00",
                "2023-08-21T22:00:00"
            )
            # diff == 15

        Robot Framework example.

        .. code-block:: robotframework

            ${diff}=  Time Difference In Months
            ...  2022-05-21T22:00:00
            ...  2023-08-21T22:00:00
            # ${diff} == 15

        """
        start_date_dt = self.create_time(start_date, timezone=start_timezone)
        end_date_dt = self.create_time(end_date, timezone=end_timezone)
        return end_date_dt.diff(start_date_dt).in_months()

    @keyword
    def time_difference_in_days(
        self,
        start_date: DTFormat,
        end_date: DTFormat,
        start_timezone: Optional[str] = None,
        end_timezone: Optional[str] = None,
    ):
        """Return the time difference of dates in days.

        :param start_date: the start date
        :param end_date: the end date
        :param start_timezone: timezone for the start date,
         defaults to None
        :param end_timezone: timezone for the end date,
         defaults to None
        :return: difference in days

        Python example.

        .. code-block:: python

            diff = Calendar().time_difference_in_days(
                "2023-05-21",
                "2023-05-29"
            )
            # diff == 8

        Robot Framework example.

        .. code-block:: robotframework

            ${diff}=  Time Difference In Days
            ...  2023-05-21
            ...  2023-05-29
            # ${diff} == 8

        """
        start_date_dt = self.create_time(start_date, timezone=start_timezone)
        end_date_dt = self.create_time(end_date, timezone=end_timezone)
        return end_date_dt.diff(start_date_dt).in_days()

    @keyword
    def time_difference_in_hours(
        self,
        start_date: DTFormat,
        end_date: DTFormat,
        start_timezone: Optional[str] = None,
        end_timezone: Optional[str] = None,
    ):
        """Return the time difference of dates in hours.

        :param start_date: the start date
        :param end_date: the end date
        :param start_timezone: timezone for the start date,
         defaults to None
        :param end_timezone: timezone for the end date,
         defaults to None
        :return: difference in hours

        Python example.

        .. code-block:: python

            diff = Calendar().time_difference_in_hours(
                "2023-08-21T22:00:00",
                "2023-08-22T04:00:00"
            )
            # diff == 6

        Robot Framework example.

        .. code-block:: robotframework

            ${diff}=  Time Difference In Hours
            ...  2023-08-21T22:00:00
            ...  2023-08-22T04:00:00
            # ${diff} == 6

        """
        start_date_dt = self.create_time(start_date, timezone=start_timezone)
        end_date_dt = self.create_time(end_date, timezone=end_timezone)
        return end_date_dt.diff(start_date_dt).in_hours()

    @keyword
    def time_difference_in_minutes(
        self,
        start_date: DTFormat,
        end_date: DTFormat,
        start_timezone: Optional[str] = None,
        end_timezone: Optional[str] = None,
    ):
        """Return the time difference of dates in minutes.

        :param start_date: the start date
        :param end_date: the end date
        :param start_timezone: timezone for the start date,
         defaults to None
        :param end_timezone: timezone for the end date,
         defaults to None
        :return: difference in minutes

        Python example.

        .. code-block:: python

            diff = Calendar().time_difference_in_minutes(
                "12:30",
                "16:35"
            )
            # diff == 245

        Robot Framework example.

        .. code-block:: robotframework

            ${diff}=  Time Difference In Minutes
            ...  12:30
            ...  16:35
            # ${diff} == 245
        """
        start_date_dt = self.create_time(start_date, timezone=start_timezone)
        end_date_dt = self.create_time(end_date, timezone=end_timezone)
        return end_date_dt.diff(start_date_dt).in_minutes()

    @keyword
    def time_difference_between_timezones(
        self,
        start_timezone: str,
        end_timezone: str,
    ):
        """Return the hour difference between timezones.

        :param start_timezone: first timezone
        :param end_timezone: second timezone
        :return: hour difference between the timezones

        Python example.

        .. code-block:: python

            diff = Calendar().time_difference_between_timezones(
                "America/New_York",
                "Europe/Helsinki"
            )
            # diff == 7

        Robot Framework example.

        .. code-block:: robotframework

            ${diff}=  Time Difference Between Timezones
            ...  America/New_York
            ...  Europe/Helsinki
            # ${diff} == 7

        """
        start_date_dt = pdl.datetime(2023, 1, 1, tz=start_timezone)
        end_date_dt = pdl.datetime(2023, 1, 1, tz=end_timezone)
        return end_date_dt.diff(start_date_dt).in_hours()

    @keyword
    def return_previous_business_day(
        self,
        date: DTFormat,
        country: Optional[str] = None,
        return_format: str = "YYYY-MM-DD",
        locale: Optional[str] = None,
    ):
        """Return the previous business day.

        :param date: day of origin
        :param country: country code, default `None`
        :param return_format: dates can be formatted for the resulting
         list, defaults to "YYYY-MM-DD"
        :param locale: name of the locale
        :return: the previous business day from day of origin

        Python example.

        .. code-block:: python

            prev_business = Calendar().return_previous_business_day("2023-01-09", "FI")
            # prev == "2023-01-05"

        Robot Framework example.

        .. code-block:: robotframework

            ${previous_business}=  Return Previous Business Day  2023-01-09  FI
            # ${previous_business} == "2023-01-05"
        """
        return self._return_business_day(date, country, return_format, locale, -1)

    @keyword
    def return_next_business_day(
        self,
        date: DTFormat,
        country: Optional[str] = None,
        return_format: str = "YYYY-MM-DD",
        locale: Optional[str] = None,
    ):
        """Return the next business day.

        :param date: day of origin
        :param country: country code, default `None`
        :param return_format: dates can be formatted for the resulting
         list, defaults to "YYYY-MM-DD"
        :param locale: name of the locale
        :return: the next business day from day of origin

        Python example.

        .. code-block:: python

            next_business = Calendar().return_next_business_day("2023-01-05", "FI")
            # next_business == "2023-01-09"

        Robot Framework example.

        .. code-block:: robotframework

            ${next_business}=  Return Next Business Day  2023-01-05  FI
            # ${next_business} == "2023-01-09"
        """
        return self._return_business_day(date, country, return_format, locale, 1)

    def _return_business_day(
        self,
        given_date: DTFormat,
        country: Optional[str] = None,
        return_format: Optional[str] = None,
        locale: Optional[str] = None,
        direction: int = -1,
    ):
        if isinstance(given_date, str):
            given_dt = pdl.parse(given_date, strict=False)
        else:
            given_dt = given_date
        previous_dt = given_dt
        years = [given_dt.year - 1, given_dt.year, given_dt.year + 1]
        holiday_list = self.return_holidays(years, country)
        while True:
            is_business_day = False
            previous_dt = previous_dt.add(days=direction)
            prev_day = pdl.date(previous_dt.year, previous_dt.month, previous_dt.day)
            if previous_dt.day_of_week in self.BUSINESS_DAYS:
                is_business_day = True
            if country and is_business_day:
                is_business_day = prev_day not in holiday_list
            if is_business_day:
                break

        if return_format:
            return previous_dt.format(fmt=return_format, locale=locale)
        else:
            return previous_dt

    @keyword
    def return_holidays(
        self, years: Union[int, List[int]], country: Optional[str] = None
    ) -> Dict:
        """Return holidays for a country. If country is not given
        then only custom holidays are returned.

        :param years: single year or list of years to list holidays for
        :param country: country code, default `None`
        :return: holidays in a dictionary, the key is the date and the
         value is name of the holiday

        Python example.

        .. code-block:: python

            holidays = Calendar().return_holidays(2023, "FI")
            for date, holiday_name in holidays.items():
                print(f"{date} is {holiday_name}")

        Robot Framework example.

        .. code-block:: robotframework

            &{holidays}=  Return Holidays  2023  FI
            FOR  ${date}  IN   @{holidays.keys()}
                Log To Console   ${date} is ${holidays}[${date}]
            END

        """
        if country:
            holiday_list = holidays.country_holidays(country=country, years=years)
        else:
            holiday_list = holidays.HolidayBase(years=years)
        # add custom holidays
        holiday_list += self.custom_holidays

        return holiday_list

    @keyword
    def first_business_day_of_the_month(
        self, date: DTFormat, country: Optional[str] = None
    ):
        """Return first business day of the month.

        If `country` is not given then holidays are not considered.

        :param date: date describing the month
        :param country: country code, default `None`
        :return: first business of the month

        Python example.

        .. code-block:: python

            first_day = Calendar().first_business_day_of_the_month("2024-06-01")
            # first_day == "2024-06-03"

        Robot Framework example.

        .. code-block:: robotframework

            ${first_day}=  First Business Day of the Month  2024-06-01
            # ${first_day} == "2024-06-03"
        """
        result = None
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
                break
            else:
                day += 1
        return result

    @keyword
    def last_business_day_of_the_month(
        self, date: DTFormat, country: Optional[str] = None
    ):
        """Return last business day of the month.

        If `country` is not given then holidays are not considered.

        :param date: date describing the month
        :param country: country code, default `None`
        :return: last business day of the month

        Python example.

        .. code-block:: python

            last_day = Calendar().last_business_day_of_the_month("2023-12-01")
            # last_day == "2023-12-29"

        Robot Framework example.

        .. code-block:: robotframework

            ${last_day}=  Last Business Day of the Month  2023-12-01
            # ${last_day} == "2023-12-29"

        """
        result = None
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
                    break
                else:
                    day -= 1
            except ValueError:
                day -= 1
        return result

    @keyword
    def sort_list_of_dates(
        self,
        dates: List[DTFormat],
        return_format: Optional[str] = None,
        reverse: bool = False,
    ) -> List:
        """Sort list of dates.

        :param dates: list of dates to sort
        :param return_format: dates can be formatted for the resulting
         list
        :param reverse: `True` return latest to oldest, defaults to `False`,
         which means order from oldest to latest
        :return: list of sorted dates

        Python example.

        .. code-block:: python

            datelist = [
                "2023-07-02 12:02:31",
                "2023-07-03 12:02:35",
                "2023-07-03 12:02:31"
            ]
            sorted = Calendar().sort_list_of_dates(datelist)
            # sorted[0] == "2023-07-03 12:02:35"
            # sorted[-1] == "2023-07-02 12:02:31"
            sorted = Calendar().sort_list_of_dates(datelist, reverse=True)
            # sorted[0] == "2023-07-02 12:02:31"
            # sorted[-1] == "2023-07-03 12:02:35"

        Robot Framework example.

        .. code-block:: robotframework

            @{datelist}=  Create List
            ...   2023-07-02 12:02:31
            ...   2023-07-03 12:02:35
            ...   2023-07-03 12:02:31
            ${sorted}=  Sort List Of Dates   ${datelist}
            # ${sorted}[0] == "2023-07-03 12:02:35"
            # ${sorted}[-1] == "2023-07-02 12:02:31"
            ${sorted}=  Sort List Of Dates   ${datelist}  reverse=True
            # ${sorted}[0] == "2023-07-02 12:02:31"
            # ${sorted}[-1] == "2023-07-03 12:02:35"

        """
        dt_list = [self.create_time(date) for date in dates]
        result = sorted(dt_list, reverse=reverse)
        return [d.format(return_format) for d in result] if return_format else result

    @keyword(name="Compare Times ${time1} < ${time2}")
    def _rfw_compare_time_before(self, time1: DTFormat, time2: DTFormat):
        """Compares given times and returns `True` if `time2`
        is more recent than `time1`.

        :param time1: first time for comparison
        :param time2: second time for comparison
        :return: `True` if `time2` is more recent than `time1`

        Robot Framework example.

        .. code-block:: robotframework

            ${recent}=  Compare Times 2023-03-09 15:50 < 2023-03-09 15:59
            IF  ${recent}
                Log  2023-03-09 15:59 is more recent
            END

        """
        return self.compare_times(time1, time2)

    @keyword(name="Compare Times ${time1} > ${time2}")
    def _rfw_compare_time_after(self, time1: DTFormat, time2: DTFormat):
        """Compares given times and returns `True` if `time1`
        is more recent than `time2`.

        :param time1: first time for comparison
        :param time2: second time for comparison
        :return: `True` if `time1` is more recent than `time2`

        Robot Framework example.

        .. code-block:: robotframework

            ${recent}=  Compare Times 2023-03-09 15:59 > 2023-03-09 15:58
            IF  ${recent}
                Log  2023-03-09 15:59 is more recent
            END

        """
        return not self.compare_times(time1, time2)

    @keyword
    def compare_times(self, time1: DTFormat, time2: DTFormat):
        """Compares given times and returns `True` if `time2`
        is more recent than `time1`.

        :param time1: first time for comparison
        :param time2: second time for comparison
        :return: `True` if `time2` is more recent than `time1`

        Python example.

        .. code-block:: python

            recent = Calendar().compare_times("2023-03-09 13:02", "2023-03-09 13:47")
            if recent:
                print("2023-03-09 13:47 is more recent")

        Robot Framework example.

        .. code-block:: robotframework

            ${recent}=  Compare Times   2023-03-09 13:02   2023-03-09 13:47
            IF  ${recent}
                Log  2023-03-09 13:47 is more recent
            END

        """
        diff = self.time_difference(time1, time2)
        return diff["end_date_is_later"]

    @keyword
    def get_iso_calendar(self, date: DTFormat):
        """Get ISO calendar information for the given date.

        :parameter date: input date
        :return: ISO calendar object containing year, week number and weekday.

        Python example.

        .. code-block:: python

            iso_cal = Calendar().get_iso_calendar("2023-03-09")
            print(iso_cal.year)
            print(iso_cal.week)
            print(iso_cal.weekday)

        Robot Framework example.

        .. code-block:: robotframework

            ${iso_cal}=  Get ISO Calendar  2023-03-09
            ${iso_year}=  Set Variable  ${iso_cal.year}
            ${iso_week}=  Set Variable  ${iso_cal.week}
            ${iso_weekday}=  Set Variable  ${iso_cal.weekday}
        """
        if isinstance(date, str):
            given_dt = pdl.parse(date, strict=False)
        else:
            given_dt = date
        return given_dt.isocalendar()

    @keyword
    def is_the_date_business_day(
        self, date: DTFormat, country: Optional[str] = None
    ) -> bool:
        """Is the date a business day in a country.

        If `country` is not given then holidays are not considered.

        :param date: input date
        :param country: country code, default `None`
        :return: `True` if the day is a business day, `False` if not

        Python example.

        .. code-block:: python

            for day in range(1,32):
                date = f"2023-1-{day}"
                is_business_day = Calendar().is_the_date_business_day(date, "FI")
                if is_business_day:
                    print(f'It is time for the work on {date}')
                else:
                    print(f'It is time to relax on {date}')

        Robot Framework example.

        .. code-block:: robotframework

            FOR  ${day}  IN RANGE  1  32
                ${date}=   Set Variable   2023-1-${day}
                ${is_business_day}=   Is the date business day  ${date}  FI
                IF   ${is_business_day}
                    Log To Console   It is time for the work on ${date}
                ELSE
                    Log To Console   It is time to relax on ${date}
                END
            END
        """
        if isinstance(date, str):
            given_dt = pdl.parse(date, strict=False)
        else:
            given_dt = date
        holiday_list = self.return_holidays(given_dt.year, country)
        is_business_day = False
        if given_dt.day_of_week in self.BUSINESS_DAYS:
            is_business_day = True
        if country and is_business_day:
            is_business_day = given_dt not in holiday_list
        return is_business_day

    @keyword(name="Is the ${date} Business Day in ${country}")
    def _rfw_is_the_day_business_day(self, date: DTFormat, country: str):
        """Is the date a business day in a country.

        :param date_in: input date
        :param country: country code
        :return: `True` if the day is a business day, `False` if not

        Robot Framework example.

        .. code-block:: robotframework

            ${is_business_day}=   Is the 2023-01-02 business day in FI
            IF   ${is_business_day}
                Log To Console   It is time for the work
            ELSE
                Log To Console   It is time to relax
            END
        """
        return self.is_the_date_business_day(date, country)

    @keyword
    def is_the_date_holiday(self, date: DTFormat, country: Optional[str] = None):
        """Is the date a holiday in a country.
        If `country` is not given then checks only if date is in custom holiday list.

        :param date_in: input date
        :param country: country code, default `None`
        :return: `True` if the day is a holiday, `False` if not

        Python example.

        .. code-block:: python

            is_holiday = Calendar().is_the_date_holiday("2022-12-26", "FI")
            if is_holiday:
                print('Time to relax')
            else:
                print('Time for the work')

        Robot Framework example.

        .. code-block:: robotframework

            ${is_holiday}=   Is the date holiday   2022-12-26   FI
            IF   ${is_holiday}
                Log  Time to relax
            ELSE
                Log  Time for the work
            END

        """
        if isinstance(date, str):
            given_dt = pdl.parse(date, strict=False)
        else:
            given_dt = date
        holiday_list = self.return_holidays(given_dt.year, country)
        return given_dt in holiday_list

    @keyword(name="Is the ${date} Holiday in ${country}")
    def _rfw_is_the_day_holiday(self, date: DTFormat, country: str):
        """Is the date a holiday in a country.

        :param date_in: input date
        :param country: country code
        :return: `True` if the day is a holiday, `False` if not

        Robot Framework example.

        .. code-block:: robotframework

            ${is_it}=   Is the 2022-12-26 holiday in FI
            IF   ${is_holiday}
                Log  Time to relax
            ELSE
                Log  Time for the work
            END

        """
        return self.is_the_date_holiday(date, country)
