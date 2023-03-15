*** Settings ***
Library     RPA.Calendar
Library     Collections


*** Variables ***
${RESOURCES}    ${CURDIR}${/}..${/}resources


*** Tasks ***
Setting Locale
    ${previous}=    Set Locale    de
    Should Be Equal As Strings    en    ${previous}
    ${previous}=    Set Locale    en
    Should Be Equal As Strings    de    ${previous}

Setting Business Days
    @{default_business_days}=    Evaluate    [1,2,3,4,5]
    @{new_business_days}=    Evaluate    [1,2]
    @{previous}=    Set Business Days    ${new_business_days}
    Lists Should Be Equal    ${previous}    ${default_business_days}
    @{previous}=    Set Business Days    ${default_business_days}
    Lists Should Be Equal    ${previous}    ${new_business_days}

Time difference when dates are in string format
    ${diff}=    Time Difference    1975-05-21T22:00:00    1975-05-22T22:00:00
    &{expected_diff}=    Get Default Difference Dict
    Set To Dictionary    ${expected_diff}    days=${1}
    Dictionaries Should Be Equal    ${diff}    ${expected_diff}
    ${diff}=    Time Difference    1975-05-23T22:00:00    1975-05-22T22:00:00
    &{expected_diff}=    Get Default Difference Dict
    Set To Dictionary    ${expected_diff}    days=${-1}    end_date_is_later=${FALSE}
    Dictionaries Should Be Equal    ${diff}    ${expected_diff}

Time difference when dates are in Python datetime format
    ${start}=    Evaluate    datetime.datetime(1975, 5, 21).strftime('%c')
    ${end}=    Evaluate    datetime.datetime(1975, 5, 22).strftime('%c')
    ${diff}=    Time Difference    ${start}    ${end}
    &{expected_diff}=    Get Default Difference Dict
    Set To Dictionary    ${expected_diff}    days=${1}
    Dictionaries Should Be Equal    ${diff}    ${expected_diff}

Test time difference in months
    ${diff}=    Time difference in months    2022-05-21T22:00:00    2023-08-21T22:00:00
    Should Be Equal As Integers    ${diff}    15

Test time difference in days
    ${diff}=    Time difference in days    2023-05-21    2023-05-29
    Should Be Equal As Integers    ${diff}    8

Test time difference in hours
    ${diff}=    Time difference in hours    2023-08-21T22:00:00    2023-08-22T04:00:00
    Should Be Equal As Integers    ${diff}    6

Test time difference in minutes
    ${diff}=    Time difference in minutes    12:30    16:35
    Should Be Equal As Integers    ${diff}    245

Test time difference in hours between London and Helsinki
    ${diff}=    Time difference in hours
    ...    2023-01-21T12:00:00
    ...    2023-01-21T12:00:00
    ...    Europe/London
    ...    Europe/Helsinki
    Should Be Equal As Integers    ${diff}    2

Test time difference in hours between New York and Helsinki
    ${diff}=    Time difference in hours
    ...    2023-06-21T12:00:00
    ...    2023-06-21T12:00:00
    ...    Europe/London
    ...    America/New_York
    Should Be Equal As Integers    ${diff}    5

Test getting time difference of timezones
    ${diff}=    Time difference between timezones
    ...    America/New_York
    ...    Europe/Helsinki
    Should Be Equal As Integers    ${diff}    7

Test Getting Previous business day for Finland
    ${previous}=    Return Previous Business Day    2022-11-14    FI
    Should Be Equal As Strings    2022-11-11    ${previous}

Test Getting Previous business day for Finland - Midsummer 2023
    ${previous}=    Return Previous Business Day    2023-06-26    FI
    Should Be Equal As Strings    2023-06-22    ${previous}

Test Getting Previous business day for Finland - New Year 2024
    ${previous}=    Return Previous Business Day    2024-01-01    FI
    Should Be Equal As Strings    2023-12-29    ${previous}

