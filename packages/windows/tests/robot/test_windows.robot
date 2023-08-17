*** Settings ***
Library           Collections
Library           Process
Library           RPA.Windows
Library           String

Test Setup      Set Wait Time    0.7

Default Tags      windows   skip


*** Variables ***
${RESOURCES}      ${CURDIR}${/}..${/}resources
${RESULTS}        ${CURDIR}${/}..${/}results

${EXE_UIDEMO}       UIDemo.exe
${EXE_CALCULATOR}   calc.exe
${EXE_SPOTIFY}      Spotify.exe

${LOC_NOTEPAD}      name:Notepad class:Notepad
${LOC_CALCULATOR}   subname:Calc control:WindowControl
${LOC_WORDPAD}      name:"Document - WordPad" and type:WindowControl

${TIMEOUT}        1


*** Keywords ***
Calculator Teardown
    Send Keys    keys={Esc}
    Sleep    1s
    Send Keys    keys={Alt}1
    Sleep    1s

Calculator Temperature Converter View
    Click    id:TogglePaneButton
    Send Keys    keys={PAGEDOWN}    wait_time=0.1    # to see the Temperature view
    ${temp} =    Set Variable    id:Temperature    # works on Windows 10 and lower
    ${ver} =    Get OS Version
    IF    "${ver}" == "11"
        ${temp} =    Set Variable    name:"Temperature Converter"
    END
    Click    ${temp}

Calculator Standard View
    Click    id:TogglePaneButton
    Send Keys    keys={PAGEUP}    wait_time=0.1    # to see the Standard view
    ${std} =    Set Variable    id:Standard
    ${ver} =    Get OS Version
    IF    "${ver}" == "11"
        ${std} =    Set Variable    name:"Standard Calculator"
    END
    Click    ${std}

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
    ${values} =    Split String    ${keys}    ,
    FOR    ${val}    IN    @{values}
        ${temperature} =    Get Attribute    id:UnitConverterRootGrid > type:TextControl and regex:.*\\s${val}    Name
        Log To Console    ${temperature}
    END

Calculator button actions
    Control Window    Calculator type:Window
    Click    id:num9Button
    Click    id:num6Button
    Click    id:plusButton
    Click    id:num4Button
    Click    id:equalButton
    ${result} =    Get Attribute    id:CalculatorResults    Name
    Log To Console    \n${result}
    Send Keys    keys={Esc}

Calculator with keys
    Control Window    Calculator
    Click    id:clearButton
    Send Keys    keys=96+4=    interval=0.1
    ${result} =    Get Attribute    id:CalculatorResults    Name
    Log To Console    ${result}
    ${buttons} =    Get Elements    type:Group and name:"Number pad" > type:Button
    FOR    ${button}    IN    @{buttons}
        Log To Console    ${button}
    END
    Length Should Be    ${buttons}    11    msg=From 0 to 9 and decimlar separator

Keep open a single Notepad
    Set Global Timeout    ${TIMEOUT}
    ${closed} =    Set Variable    0
    ${run} =    Run Keyword And Ignore Error    Close Window    ${LOC_NOTEPAD} control:WindowControl
    IF    "${run}[0]" == "PASS"
        ${closed} =    Set Variable    ${run}[1]
    END
    Log    Closed Notepads: ${closed}
    Windows Run    Notepad

Kill app by name
    [Arguments]    ${app_name}
    ${window_list} =    List Windows
    FOR    ${win}    IN    @{window_list}
        ${exists} =    Evaluate    re.match(".*${app_name}.*", """${win}[title]""")
        IF    ${exists}
            ${command} =    Set Variable    os.kill($win["pid"], signal.SIGTERM)
            Log    Killing app: ${win}[title] (PID: $win["pid"])
            Evaluate    ${command}    signal
        END
    END

Close Current Window And Sleep
    Close Current Window
    Sleep    1s


*** Test Cases ***
Windows search Calculator by clicking buttons
    Windows Search    Calculator    wait_time=1
    Calculator button actions
    [Teardown]    Close Current Window And Sleep

Calculator by clicking buttons already running
    [Tags]  manual  # Calculator should be already open.
    Calculator button actions

Windows run Do some calculations
    Windows Run    ${EXE_CALCULATOR}    wait_time=1
    Calculator with keys
    [Teardown]    Close Current Window And Sleep

