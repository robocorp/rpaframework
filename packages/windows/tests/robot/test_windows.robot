*** Settings ***
Library           RPA.Windows
Library           String
Library           Process
Task Setup        Set Wait Time    0.1

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

Calculator button actions
    Control Window    Calculator type:Window
    Click    id:num9Button
    Click    id:num6Button
    Click    id:plusButton
    Click    id:num4Button
    Click    id:equalButton
    ${result}=    Get Attribute    id:CalculatorResults    Name
    Log To Console    \n${result}
    Send Keys    keys={Esc}

Calculator with keys
    Control Window    Calculator
    Click    id:clearButton
    Send Keys    keys=96+4=
    ${result}=    Get Attribute    id:CalculatorResults    Name
    Log To Console    ${result}
    ${buttons}=    Get Elements    type:Group and name:'Number pad' > type:Button
    FOR    ${button}    IN    @{buttons}
        Log To Console    ${button}
    END

*** Tasks ***
Windows search Calculator by clicking buttons
    Windows Search    Calculator
    Calculator button actions
    [Teardown]    Close Current Window

Calculator by clicking buttons already running
    Calculator button actions

*** Tasks ***
Windows run Do some calculations
    Windows Run    calc.exe
    Calculator with keys
    [Teardown]    Close Current Window

Windows run Do some calculations already running
    Calculator with keys

Play Task Calculator
    Windows Search    Calculator
    Control Window    Calculator
    Click    id:clearButton
    Click    type:Group and name:'Number pad' > type:Button and index:4
    Click    type:Group and name:'Number pad' > type:Button index:5 offset:370,0    # it is optional to use "and" in the locator syntax
    Click    control:Group and name:'Number pad' > control:Button index:7    # "control" maps to same thing as "type" -> "ControlType"
    Click    id:equalButton
    [Teardown]    Close Current Window

Play Task Temperature
    Windows Search    Calculator
    Control Window    Calculator
    Click    id:TogglePaneButton
    Click    id:Temperature    # TODO. make the click even when not visible
    Log To Console    \nGet temperatures
    Select Temperature Unit    Kelvin    225
    Get Temperature Values    Fahrenheit
    Select Temperature Unit    Fahrenheit    225
    Get Temperature Values    Kelvin
    Select Temperature Unit    Celsius    225
    Get Temperature Values    Kelvin,Fahrenheit
    [Teardown]    Close Current Window

Play Task UIDemo
    [Tags]    skip
    Windows Run    C:\\apps\\UIDemo.exe
    Control Window    UiDemo
    Send Keys    id:user    admin
    Send Keys    id:pass    password
    Click    class:Button
    Control Window    UIDemo
    Set Anchor    id:DataGrid    10.0
    ${headers}=    Get Elements    type:HeaderItem
    ${rows}=    Get Elements    class:DataGridRow name:'UiDemo.DepositControl+LineOfTable'
    #Log To Console    ${element.Name}
    FOR    ${row}    IN    @{rows}
        ${columns}=    Get Elements    class:DataGridCell    root_element=${row}
        FOR    ${col}    IN    @{columns}
            Log To Console    Cell value: ${col.item.Name}
        END
#    Screenshot    $el    element${el.item.Name}.png
#    ${name}=    Get Attribute    $el    Name
#    Log To Console    ${name}
    END
    #${element}=    Get Element    type:HeaderItem
    #Screenshot    ${element}    element${element.item.Name}.png
    #${name}=    Get Attribute    ${element}    Name
    #Control Window    UIDemo    # Handle: 5901414
    #Click    type:ButtonControl and class:Button and name:Exit > type:TextControl and class:TextBlock and name:Exit
    # TODO. add more actions to the task --- slider, checkboxes, table (get/set vals)
    [Teardown]    Close Current Window

Play Task Spotify
    [Tags]    skip
    ${window}=    Control Window    executable:Spotify.exe
    Sleep    5s
    Log To Console    ${window}
    #Maximize Window
    FOR    ${_}    IN RANGE    3
        Click    ${SPOTIFY_NEXT}
        Sleep    5s
    END
    Minimize Window
    Sleep    10s
    Maximize Window
    Sleep    2s
    Foreground Window
    Restore Window

Notepad write text into a file
    Windows Search    notepad
    Control Window    subname:'- Notepad'
    Click    type:MenuBar name:Application > name:Format
    Click    name:Font...
    Control Window    Font
    Select    type:ComboBox id:1136    Trebuchet MS
    Select    type:ComboBox id:1138    28
    Click    type:Button name:OK
    Control Window    subname:'- Notepad'
    Send Keys    keys={Ctrl}a{Del}
    Send Keys    keys=Lets add some text to the notepad
    Control Window    subname:'- Notepad'
    Click    type:MenuBar name:Application > name:File
    Click    type:MenuItem subname:'Save As'
    Send Keys    keys=story4.txt{Enter}
    Minimize Window    subname:'- Notepad'
    Close Current Window

Control Window by handle
    Log To Console    \nList Windows
    ${win}=    List Windows
    FOR    ${w}    IN    @{win}
        Log To Console    ${w}
    END
    Control Window    handle:${win}[0][handle]    # handle of the first window in the list

Result from recording
    [Tags]    skip    manual
    Control Window    Calculator    # Handle: 4066848
    Click    name:'Seven'
    Click    name:'Eight'
    Click    name:'Nine'
    Click    name:'Plus'
    Click    name:'One'
    Click    name:'Two'
    Click    name:'Three'
    Click    name:'Equals'

Write to Notepad on background
    [Tags]    skip    manual
    Control Window    subname:'- Notepad'    foreground=False
    # Clear Notepad window and start appending text
    Set Anchor    name:'Text Editor'
    # all following keyword calls will use anchor element as locator
    # UNLESS they specify locator specifically or `Clear Anchor` is used
    ${time}=    Get Time
    Set Value    value=time now is ${time}    # clears when append=False (default)
    Set Value    value= and it's task run time    append=True    newline=True
    Set Value    value=this will appear on the 2nd line    append=True
    Set Value    value=${EMPTY}    append=True    enter=True

Test get element
    [Tags]    skip    manual
    ${desktop}=    Get Element
    ${buttons}=    Get Elements    name:'Running applications' > type:Button    root_element=${desktop}
    Log To Console    \nList task bar applications\n
    Log To Console    Desktop: ${desktop}
    FOR    ${b}    IN    @{buttons}
        Log To Console    app = ${b}
    END
