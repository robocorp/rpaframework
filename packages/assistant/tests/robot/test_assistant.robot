*** Settings ***
Library     RPA.Assistant
Library     Process
# Library    RPA.Browser.Selenium
Library     ExecutionContexts.py


*** Test Cases ***
Main
    [Tags]    skip
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

Sleep and Log to Console
    Log To Console    sleeping
    Sleep    1
    Log To Console    awakening

Long Sleep That Timeouts
    [Timeout]    1
    Log To Console    sleeping
    Sleep    2
    Log To Console    should never print

Print with Python Subprocess
    ${result}=    Run Process    python    -c    print("hello")
    Log to Console    ${result}
    Log to Console    ${result.stdout}

Print and Log Execution Context
    ${context}=    Print Execution Context
    Log    ${context}

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

    Add Heading    UI elements for testing
    Add Slider    name=slier    slider_min=0    slider_max=1    default=0.5    steps=10

    Add Heading    good buttons
    Add Button    log button    Log    test_string
    Add Button    print button    Log To Console    test_string
    Add Button    open browser    Open Website
    Add Button    close browser    Close Browser

    Add Button    process_button    Dummy Process
    Add Button    print with python    Print With Python Subprocess
    Add Button    Test Execution Context    Print and Log Execution Context
    Add Button    Sleep and log to console    Sleep and Log to Console
    Add Button    Sleep that timeouts    Long Sleep That Timeouts

    Add Heading    BAD buttons
    # For debugging how unavailable keywords appear in robot side
    Add Button    Keyword Not Found    Not A Keyword
    Add Button    add buttons (does not work)    Control Buttons
    Add Button    subrobot button (broken!)    Exec Robot
    Add Button    python button (broken!)    Exec Python

    Add Heading    submit is below this