Windows run Do some calculations already running
    [Tags]  manual  # Calculator should be already open.
    Calculator with keys

Play Task Calculator
    [Documentation]    Checks if 34+6=40
    Windows Search    Calculator    wait_time=1
    Control Window    Calculator
    Click    id:clearButton
    ${button_locator} =    Set Variable
    ...    type:Group and name:"Number pad" > type:Button
    # It is optional to use "and" in the locator syntax. (only "and"s are assumed)
    Click    ${button_locator} and index:4    # "3"
    Click    ${button_locator} index:5 offset:0,0    # "4"
    # NOTE(cmin764): On different Windows versions the app UI differs so the offsets.
    #    (might be also resolution bound)
    ${ver} =    Get OS Version
    IF    "${ver}" == "11"
        ${offset} =    Set Variable    480,100
    ELSE
        ${offset} =    Set Variable    370,0    # FIXME on Windows 10
    END
    # Click the "+" button relative to "4" by offset.
    Click    ${button_locator} index:5 offset:${offset}    # "+"
    # "control" maps to same thing as "type" -> "ControlType".
    Click    control:Group and name:"Number pad" > control:Button index:7    # 6
    Click    id:equalButton    # "="
    ${result} =    Get Attribute    id:CalculatorResults    Name
    Should Be Equal    ${result}    Display is 40
    [Teardown]    Close Current Window

Play Task Temperature
    Windows Search    Calculator    wait_time=1
    Control Window    Calculator

    Calculator Temperature Converter View
    Log To Console    \nGet temperatures
    Select Temperature Unit    Kelvin    225
    Get Temperature Values    Fahrenheit
    Select Temperature Unit    Fahrenheit    225
    Get Temperature Values    Kelvin
    Select Temperature Unit    Celsius    225
    Get Temperature Values    Kelvin,Fahrenheit

    Calculator Standard View
    [Teardown]    Close Current Window

Play Task UIDemo
    Windows Run    ${EXE_UIDEMO}
    Control Window    UiDemo
    Send Keys    id:user    admin
    Send Keys    id:pass    password
    Click    class:Button
    Control Window    UIDemo
    Set Anchor    id:DataGrid    10.0
    ${headers} =    Get Elements    type:HeaderItem
    Log To Console    Headers: ${headers}
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
    Log To Console    Attribute: ${name}
    # Clears set anchor above so the clicks would work on the current active window.
    Clear Anchor
    Control Window    UIDemo    # Handle: 5901414
    Click
    ...    type:ButtonControl and class:Button and name:Exit > type:TextControl and class:TextBlock and name:Exit
    ...    timeout=1
    # TODO: Add more actions to the task: slider, checkboxes, table (get/set vals).
    [Teardown]    Close Current Window

Resize window with Spotify
    [Tags]  manual  # Spotify should be installed and available to use.

    Windows Run    ${EXE_SPOTIFY}
    ${window} =    Control Window    executable:${EXE_SPOTIFY}
    Log To Console    Spotify window: ${window}

    Maximize Window
    ${spotify_playcontrol} =    Set Variable
    ...     name:"Player controls" > control:ButtonControl and name:
    ${spotify_next} =   Set Variable    ${spotify_playcontrol}Next
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
    [Setup]     Windows Run    notepad

    Control Window    ${LOC_NOTEPAD}
    ${ver} =    Get OS Version
    IF    "${ver}" == "11"
        Click    Edit    wait_time=0.5
        Click    Font    wait_time=0.5    # for some reason this only highlitghts the button
        Click    Font    wait_time=2    # and this finally clicks it

        Click    id:FontFamilyComboBox
        Send Keys   keys={DOWN}
        Send Keys   keys={Ctrl}a{Del}
        Send Keys   keys=Lucida Sans Unicode    send_enter=${True}    wait_time=0.5

        Select  id:FontSizeComboBox     22
        # If the Select above doesn't work.
