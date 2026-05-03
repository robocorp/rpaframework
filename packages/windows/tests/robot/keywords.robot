
*** Settings ***
Library           Collections
Library           Process
Library           RPA.Windows
Library           String


*** Variables ***
${RESOURCES}      ${CURDIR}${/}..${/}..${/}resources
${RESULTS}        ${CURDIR}${/}..${/}results

${EXE_UIDEMO}       UIDemo.exe
${EXE_CALCULATOR}   calc.exe
${EXE_SPOTIFY}      Spotify.exe
${LOC_TESTAPP}      name:"RPA Windows Test App"
${LOC_TESTAPP_WX}   name:"RPA Windows Test App WX"

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

# ---------------------------------------------------------------------------
# Test App — testapp.py
# ---------------------------------------------------------------------------

Start Test App
    [Documentation]     Launch the local testapp.py and return its window element.
    Start Process    python    ${RESOURCES}${/}testapp.py    alias=testapp
    Sleep    1.5s
    ${win} =    Control Window    ${LOC_TESTAPP}
    RETURN    ${win}

Stop Test App
    Terminate Process    handle=testapp
    Wait For Process    handle=testapp    timeout=5s    on_timeout=kill


# ---------------------------------------------------------------------------
# WX Test App — testapp_wx.py  (wxPython: proper UIAutomation exposure)
# ---------------------------------------------------------------------------

Start Test App WX
    [Documentation]     Launch testapp_wx.py and set it as the active window.
    Start Process    uv    run    python    ${RESOURCES}${/}testapp_wx.py    alias=testapp_wx
    Sleep    2s
    Control Window    ${LOC_TESTAPP_WX}

Stop Test App WX
    Terminate Process    handle=testapp_wx
    Wait For Process    handle=testapp_wx    timeout=5s    on_timeout=kill