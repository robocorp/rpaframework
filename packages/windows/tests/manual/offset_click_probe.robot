*** Settings ***
Documentation     Probe for issue #1379 in Robot Framework syntax. Run on Windows:
...               uv run robot tests/manual/offset_click_probe.robot
Library           RPA.Windows
Suite Setup       Windows Run    calc.exe    wait_time=2.0
Suite Teardown    Close Current Window


*** Test Cases ***
Offset Spanning To The Next Button Presses It
    Control Window    name:Calculator
    Set Wait Time    0.3
    ${five} =    Get Element    id:num5Button
    ${six} =    Get Element    id:num6Button
    ${dx} =    Evaluate    $six.item.BoundingRectangle.xcenter() - $five.item.BoundingRectangle.xcenter()
    ${dy} =    Evaluate    $six.item.BoundingRectangle.ycenter() - $five.item.BoundingRectangle.ycenter()
    Log To Console    distance from '5' to '6' centre: ${dx},${dy}

    Click    id:clearButton
    Click    id:num5Button offset:${dx},${dy}
    ${shown} =    Get Attribute    id:CalculatorResults    Name
    Should Be Equal    ${shown}    Display is 6

    Click    id:clearButton
    ${elem} =    Get Element    id:num5Button offset:${dx},${dy}
    Click    ${elem}
    ${shown} =    Get Attribute    id:CalculatorResults    Name
    Should Be Equal    ${shown}    Display is 6

Offset Forty Right Lands Forty Right Of Centre
    Control Window    name:Calculator
    Click    id:clearButton
    ${elem} =    Get Element    id:num5Button offset:40,0
    ${cx} =    Evaluate    $elem.item.BoundingRectangle.xcenter()
    ${cy} =    Evaluate    $elem.item.BoundingRectangle.ycenter()
    Click    ${elem}
    ${landed} =    Evaluate    __import__("uiautomation").GetCursorPos()
    Log To Console    centre=(${cx},${cy}) expected=(${{$cx + 40}},${cy}) landed=${landed}
    Should Be Equal As Integers    ${landed}[0]    ${{$cx + 40}}
    Should Be Equal As Integers    ${landed}[1]    ${cy}
