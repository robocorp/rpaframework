*** Settings ***
Library           RPA.Windows
Library           String
Library           Process
Task Setup        Set Wait Time    0.7


*** Variables ***
# Not used as vars, but make sure you have these in PATH.
${EXE_UIDEMO}           uidemo.exe
${EXE_CALCULATOR}       calc.exe
${EXE_NOTEPAD}          notepad.exe
${EXE_SPOTIFY}          Spotify.exe
${EXE_SAGE50}           sage.exe

${SPOTIFY_PLAYCONTROL}    name:"Player controls" > control:ButtonControl and name:
${SPOTIFY_PLAY}    ${SPOTIFY_PLAYCONTROL}Play
${SPOTIFY_PAUSE}    ${SPOTIFY_PLAYCONTROL}Pause
${SPOTIFY_NEXT}    ${SPOTIFY_PLAYCONTROL}Next
${SPOTIFY_Prev}    ${SPOTIFY_PLAYCONTROL}Prev
${TIMEOUT}         1


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
    Send Keys    keys=96+4=     interval=0.1
    ${result} =    Get Attribute    id:CalculatorResults    Name
    Log To Console    ${result}
    ${buttons} =    Get Elements    type:Group and name:"Number pad" > type:Button
    FOR    ${button}    IN    @{buttons}
        Log To Console    ${button}
    END
    Length Should Be    ${buttons}      11      msg=From 0 to 9 and decimlar separator

Keep open a single Notepad
    Set Global Timeout    ${TIMEOUT}
    ${closed} =     Set Variable    0
    ${run} =    Run Keyword And Ignore Error    Close Window    subname:Notepad control:WindowControl
    IF    "${run}[0]" == "PASS"
        ${closed} =    Set Variable    ${run}[1]
    END
    Log    Closed Notepads: ${closed}
    Windows Run   Notepad

Kill app by name
    [Arguments]     ${app_name}

    ${window_list} =   List Windows
    FOR  ${win}  IN   @{window_list}
        ${exists} =   Evaluate   re.match(".*${app_name}.*", """${win}[title]""")

        IF  ${exists}
            ${command} =    Set Variable    os.kill($win["pid"], signal.SIGTERM)
            Log     Killing app: ${win}[title] (PID: $win["pid"])
            Evaluate    ${command}    signal
        END
    END

Close Current Window And Sleep
    Close Current Window
    Sleep   1s


*** Tasks ***
Windows search Calculator by clicking buttons
    Windows Search    Calculator    wait_time=1
    Calculator button actions
    [Teardown]    Close Current Window And Sleep

Calculator by clicking buttons already running
    [Tags]    skip      manual
    Calculator button actions

Windows run Do some calculations
    Windows Run    calc.exe     wait_time=1
    Calculator with keys
    [Teardown]    Close Current Window And Sleep

Windows run Do some calculations already running
    [Tags]    skip      manual
    Calculator with keys

Play Task Calculator
    Windows Search    Calculator    wait_time=1
    Control Window    Calculator
    Click    id:clearButton
    Click    type:Group and name:"Number pad" > type:Button and index:4
    # It is optional to use "and" in the locator syntax.
    ${ver} =    Get OS Version
    IF    "${ver}" == "11"
        # FIXME(cmiN): On Windows 11 this offset minimizes the window. (might be resolution bound)
        ${locator} =    Set Variable    type:Group and name:"Number pad" > type:Button index:5
    ELSE
        ${locator} =    Set Variable    type:Group and name:"Number pad" > type:Button index:5 offset:370,0
    END
    Click    ${locator}
    # "control" maps to same thing as "type" -> "ControlType".
    Click    control:Group and name:"Number pad" > control:Button index:7
    Click    id:equalButton
    [Teardown]    Close Current Window

