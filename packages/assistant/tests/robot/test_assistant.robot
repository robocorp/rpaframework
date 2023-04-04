*** Settings ***
Library     RPA.Assistant
Library     Process
# Library    RPA.Browser.Selenium
Library     ExecutionContexts.py


*** Test Cases ***
Main
    [Tags]    skip

    Control Buttons
    ${results}=    Ask User    location=TopLeft
    Log To Console  ${results}

    Should Be True     ${results.true_checkbox}
    Should Be True     $results.true_checkbox
    Should Be True     not(${results.false_checkbox})
    Should Be True     not($results.false_checkbox)

    Should Be Equal    ${results.slider}    ${0.5}
    Should Be Equal    ${results}[slider]    ${0.5}


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

Stack Testing Ui
    Clear Dialog
    Open Stack    width=360    height=360

    Open Container    width=64    height=64    location=Center
    Add Text    center
    Close Container

    Open Container    width=64    height=64    location=TopRight
    Add Text    top right
    Close Container

    Open Container    width=64    height=64    location=TopLeft
    Add Text    bottom right
    Close Container

    Close Stack
    Refresh Dialog

DotDict Ui
    [Arguments]  ${results}
    Clear Dialog
    Add Slider     name=slider    slider_min=0    slider_max=1    default=0.5    steps=10
    Add Text  ${results.hidden}

    Refresh Dialog

Must Be Short
    [Arguments]  ${value}
    # We sleep to enable testing of a validation that won't return quickly
    # If there is a long sleep here the event synchronity gets out of order
    # Sleep  0.2
    IF  len($value) > 3
        RETURN  Value Too Long
    ELSE
        RETURN
    END

Validate Email
    [Arguments]    ${email}
    # E-mail specification is complicated, this matches that the e-mail has
    # at least one character before and after the @ sign, and at least one
    # character after the dot.
    ${regex}=    Set Variable    ^.+@.+\\..+
    ${valid}=    Run Keyword And Return Status    Should Match Regexp  ${email}  ${regex}
    IF  not $valid
        RETURN  Invalid email address
    END


Control Buttons
    Add Heading    UI elements for testing
    Add Slider     name=slider    slider_min=0    slider_max=1    default=0.5    steps=10
    Add Checkbox    name=true_checkbox    label=Checkbox  default=True
    Add Checkbox    name=false_checkbox   label=Checkbox  default=False
    Add Flet Icon    icon_name=check_circle_rounded    color=FF00FF    size=48

    Add Heading    good buttons
    Add Button    Set title    Set Title    testing_title
    Add Button    log button    Log    test_string
    Add Button    print button    Log To Console    test_string
    Add Button    open browser    Open Website
    Add Button    close browser    Close Browser
    Add Button    stack ui    Stack Testing Ui
    Add Hidden Input    hidden  value
    Add Next Ui Button  Test dotdict for next UI  DotDict Ui

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

    Add Heading  Inputs with validations
    Add Text Input  short_text  required=True  validation=Must Be Short
    Add text input    email  label=Email  validation=Validate Email


    Add Heading    submit is below this
