*** Settings ***
Library           RPA.JSON
Library           OperatingSystem
Library           String
Default Tags      RPA.JSON

*** Variables ***
${RESOURCES}      ${CURDIR}${/}..${/}resources
${CUSTOMERS_JSON}    ${RESOURCES}${/}customers.json
${BIGDATA_JSON}    ${RESOURCES}${/}bigdata.json
${SECRETS_JSON}    ${RESOURCES}${/}secrets.json
${TEMP_RESULT_JSON}    tempresult.json

*** Keywords ***
Test setup for most cases
    ${data}    Load JSON From File    ${SECRETS_JSON}
    Set Task Variable    ${data}

*** Tasks ***
Read JSON and Update Values
    [Documentation]    Testing larger scenario
    ${customers}    Load JSON From File    ${CUSTOMERS_JSON}
    ${customer}    Create Dictionary    name=John Doe    address=Main Road 12
    ${customers}    Add To JSON    ${customers}    $    ${customer}
    ${customers}    Update Value To JSON
    ...    ${customers}
    ...    $.customers[?(@.name='Tim Thompson')].address
    ...    New Location 2
    Save JSON To File    ${customers}    ${TEMP_RESULT_JSON}
    File Should Not Be Empty    ${TEMP_RESULT_JSON}
    ${customers2}    Load JSON From File    ${TEMP_RESULT_JSON}
    Should Be Equal    ${customers}    ${customers2}
    [Teardown]    Remove File    ${TEMP_RESULT_JSON}

Delete values from JSON
    [Setup]    Test setup for most cases
    Should Contain    ${data}[windows]    domain
    ${data}    Delete from JSON    ${data}    $.windows.domain
    Should Not Contain    ${data}[windows]    domain
    ${data}    Delete from JSON    ${data}    $.windows
    Should Not Contain    ${data}    windows

Get value from JSON
    [Setup]    Test setup for most cases
    ${item}    Get Value from JSON    ${data}    $.swaglabs
    Should Contain    ${item}    username
    Should Contain    ${item}    password

Get value from JSON too many matches
    [Setup]    Test setup for most cases
    Run Keyword And Expect Error
    ...    ValueError*
    ...    Get Value from JSON    ${data}    $..password

Get values from JSON
    [Setup]    Test setup for most cases
    ${allpasswords}    Get Values from JSON    ${data}    $..password
    Length Should Be    ${allpasswords}    4

Convert JSON to string and vice versa
    [Setup]    Test setup for most cases
    Run Keyword And Expect Error
    ...    *is not a string*
    ...    Should Be String    ${data}
    ${json_str}    Convert JSON to String    ${data}
    Should Be String    ${json_str}
    ${json_obj}    Convert String to JSON    ${json_str}
    Run Keyword And Expect Error
    ...    *is not a string*
    ...    Should Be String    ${data}
    Should Contain    ${json_obj}    swaglabs