Play Task Temperature
    Windows Search    Calculator    wait_time=1
    Control Window    Calculator
    # Go to Temperature Converter view.
    Click    id:TogglePaneButton
    Send Keys   keys={PAGEDOWN}     wait_time=0.1  # to see the Temperature view
    ${temp} =  Set Variable    id:Temperature  # works on Windows 10 and lower
    ${ver} =    Get OS Version
    IF    "${ver}" == "11"
        ${temp} =  Set Variable    name:"Temperature Converter"
    END
    Click    ${temp}

    Log To Console    \nGet temperatures
    Select Temperature Unit    Kelvin    225
    Get Temperature Values    Fahrenheit
    Select Temperature Unit    Fahrenheit    225
    Get Temperature Values    Kelvin
    Select Temperature Unit    Celsius    225
    Get Temperature Values    Kelvin,Fahrenheit

    # Go back to Standard Calculator view.
    Click    id:TogglePaneButton
    Send Keys   keys={PAGEUP}     wait_time=0.1  # to see the Standard view
    ${std} =  Set Variable    id:Standard
    IF    "${ver}" == "11"
        ${std} =  Set Variable    name:"Standard Calculator"
    END
    Click    ${std}

    [Teardown]    Close Current Window

Play Task UIDemo
    [Tags]    skip

    Windows Run    UIDemo.exe
    Control Window    UiDemo
    Send Keys    id:user    admin
    Send Keys    id:pass    password
    Click    class:Button

    Control Window    UIDemo
    Set Anchor    id:DataGrid    10.0
    ${headers} =    Get Elements    type:HeaderItem
    Log To Console      Headers: ${headers}
    ${rows} =    Get Elements    class:DataGridRow name:"UiDemo.DepositControl+LineOfTable"
    FOR    ${row}    IN    @{rows}
        ${columns} =    Get Elements    class:DataGridCell    root_element=${row}
        FOR    ${col}    IN    @{columns}
            Log To Console    Cell value: ${col.name}
        END
    END
    ${element} =    Get Element    type:HeaderItem
    Screenshot    ${element}    ${OUTPUT_DIR}${/}element${element.name}.png
    ${name} =    Get Attribute    ${element}    Name
    Log To Console      Attribute: ${name}

    # Clears set anchor above so the clicks would work on the current active window.
    Clear Anchor
    Control Window    UIDemo    # Handle: 5901414
    Click    type:ButtonControl and class:Button and name:Exit > type:TextControl and class:TextBlock and name:Exit     timeout=1
    # TODO: Add more actions to the task: slider, checkboxes, table (get/set vals).
    [Teardown]    Close Current Window

Resize window with Spotify
    [Tags]    skip    manual

    Windows Run     Spotify.exe
    ${window} =    Control Window    executable:Spotify.exe
    Log To Console      Spotify window: ${window}
    Maximize Window
    FOR    ${_}    IN RANGE    3
        Click    ${SPOTIFY_NEXT}
        Sleep    3s
    END
    Minimize Window
    Sleep    1s
    Maximize Window
    Sleep    2s
    Foreground Window
    Restore Window

    [Teardown]    Close Current Window

Notepad write text into a file
    Windows Search    notepad   wait_time=1
    Control Window    subname:"- Notepad"

    ${ver} =    Get OS Version
    IF    "${ver}" == "11"
        Click    Edit   wait_time=0.5
        Click    Font   wait_time=0.5  # for some reason this only highlitghts the button
        Click    Font   wait_time=2  # and this finally clicks it
        Click    id:FontFamilyComboBox
        Click    name:"Lucida Sans Unicode"  wait_time=0.5
        Click    id:FontSizeComboBox
        Click    name:"26"   wait_time=0.5
        Click    name:"Back"
    ELSE
        Control Window    Font
        Click    type:MenuBar name:Application > name:Format
        Click    name:Font...
        Select    type:ComboBox id:1136    Trebuchet MS
        Select    type:ComboBox id:1138    28
        Click    type:Button name:OK
    END

    Control Window    subname:"- Notepad"
    Send Keys    keys={Ctrl}a{Del}
    Send Keys    keys=Lets add some text to the notepad

    Control Window    subname:"- Notepad"
    IF    "${ver}" == "11"
        Click   File    wait_time=0.3
        Click   Save as
        Click   Save as     wait_time=1.5
    ELSE
        Click    type:MenuBar name:Application > name:File
        Click    type:MenuItem subname:"Save As"
    END
    Send Keys    keys=best-win-auto.txt{Enter}  interval=0.05
    ${run} =    Run Keyword And Ignore Error    Control Window    Confirm Save As   timeout=0.5
    IF    "${run}[0]" == "PASS"
        Click   Yes   wait_time=0.3
    END
    Minimize Window    subname:"- Notepad"
    [Teardown]      Close Current Window