#        Click    id:FontSizeComboBox
#        Send Keys   keys={DOWN}
#        Send Keys   keys={Ctrl}a{Del}
#        Send Keys   keys=22     send_enter=${True}    wait_time=0.5

        Click    name:"Back"
    ELSE
        Control Window    Font
        Click    type:MenuBar name:Application > name:Format
        Click    name:Font...
        Select    type:ComboBox id:1136    Trebuchet MS
        Select    type:ComboBox id:1138    28
        Click    type:Button name:OK
    END
    Control Window    ${LOC_NOTEPAD}
    Send Keys    keys={Ctrl}a{Del}
    Send Keys    keys=Lets add some text to the notepad
    Control Window    ${LOC_NOTEPAD}
    IF    "${ver}" == "11"
        Click    File    wait_time=0.3
        Click    Save as
        Click    Save as    wait_time=1.5
    ELSE
        Click    type:MenuBar name:Application > name:File
        Click    type:MenuItem subname:"Save As"
    END
    Send Keys    keys=best-win-auto.txt{Enter}    interval=0.05
    ${run} =    Run Keyword And Ignore Error    Control Window    Confirm Save As    timeout=0.5
    IF    "${run}[0]" == "PASS"
        Click    Yes    wait_time=0.3
    END
    Minimize Window    ${LOC_NOTEPAD}

    [Teardown]    Close Current Window

Control Window by handle
    Log To Console    \nList Windows
    ${win} =    List Windows
    FOR    ${w}    IN    @{win}
        Log To Console    ${w}
    END
    ${win} =    Control Window    handle:${win}[0][handle]    # handle of the first window in the list
    Log To Console    Controlled window: ${win}

Calculator result from recording
    Windows Run    Calc
    Control Window    Calculator    # Handle: 4066848

    Calculator Standard View
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
    [Tags]  manual  # The text editing element can't be found anymore.
    [Setup]     Windows Run    Notepad

    Windows Run    Calc
    Clear Anchor
    Control Window    ${LOC_NOTEPAD}    foreground=${False}
    # All the following keyword calls will use the set anchor element as root locator,
    #  UNLESS they specify a locator / root element explicitly or `Clear Anchor` is
    #  used.
    Set Anchor    regex:"Text (E|e)ditor"

    # Write in Notepad while having Calculator as active window.
    Control Window    Calculator
    # Clear Notepad edit window by writing initial text, then append rest of the text.
    ${time} =    Get Time
    Set Value    value=time now is ${time}    # clears when append=${False} (default)
    Set Value    value= and it's the task run time    append=${True}    newline=${True}
    Set Value    value=this will appear on the 2nd line    append=${True}
    Set Value    value=${EMPTY}    append=${True}    enter=${True}

    Close Current Window    # this closes Calculator first (as active window)
    [Teardown]    Close Window    ${LOC_NOTEPAD}    # finally Notepad is closed too

Test getting elements
    Clear Anchor
    ${ver} =    Get OS Version
    ${desktop} =    Get Element     desktop
    IF    "${ver}" == "11"
        ${buttons} =    Get Elements    id:TaskbarFrameRepeater > type:Button    root_element=${desktop}
    ELSE
        ${buttons} =    Get Elements    name:"Running applications" > type:Button    root_element=${desktop}
    END
    Log To Console    \nList Taskbar applications\n
    Log To Console    Desktop: ${desktop}
    FOR    ${button}    IN    @{buttons}
        Log To Console    App: ${button.name}
    END

Control window after closing linked root element
    [Setup]    Keep open a single Notepad
    ${window} =    Control Window    ${LOC_NOTEPAD} control:WindowControl
    Log    Controlling Notepad window: ${window}
    Kill app by name    Notepad
    Windows Run    Calc
    # Tests against `COMError` fixes.
    ${window} =    Control Window    ${LOC_CALCULATOR}    main=${False}
    Log    Controlling Calculator window: ${window}
    [Teardown]    Close Current Window    # closes Calculator (last active window)

Tree printing and controlled anchor cleanup
    Windows Run    Calc
    ${win} =    Control Window    ${LOC_CALCULATOR}    timeout=${TIMEOUT}
    Set Anchor    ${win}
    ${elem} =    Get Element    # pulls the anchor
    Should Be Equal    ${elem.name}    Calculator
    Close Window    ${LOC_CALCULATOR}    timeout=${TIMEOUT}
    # With the controlled Calculator closed and active window/anchor cleaned up, we
    #    should get the Desktop element only.
    ${elem} =    Get Element
    Should Be Equal    ${elem.name}    Desktop 1

