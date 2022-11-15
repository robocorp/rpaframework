*** Settings ***
Library           RPA.DateTime
Library           Collections

*** Variables ***
${RESOURCES}      ${CURDIR}${/}..${/}resources

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
    Set To Dictionary    ${expected_diff}    days=${-1}    end_date_is_greater=${FALSE}
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

Previous business day
    ${previous}=    Return Previous Business Day    2022-11-14    FI
    Should Be Equal As Strings    2022-11-11T00:00:00+00:00    ${previous}
    ${previous}=    Return Previous Business Day    2022-11-14    FI    return_format=YYYY-MM-DD
    Should Be Equal As Strings    2022-11-11    ${previous}

*** Keywords ***
Get Default Difference Dict
    &{dict}=    Create Dictionary    end_date_is_greater=${TRUE}    years=${0}
    ...    months=${0}    days=${0}    hours=${0}    minutes=${0}    seconds=${0}
    RETURN    ${dict}
