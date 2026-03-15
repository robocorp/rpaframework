*** Settings ***
Library     RPA.Assistant


*** Keywords ***
Second Page
    [Arguments]    ${form}
    Clear Dialog
    Add Heading    Hello ${form}[username]!
    Add Text    This is the second page
    Add Submit Buttons    Done
    Refresh Dialog

Verify Pass
    [Arguments]    ${result}
    Log To Console    ${result}
    Should Be Equal    ${result.submit}    Pass    User marked test as Fail


*** Test Cases ***
Test Heading Only
    [Tags]    manual
    Add Heading    Hello World
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Text
    [Tags]    manual
    Add Heading    Text Test
    Add Text    This is a paragraph of text
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Slider
    [Tags]    manual
    Add Heading    Slider Test
    Add Slider    name=slider    slider_min=0    slider_max=1    default=0.5    steps=10
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}
    Should Be Equal    ${result.slider}    ${0.5}

Test Checkbox
    [Tags]    manual
    Add Heading    Checkbox Test
    Add Checkbox    name=my_check    label=Check me    default=True
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Text Input
    [Tags]    manual
    Add Heading    Text Input Test
    Add Text Input    name=my_input    label=Type something
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Single Button
    [Tags]    manual
    Add Heading    Button Test
    Add Text    Click the button, verify it logs to console, then submit
    Add Button    Click me    Log To Console    button_clicked
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Multiple Buttons
    [Tags]    manual
    Add Heading    Multiple Buttons
    Add Text    Verify all three buttons log to console when clicked
    Add Button    Button 1    Log To Console    btn1
    Add Button    Button 2    Log To Console    btn2
    Add Button    Button 3    Log To Console    btn3
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Drop Down
    [Tags]    manual
    Add Heading    Drop Down Test
    Add Drop-Down    name=choice    options=Option A,Option B,Option C    default=Option B
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Icons
    [Tags]    manual
    Add Heading    Icon Variants Test
    Add Text    Success (green checkmark):
    Add Icon    Success    size=64
    Add Text    Warning (yellow triangle):
    Add Icon    Warning    size=64
    Add Text    Failure (red X):
    Add Icon    Failure    size=64
    Add Text    Flet Icon (white check circle, purple color):
    Add Flet Icon    icon=check_circle_rounded    color=FF00FF    size=48
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Radio Buttons
    [Tags]    manual
    Add Heading    Radio Button Test
    Add Radio Buttons    name=choice    options=Option A,Option B,Option C    default=Option B    label=Pick one
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Required Field Validation
    [Tags]    manual
    Add Heading    Required Field Test
    Add Text    Leave the field empty and click Pass to see validation error
    Add Text Input    name=required_field    label=Required field    required=${TRUE}
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test File Input
    [Tags]    manual
    Add Heading    File Input Test
    Add File Input    name=selected_file    label=Choose a file
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Button Click Then Submit
    [Tags]    manual
    [Documentation]    Tests that clicking a callback button and then submitting works correctly.
    ...    This verifies the thread-safe page.update() fix.
    Add Heading    Click the button first, then submit
    Add Button    Click me    Log To Console    callback_executed
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Window Position Center
    [Tags]    manual
    Add Heading    Centered Window
    Add Text    This window should be centered on screen
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180    location=Center
    Verify Pass    ${result}

Test Window Position TopLeft
    [Tags]    manual
    Add Heading    Top Left Window
    Add Text    This window should be at top-left corner
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180    location=TopLeft
    Verify Pass    ${result}

Test Next Ui Button
    [Tags]    manual
    [Documentation]    Tests that Next UI Button passes form results and navigates to next page.
    ...    Type something, click Next, verify second page shows, then click Done.
    Add Heading    Enter your name
    Add Text Input    name=username    label=Username
    Add Next Ui Button    Next    Second Page
    ${result}=    Run Dialog    timeout=180
    Log To Console    ${result}

