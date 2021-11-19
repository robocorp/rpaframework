*** Settings ***
Library           RPA.Windows
Library           String
Library           Process
Task Setup        Set Timeout    0.1

*** Variables ***
${EXE_UIDEMO}     c:\\koodi\\uidemo.exe
${EXE_CALCULATOR}    calc.exe
${EXE_NOTEPAD}    notepad.exe
${EXE_SPOTIFY}    Spotify.exe
${EXE_SAGE50}     sage.exe
${SPOTIFY_PLAYCONTROL}    name:'Player controls' > control:ButtonControl and name:
${SPOTIFY_PLAY}    ${SPOTIFY_PLAYCONTROL}Play
${SPOTIFY_PAUSE}    ${SPOTIFY_PLAYCONTROL}Pause
${SPOTIFY_NEXT}    ${SPOTIFY_PLAYCONTROL}Next
${SPOTIFY_Prev}    ${SPOTIFY_PLAYCONTROL}Prev

*** Keywords ***
Calculator Teardown
    Send Keys    keys={Esc}
    Sleep    1s
    Send Keys    keys={Alt}1
    Sleep    1s

Select Temperature Unit
    [Arguments]    ${unit}    ${degrees}
    # Select Unit
    Click    id:Units1
    Click    id:Units1 > name:${unit}
    Send Keys    keys=${degrees}
    Log To Console    Set ${unit}: ${degrees}
    Send Keys    keys={Esc}

Get Temperature Values
    [Arguments]    ${keys}
    ${values}=    Split String    ${keys}    ,
    FOR    ${val}    IN    @{values}
        ${temperature}=    Get Attribute    id:UnitConverterRootGrid > type:TextControl and regex:.*\\s${val}    Name
        Log To Console    ${temperature}
    END

Start application if it is not open
    [Arguments]    ${windowtitle}    ${start}=${TRUE}
    ${windowlist}=    List Windows
    FOR    ${win}    IN    @{windowlist}
        ${match}=    Get Regexp Matches    ${win}[title]    ^${windowtitle}$
        IF    ${match}
            Return From Keyword    ${TRUE}
        END
    END
    IF    $start
        Windows Search    ${windowtitle}
    END
    Return From Keyword    ${FALSE}

*** Tasks ***
Calculator by clicking buttons
    Start application if it is not open    Calculator
    Control Window    name:Calculator
    Click    id:num9Button
    Click    id:num6Button
    Click    id:plusButton
    Click    id:num4Button
    Click    id:equalButton
    ${result}=    Get Attribute    id:CalculatorResults    Name
    Log To Console    \n${result}
    Send Keys    keys={Esc}
    Close Current Window

*** Tasks ***
Do some calculations
    Start application if it is not open    Calculator
    Control Window    name:Calculator
    Click    id:clearButton depth:16
    Send Keys    keys=96+4=
    ${result}=    Get Attribute    id:CalculatorResults    Name
    Log To Console    \n${result}
    Close Current Window

Play Task Calculator
    Start application if it is not open    Calculator
    Control Window    name:Calculator
    #Control Window    executable:calc.exe
    Click    id:clearButton
    Click    type:Group and name:'Number pad' > type:Button and index:4
    Click    type:Group and name:'Number pad' > type:Button index:5 offset:370,0    # it is optional to use "and" in the locator syntax
    Click    control:Group and name:'Number pad' > control:Button index:7    # "control" maps to same thing as "type" -> "ControlType"
    Click    id:equalButton
    Close Current Window

Play Task Temperature
    Start application if it is not open    Calculator
    Control Window    name:Calculator
    Click    id:TogglePaneButton
    Click    id:Temperature    # TODO. make the click even when not visible
    Log To Console    \nGet temperatures
    Select Temperature Unit    Kelvin    225
    Get Temperature Values    Fahrenheit
    Select Temperature Unit    Fahrenheit    225
    Get Temperature Values    Kelvin
    Select Temperature Unit    Celsius    225
    Get Temperature Values    Kelvin,Fahrenheit
    Close Current Window

Play Task UIDemo
    Windows Run    ${EXE_UIDEMO}
    Control Window    UiDemo    # Handle: 5835532
    Input Text    admin    id:user
    Input Text    password    id:pass
    Click    class:Button
    #Maximize Window
    Sleep    5s
    #Minimize Window
    #Control Window    UIDemo    # Handle: 5901414
    #Click    type:ButtonControl and class:Button and name:Exit > type:TextControl and class:TextBlock and name:Exit
    # TODO. add more actions to the task --- slider, checkboxes, table (get/set vals)

Play Task Spotify
    #Windows Search    spotify
    # TODO. make process find faster
    Run Keyword And Expect Error
    ...    WindowControlError: There is no active window
    ...    Minimize Window
    Run Keyword And Expect Error
    ...    WindowControlError: There is no active window
    ...    Maximize Window
    Control Window    executable:Spotify.exe
    #Maximize Window
    FOR    ${_}    IN RANGE    3
        Click    ${SPOTIFY_NEXT}
        Sleep    5s
    END
    Minimize Window
    Sleep    10s
    Maximize Window

Notepad write text into a file
    Windows Search    notepad
    Control Window    subname:'- Notepad'
    Click    type:MenuBar name:Application > name:Format
    Click    type:MenuItem name:'Font...'
    Control Window    Font
    Select    type:ComboBox id:1136    Trebuchet MS
    Select    type:ComboBox id:1138    28
    Click    type:Button name:OK
    Send Keys    keys={Ctrl}a{Del}
    Send Keys    keys=Lets add some text to the notepad
    Control Window    subname:'- Notepad'
    Click    type:MenuBar name:Application > name:File
    Click    type:MenuItem subname:'Save As'
    Send Keys    keys=story3.txt{Enter}
    Minimize Window    subname:'- Notepad'
    Close Current Window

Windows run and close app
    ${running}=    Start application if it is not open    Calculator    ${FALSE}
    IF    not $running
        Windows Run    calc.exe
    END
    Control Window    Calculator
    Log To Console    Calculator in control
    Close Current Window
    Log To Console    Calculator closed

Control Window by handle
    Log To Console    \nList Windows
    ${win}=    List Windows
    FOR    ${w}    IN    @{win}
        Log To Console    ${w}
    END
    Control Window    handle:3672864

Result from recording
    Control Window    Calculator    # Handle: 4066848
    Click    name:'Seven'
    Click    name:'Eight'
    Click    name:'Nine'
    Click    name:'Plus'
    Click    name:'One'
    Click    name:'Two'
    Click    name:'Three'
    Click    name:'Equals'
