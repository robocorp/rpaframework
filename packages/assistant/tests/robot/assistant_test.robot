*** Settings ***
Library     RPA.Assistant
Library     Process
# Library    RPA.Browser.Selenium


*** Test Cases ***
Main
    Control Buttons
    Ask User    location=TopLeft


*** Keywords ***
Exec Robot
    Set Log Level    TRACE
    ${robot_cmd}=    Create List
    ...    python
    ...    -m
    ...    robot
    ...    --report
    ...    NONE
    ...    --outputdir
    ...    ${CURDIR}/tests/output
    ...    ${CURDIR}/tests/assistant_test.robot
    ${result}=    Run Process    @{robot_cmd}    timeout=5m

Exec Python
    Set Log Level    TRACE
    ${robot_cmd}=    Create List    python    tests/assistant_test.py
    ${result}=    Run Process    @{robot_cmd}
    Log    ${result}

Print with Python
    ${result}=    Run Process    python    -c    print("hello")
    Log to Console    ${result}
    Log to Console    ${result.stdout}

Dummy Process
    Set Log Level    TRACE
    ${result}=    Run Process    echo    0
    Log to Console    ${result}
    Log to Console    ${result.stdout}

Open Website
    Set Log Level    TRACE
    Open Available Browser    robocorp.com

Control Buttons
    Set Log Level    TRACE
    Add Heading    good buttons
    Add Button    log button    Log    test_string
    Add Button    print button    Log To Console    test_string
    Add Button    open browser    Open Website
    Add Button    close browser    Close Browser

    Add Button    process_button    Dummy Process
    Add Button    print with python    Print With Python

    Add Heading    BAD buttons
    # For debugging how unavailable keywords appear in robot side
    Add Button    Keyword Not Found    Not A Keyword
    Add Button    add buttons (does not work)    Control Buttons
    Add Button    subrobot button (broken!)    Exec Robot
    Add Button    python button (broken!)    Exec Python

    Add Heading    submit is below this