Test Password Input
    [Tags]    manual
    Add Heading    Password Test
    Add Text    Verify password field masks input
    Add Text Input    name=username    label=Username
    Add Password Input    name=password    label=Password    placeholder=Enter password
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Hidden Input
    [Tags]    manual
    Add Heading    Hidden Input Test
    Add Text    No hidden field should be visible. Submit to verify value.
    Add Hidden Input    user_id    hidden_value_123
    Add Text Input    name=username    label=Username
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}
    Should Be Equal    ${result.user_id}    hidden_value_123

Test Date Input
    [Tags]    manual
    Add Heading    Date Input Test
    Add Date Input    name=birthdate    default=1993-04-26    label=Birthdate
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Link
    [Tags]    manual
    Add Heading    Link Test
    Add Text    Verify links are clickable and open browser
    Add Link    https://robocorp.com    label=Robocorp Website
    Add Link    https://flet.dev
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Image URL
    [Tags]    manual
    Add Heading    Image Test (URL)
    Add Text    Verify image renders below
    Add Image    https://flet.dev/img/logo.svg    width=200
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Loading Spinner
    [Tags]    manual
    Add Heading    Loading Spinner Test
    Add Text    Verify spinner is animating below
    Add Loading Spinner    name=spinner    width=32    height=32    color=blue500
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Loading Bar
    [Tags]    manual
    Add Heading    Loading Bar Test
    Add Text    Verify progress bar shows at 60%
    Add Loading Bar    name=progress    width=200    bar_height=8    color=green500    value=0.6
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Row Layout
    [Tags]    manual
    Add Heading    Row Layout Test
    Add Text    Verify items appear side by side
    Open Row
    Add Text    Left item
    Add Text    Middle item
    Add Text    Right item
    Close Row
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Column Layout
    [Tags]    manual
    Add Heading    Column Layout Test
    Add Text    Verify two columns side by side
    Open Row
    Open Column
    Add Text    Column 1 - Item 1
    Add Text    Column 1 - Item 2
    Close Column
    Open Column
    Add Text    Column 2 - Item 1
    Add Text    Column 2 - Item 2
    Close Column
    Close Row
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Stack With Containers
    [Tags]    manual
    Add Heading    Stack Layout Test
    Open Stack    width=360    height=360
    Open Container    width=64    height=64    location=Center
    Add Text    center
    Close Container
    Open Container    width=64    height=64    location=TopRight
    Add Text    top right
    Close Container
    Open Container    width=64    height=64    location=TopLeft
    Add Text    top left
    Close Container
    Close Stack
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Navbar
    [Tags]    manual
    Open Navbar    title=My App
    Add Button    Menu    Log To Console    menu_clicked
    Close Navbar
    Add Heading    Content with Navbar
    Add Text    Verify navigation bar is visible at the top
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Set Title Via Button
    [Tags]    manual
    [Documentation]    Click the button to change the window title, then submit.
    Add Heading    Click button to change title
    Add Text    After clicking, window title should change to "New Window Title"
    Add Button    Change Title    Set Title    New Window Title
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Ask User
    [Tags]    manual
    [Documentation]    Tests the Ask User convenience keyword.
    Add Heading    Ask User Test
    Add Text Input    name=answer    label=Your answer
    ${result}=    Ask User    timeout=180
    Log To Console    ${result}

Test Container Styling
    [Tags]    manual
    Add Heading    Container Styling Test
    Add Text    Verify blue background with padding below
    Open Container    padding=20    background_color=blue100    margin=10
    Add Text    Styled container with padding and background
    Close Container
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}

Test Combined Elements
    [Tags]    manual
    Add Heading    Combined Test
    Add Text    Fill in the form below and verify all elements work
    Add Text Input    name=username    label=Username
    Add Slider    name=age    slider_min=0    slider_max=100    default=25    steps=100
    Add Checkbox    name=agree    label=I agree    default=False
    Add Drop-Down    name=color    options=Red,Green,Blue    default=Red
    Add Submit Buttons    buttons=Pass,Fail
    ${result}=    Run Dialog    timeout=180
    Verify Pass    ${result}