Test Getting Previous business day for Finland With Return Format Set
    ${previous}=    Return Previous Business Day    2022-11-14    FI    return_format=YYYY-MM-DD
    Should Be Equal As Strings    2022-11-11    ${previous}

Test Getting Previous business day for USA - Memorial Day 2023
    ${previous}=    Return Previous Business Day    2023-05-30    US
    Should Be Equal As Strings    2023-05-26    ${previous}

Test Time difference Expecting Negative Difference
    ${diff}=    Time Difference    12:01:25    14:30
    &{expected}=    Get Default Difference Dict
    Set To Dictionary    ${expected}
    ...    end_date_is_later=${TRUE}
    ...    hours=${2}
    ...    minutes=${28}
    ...    seconds=${35}
    Dictionaries Should Be Equal    ${diff}    ${expected}

Test Time difference Expecting Positive Difference
    ${diff}=    Time Difference    14:30    14:32
    &{expected}=    Get Default Difference Dict
    Set To Dictionary    ${expected}    hours=${0}    minutes=${2}
    Dictionaries Should Be Equal    ${diff}    ${expected}

Test Time is not later with greater than character
    ${is_it}=    Compare Times 13:30 > 14:00
    Should Not Be True    ${is_it}

Test Time is later with greater than character
    ${is_it}=    Compare Times 23:30 > 14:00
    Should Be True    ${is_it}

Test Time is before with smaller than character
    ${is_it}=    Compare Times 13:30 < 14:00
    Should Be True    ${is_it}

Test Time is not before with smaller than character
    ${is_it}=    Compare Times 19:30 < 14:00
    Should Not Be True    ${is_it}

Test Time is before with smaller than character and variables
    ${first_date}=    Set Variable    04:25
    ${second_date}=    Set Variable    09:01
    ${is_it}=    Compare Times ${first_date} < ${second_date}
    Should Be True    ${is_it}

Test longer formatted time is before with smaller than character and variables
    ${first_date}=    Set Variable    2023-01-23 04:25
    ${second_date}=    Set Variable    2023-01-23 09:01
    ${is_it}=    Compare Times ${first_date} < ${second_date}
    Should Be True    ${is_it}

Test longer formatted time is after with bigger than character
    ${is_it}=    Compare Times 2023-01-23 09:01 > 2023-01-23 04:25
    Should Be True    ${is_it}

Test Time is not before with smaller than character and variables
    ${first_date}=    Set Variable    21:00
    ${second_date}=    Set Variable    09:01
    ${is_it}=    Compare Times ${first_date} < ${second_date}
    Should Not Be True    ${is_it}

Test Time is before using arguments normally
    ${first_date}=    Set Variable    04:25
    ${second_date}=    Set Variable    09:01
    ${is_it}=    Compare Times    ${first_date}    ${second_date}
    Should Be True    ${is_it}

Test Getting First Business Day of the Month - February 2023 Finland
    ${result}=    First Business Day of the Month    2023-02-01    FI
    Should Be Equal As Strings    2023-02-01    ${result}

Test Getting First Business Day of the Month - April 2023 Finland
    ${result}=    First Business Day of the Month    2023-04-01    FI
    Should Be Equal As Strings    2023-04-03    ${result}

Test Getting Last Business Day of the Month - April 2023 Finland
    ${result}=    Last Business Day of the Month    2023-04-01    FI
    Should Be Equal As Strings    2023-04-28    ${result}

Test Getting Last Business Day of the Month - July 2023 US
    ${result}=    Last Business Day of the Month    2023-07-01    US
    Should Be Equal As Strings    2023-07-31    ${result}

Test Getting Last Business Day of the Month - December 2023 US
    ${result}=    Last Business Day of the Month    2023-12-12    US
    Should Be Equal As Strings    2023-12-29    ${result}

Test Getting Next Business Day of the Month - After Christmas 2023 Finland
    ${result}=    Return Next Business Day    2023-12-22    FI
    Should Be Equal As Strings    2023-12-27    ${result}

