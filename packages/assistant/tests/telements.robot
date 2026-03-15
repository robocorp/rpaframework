*** Settings ***
Library     RPA.Assistant


*** Test Cases ***
Test Heading Only
    [Tags]    manual
    Add Heading    Hello World
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Text
    [Tags]    manual
    Add Heading    Text Test
    Add Text    This is a paragraph of text
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Slider
    [Tags]    manual
    Add Heading    Slider Test
    Add Slider    name=slider    slider_min=0    slider_max=1    default=0.5    steps=10
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}
    Should Be Equal    ${result.slider}    ${0.5}

Test Checkbox
    [Tags]    manual
    Add Heading    Checkbox Test
    Add Checkbox    name=my_check    label=Check me    default=True
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Icon
    [Tags]    manual
    Add Heading    Icon Test
    Add Flet Icon    icon=check_circle_rounded    color=FF00FF    size=48
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Text Input
    [Tags]    manual
    Add Heading    Text Input Test
    Add Text Input    name=my_input    label=Type something
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Single Button
    [Tags]    manual
    Add Heading    Button Test
    Add Button    Click me    Log To Console    button_clicked
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Multiple Buttons
    [Tags]    manual
    Add Heading    Multiple Buttons
    Add Button    Button 1    Log To Console    btn1
    Add Button    Button 2    Log To Console    btn2
    Add Button    Button 3    Log To Console    btn3
    Add Submit Buttons    buttons=Submit,Cancel    default=Submit
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Drop Down
    [Tags]    manual
    Add Heading    Drop Down Test
    Add Drop-Down    name=choice    options=Option A,Option B,Option C    default=Option B
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Icon Success
    [Tags]    manual
    Add Heading    Success Icon
    Add Icon    Success    size=64
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Icon Warning
    [Tags]    manual
    Add Heading    Warning Icon
    Add Icon    Warning    size=64
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Icon Failure
    [Tags]    manual
    Add Heading    Failure Icon
    Add Icon    Failure    size=64
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Radio Buttons
    [Tags]    manual
    Add Heading    Radio Button Test
    Add Radio Buttons    name=choice    options=Option A,Option B,Option C    default=Option B    label=Pick one
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Required Field Validation
    [Tags]    manual
    Add Heading    Required Field Test
    Add Text    Leave the field empty and click OK to see validation error
    Add Text Input    name=required_field    label=Required field    required=${TRUE}
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test File Input
    [Tags]    manual
    Add Heading    File Input Test
    Add File Input    name=selected_file    label=Choose a file
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Button Click Then Submit
    [Tags]    manual
    [Documentation]    Tests that clicking a callback button and then submitting works correctly.
    ...    This verifies the thread-safe page.update() fix.
    Add Heading    Click the button first, then click OK
    Add Button    Click me    Log To Console    callback_executed
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Window Position Center
    [Tags]    manual
    Add Heading    Centered Window
    Add Text    This window should be centered on screen
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180    location=Center
    Log To Console    ${result}

Test Window Position TopLeft
    [Tags]    manual
    Add Heading    Top Left Window
    Add Text    This window should be at top-left corner
    Add Submit Buttons    OK
    ${result}=    Run Dialog    timeout=180    location=TopLeft
    Log To Console    ${result}

Test Combined Elements
    [Tags]    manual
    Add Heading    Combined Test
    Add Text    Fill in the form below
    Add Text Input    name=username    label=Username
    Add Slider    name=age    slider_min=0    slider_max=100    default=25    steps=100
    Add Checkbox    name=agree    label=I agree    default=False
    Add Drop-Down    name=color    options=Red,Green,Blue    default=Red
    Add Submit Buttons    buttons=Submit,Cancel    default=Submit
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}