Control Window by handle
    Log To Console    \nList Windows
    ${win} =    List Windows
    FOR    ${w}    IN    @{win}
        Log To Console    ${w}
    END
    ${win} =    Control Window    handle:${win}[0][handle]    # handle of the first window in the list
    Log To Console      Controlled window: ${win}

Calculator result from recording
    [Tags]    skip    manual
    Windows Run     Calc

    Control Window    Calculator    # Handle: 4066848
    Click    name:"Seven"
    Click    name:"Eight"
    Click    name:"Nine"
    Click    name:"Plus"
    Click    name:"One"
    Click    name:"Two"
    Click    name:"Three"
    Click    name:"Equals"

    [Teardown]    Close Current Window

Write to Notepad in the background
    [Tags]    skip
    Windows Run     Notepad
    Windows Run     Calc

    Clear Anchor
    Control Window    subname:"- Notepad"    foreground=${False}
    # All the following keyword calls will use the set anchor element as root locator,
    #  UNLESS they specify a locator explicitly or `Clear Anchor` is used.
    ${text_edit} =      Set Variable    name:"Text Editor"
    ${ver} =    Get OS Version
    IF    "${ver}" == "11"
        ${text_edit} =  Set Variable    name:"RichEdit Control"
    END
    Set Anchor      ${text_edit}

    # Write in Notepad while having Calculator as active window.
    Control Window    Calculator
    # Clear Notepad edit window by writing initial text, then append rest of the text.
    ${time} =    Get Time
    Set Value    value=time now is ${time}  # clears when append=False (default)
    Set Value    value= and it's task run time    append=True    newline=True
    Set Value    value=this will appear on the 2nd line    append=True
    Set Value    value=${EMPTY}    append=True    enter=True
    Close Current Window  # this closes Calculator first (as active window)

    [Teardown]    Close Window      subname:Notepad  # finally Notepad is closed too

Test getting elements
    [Tags]    skip
    Clear Anchor

    ${ver} =    Get OS Version
    ${desktop} =    Get Element
    IF    "${ver}" == "11"
        ${buttons} =    Get Elements    id:TaskbarFrameRepeater > type:Button   root_element=${desktop}
    ELSE
        ${buttons} =    Get Elements    name:"Running applications" > type:Button   root_element=${desktop}
    END
    Log To Console    \nList Taskbar applications\n
    Log To Console    Desktop: ${desktop}
    FOR    ${button}    IN    @{buttons}
        Log To Console    App: ${button.name}
    END

Control window after closing linked root element
    [Setup]    Keep open a single Notepad
    ${window} =     Control Window   subname:Notepad control:WindowControl
    Log    Controlling Notepad window: ${window}

    Kill app by name    Notepad

    Windows Run   Calc
    # Tests against `COMError` fixes.
    ${window} =     Control Window   subname:Calc    main=${False}
    Log    Controlling Calculator window: ${window}

    [Teardown]    Close Current Window  # closes Calculator (last active window)

Tree printing and controlled anchor cleanup
    Print Tree     #capture_image_folder=output${/}controls

    Windows Run   Calc
    ${win} =    Control Window   subname:Calc control:WindowControl    timeout=${TIMEOUT}
    Set Anchor    ${win}
    ${elem} =    Get Element  # pulls the anchor
    Should Be Equal    ${elem.name}    Calculator

    Close Window    subname:Calc control:WindowControl    timeout=${TIMEOUT}
    # With the controlled Calculator closed and active window/anchor cleaned up, we
    #  should get the Desktop element only.
    ${elem} =    Get Element
    Should Be Equal     ${elem.name}     Desktop 1