Test Custom Holidays and Getting Next Business Day
    Add Custom Holidays    2023-03-07
    Add Custom Holidays    2023-03-08
    ${custom}=    Add Custom Holidays    2023-03-09
    ${result}=    Return Next Business Day    2023-03-06    FI
    Should Be Equal As Strings    2023-03-10    ${result}
    ${result}=    Return Next Business Day    2024-03-06    FI
    Should Be Equal As Strings    2024-03-07    ${result}

Test Custom Holidays given in list
    ${holidays}=    Create List    2023-03-07    2023-03-08    2023-03-09
    Add Custom Holidays    ${holidays}
    ${result}=    Return Next Business Day    2023-03-06    FI
    Should Be Equal As Strings    2023-03-10    ${result}

Test Custom Holidays given as command separated string
    Add Custom Holidays    2023-03-07,2023-03-08,2023-03-09
    ${result}=    Return Next Business Day    2023-03-06    FI
    Should Be Equal As Strings    2023-03-10    ${result}

Test ordering list of dates
    @{dates}=    Create List
    ...    2023-07-03
    ...    2024-04-03
    ...    2023-02-05
    ...    2021-04-03
    ...    2023-04-03
    ...    2023-07-05
    ...    2023-01-01
    @{expected}=    Create List
    ...    2021-04-03
    ...    2023-01-01
    ...    2023-02-05
    ...    2023-04-03
    ...    2023-07-03
    ...    2023-07-05
    ...    2024-04-03
    ${result}=    Sort List Of Dates    ${dates}    return_format=YYYY-MM-DD
    Lists Should Be Equal    ${result}    ${expected}

Test ordering list of dates latest first
    @{dates}=    Create List
    ...    2023-07-05 14:20
    ...    2023-02-05
    ...    2023-04-03
    ...    2023-07-05 14:49
    ...    2023-01-01
    @{expected}=    Create List
    ...    2023-07-05 14:49
    ...    2023-07-05 14:20
    ...    2023-04-03 00:00
    ...    2023-02-05 00:00
    ...    2023-01-01 00:00

    ${result}=    Sort List Of Dates    ${dates}    return_format=YYYY-MM-DD HH:mm    reverse=True
    Lists Should Be Equal    ${result}    ${expected}

Test Getting Previous business day when country is not set - Memorial Day 2023
    ${previous}=    Return Previous Business Day    2023-05-30
    Should Be Equal As Strings    2023-05-29    ${previous}

Test Is Finnish Independence Day a business day
    ${business_day}=    Is The Date Business Day    2023-12-06    FI
    Should Not Be True    ${business_day}

Test Is Finnish Independence Day a holiday
    ${holiday}=    Is The Date Holiday    2023-12-06    FI
    Should Be True    ${holiday}

Test helper keyword - is the date business day
    ${business_day}=    Is The 2023-12-05 Business Day in FI
    Should Be True    ${business_day}

Test Getting Holidays
    Reset Custom Holidays
    &{holidays}=    Return Holidays    2023    FI
    FOR    ${date}    IN    @{holidays.keys()}
        Log To Console    ${date} is ${holidays}[${date}]
    END
    ${length}=    Get Length    ${holidays}
    Should Be Equal As Integers    ${length}    15

Test Time Now
    ${freezer} =    Evaluate    freezegun.freeze_time("2023-03-09")
    ...     modules=freezegun
    Evaluate    $freezer.start()

    Set Locale    es
    ${now}=    Time Now    timezone=Europe/Helsinki   return_format=dddd DD MMMM YYYY
    Should Be Equal As Strings    ${now}    jueves 09 marzo 2023

    Set Locale    en
    ${now}=    Time Now    timezone=Europe/Helsinki   return_format=dddd DD MMMM YYYY
    Should Be Equal As Strings    ${now}    Thursday 09 March 2023

    [Teardown]      Evaluate    $freezer.stop()


*** Keywords ***
Get Default Difference Dict
    &{dict}=    Create Dictionary    end_date_is_later=${TRUE}    years=${0}
    ...    months=${0}    days=${0}    hours=${0}    minutes=${0}    seconds=${0}
    RETURN    ${dict}
