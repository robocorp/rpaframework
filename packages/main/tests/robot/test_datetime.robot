*** Settings ***
Library     RPA.DateTime
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

Time difference in months
    ${diff}=    Time difference in months    2022-05-21T22:00:00    2023-05-21T22:00:00
    Should Be Equal As Integers    ${diff}[months]    12
    ${diff}=    Time difference in months    2022-05-21T22:00:00    2023-08-21T22:00:00
    Should Be Equal As Integers    ${diff}[months]    15

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
    ${diff}=    Time Difference    14:30    12:01
    &{expected}=    Get Default Difference Dict
    Set To Dictionary    ${expected}    end_date_is_later=${FALSE}    hours=${-2}    minutes=${-29}
    Dictionaries Should Be Equal    ${diff}    ${expected}

Test Time difference Expecting Positive Difference
    ${diff}=    Time Difference    14:30    14:32
    &{expected}=    Get Default Difference Dict
    Set To Dictionary    ${expected}    hours=${0}    minutes=${2}
    Dictionaries Should Be Equal    ${diff}    ${expected}

Test Time is not later with greater than character
    ${is_it}=    Is Time 13:30 > 14:00
    Should Not Be True    ${is_it}

Test Time is later with greater than character
    ${is_it}=    Is Time 23:30 > 14:00
    Should Be True    ${is_it}

Test Time is before with smaller than character
    ${is_it}=    Is Time 13:30 < 14:00
    Should Be True    ${is_it}

Test Time is not before with smaller than character
    ${is_it}=    Is Time 19:30 < 14:00
    Should Not Be True    ${is_it}

Test Time is before with smaller than character and variables
    ${first_date}=    Set Variable    04:25
    ${second_date}=    Set Variable    09:01
    ${is_it}=    Is Time ${first_date} < ${second_date}
    Should Be True    ${is_it}

Test Time is not before with smaller than character and variables
    ${first_date}=    Set Variable    21:00
    ${second_date}=    Set Variable    09:01
    ${is_it}=    Is Time ${first_date} < ${second_date}
    Should Not Be True    ${is_it}

Test Time is before using arguments normally
    ${first_date}=    Set Variable    04:25
    ${second_date}=    Set Variable    09:01
    ${is_it}=    Is Time Before Than    ${first_date}    ${second_date}
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


*** Keywords ***
Get Default Difference Dict
    &{dict}=    Create Dictionary    end_date_is_later=${TRUE}    years=${0}
    ...    months=${0}    days=${0}    hours=${0}    minutes=${0}    seconds=${0}
    RETURN    ${dict}