Click Calculator Numeric Buttons
    [Documentation]    Clicks all the numeric buttons in Calculator

    Windows Run    Calc
    Control Window    ${LOC_CALCULATOR}
    @{buttons} =    Get Elements    id:NumberPad > class:Button
    FOR    ${button}    IN    @{buttons}
        ${is_numeric} =    Evaluate    "num" in "${button.item.AutomationId}"
        IF    ${is_numeric}
            Click    ${button}    wait_time=0.2
        END
    END

    [Teardown]  Close Current Window

Log All Calculator Buttons Matching Expression
    [Documentation]    Logs all the buttons in the controlled window if they contain
    ...     an 'o' in their name.
    [Setup]   Windows Run    Calc

    Control Window    ${LOC_CALCULATOR}
    @{buttons} =    Get Elements    class:Button regex:.*o.*
    ...     siblings_only=${False}  # this will search globally for such buttons
    Log List    ${buttons}
    ${length} =     Get Length      ${buttons}
    Log To Console      Number of buttons: ${length}

    [Teardown]  Close Current Window

Retrieve Nested Notepad Elements
    [Documentation]     Try to unfold menu items until being able to retrieve a deep
    ...     element inside the tree as soon as it becomes visible.
    [Setup]   Windows Run    Notepad

    Control Window      ${LOC_NOTEPAD}
    Click   View
    Click   Zoom
    ${zoom_in} =   Get Element     Zoom in
    Log To Console      "Zoom in" item: ${zoom_in}

    [Teardown]  Close Current Window

Test Desktop Searching
    [Documentation]     Test some odd scenarios of elements retrieval.

    @{desktops} =     Get Elements  desktop     siblings_only=${False}
    Log List    ${desktops}

Test Locator Path Strategy
    [Documentation]     Check elements retrieval and tree printing with a path of
    ...     element indexes. (node positions in the tree)
    [Setup]     Windows Run     ${EXE_CALCULATOR}

    # Retrieve the "One" button from a root parent.
    ${elem} =   Get Element     Calculator > path:2|3|2|8|2 offset:120,0
    Should Be Equal     ${elem.name}    One
    Click   ${elem}  # clicks with offset too, even if found by path (Two button)

    # Get all the numeric buttons using a path parent.
    ${elems} =   Get Elements     Calculator > path:2|3|2|8 > type:ButtonControl
    @{names} =   Create List
    FOR     ${btn}   IN     @{elems}
        Append To List  ${names}    ${btn.name}
    END
    List Should Contain Value   ${names}    Four

    # Check the structure returned by the tree printing.
    ${tree} =   Print Tree      Calculator > path:2|3|2|8   return_structure=${True}
    ...     capture_image_folder=${RESULTS}${/}images   log_as_warnings=${True}
    Log To Console      ${tree}
    # Check if the fifth control on level 2 in the tree is actually the "Four" button.
    ${elem} =   Set Variable    ${tree}[${2}][${5 - 1}]
    @{names} =  Create List     ${elem.name}
    Should Contain Any      ${names}    Four    4

    [Teardown]      Close Window   ${LOC_CALCULATOR}

Click and set values in WordPad
    [Documentation]     Set values in WordPad while text editor widget isn't in focus.
    ...    (note that an additional '\r' is added with each value set, not in our
    ...    control)
    [Setup]     Windows Run     Wordpad

    # Just control the main window and click the title bar.
    Control Window      ${LOC_WORDPAD}
    Click   id:TitleBar and type:TitleBarControl

    # Enable mouse movement simulation while changing the page size.
    ${old} =    Set Mouse Movement     ${True}
    Should Be True      "${old}" == "False"  # disabled by default
    Click   name:View
    Click   File tab
    Click   Page setup
    Select  name:Size: class:ComboBox   A4
    Send Keys   keys={Enter}
    # Disable mouse movement simulation.
    ${old} =    Set Mouse Movement     ${False}
    Should Be True      "${old}" == "True"  # was enabled before

    # Note that one additional `\r` (Windows EOL) is added by the app itself in this
    #  scenario.
    ${text_locator} =   Set Variable    name:"Rich Text Window"
    ${elem} =   Set Value   ${text_locator}     This i
    Set Value   ${elem}     s my test text.     append=${True}
    Set Value   ${elem}     append=${True}      enter=${True}
    Set Value   ${elem}     2nd line text.   append=${True}    newline=${True}
    ${text} =   Get Value   ${elem}
    Should Be Equal     ${text}     This i\rs my test text.\r\r\r2nd line text.\r\r

    [Teardown]  Close Current Window
