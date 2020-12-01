*** Settings ***
Library  RPA.Desktop
Library  OperatingSystem
Default Tags    RPA.Desktop

*** Variables ***
${filename}=  temporary_test_file.png

*** Tasks ***
Test Application keywords
    [Documentation]  Skipped for now because would require starting and stopping of Applications
    [Tags]  skip
    Close All Applications
    Close Application
    Open Application
    Open File

Test Basic clipboard KWs
    ${previous_contents}=  Get Clipboard Value
    Clear Clipboard
    ${clear_contents}=  Get Clipboard Value
    Should be Equal  ${EMPTY}  ${clear_contents}

    Set Clipboard Value  test_string
    ${test_value}=  Get Clipboard Value
    Should Be Equal  ${test_value}  test_string

    [Teardown]
    Set Clipboard Value  ${previous_contents}

Copy To Clipboard and Paste from Clipboard
    [Documentation]  Skipped for now because would require a running application to run KWs
    [Tags]  skip
    Copy To Clipboard  ${test_value}
    Paste From Clipboard

Element KWs
    [Documentation]  Skipped for now because would require a running application to run KWs
    [Tags]  skip
    Find Element
    Find Elements
    Highlight Elements
    Wait For Element

Take Screenshot
    Take Screenshot  filename=${filename}
    [Teardown]
    Remove File  ${filename}

Get Mouse Position and assert it is within display dimensions
    ${x}  ${y}  Get Mouse Position
    ${left}  ${top}  ${right}  ${bottom}  Get Display Dimensions
    Should Be True  ${left} < ${x} and ${x} < ${right}
    Should Be True  ${bottom} > ${y} and ${y} > ${top}

Test Mouse keywords
    [Documentation]  Skipped for now because testing these would require mocks to not get inconsistent failures when mouse is moved during test
    [Tags]  skip
    Drag And Drop
    Move Mouse
    Click
    Click With Offset
    Press Mouse Button
    Release Mouse Button

Test keyboard keywords
    [Documentation]  Skipped for now because testing these would require mocks to not get inconsistent failures when keyboard is used during test
    [Tags]  skip
    Press Keys
    Type Text
    Type Text Into

Test Define Region
    ${region}=          Define Region  100  100  300  300
    ${width}=           Evaluate  $region.width
    ${height}=          Evaluate  $region.height
    Should Be True      ${width} == 200
    Should Be True      ${height} == 200

Test Move Region
    ${region}=          Define Region  100  100  300  300
    ${moved_region}=    Move Region  ${region}  50  50
    ${left}=            Evaluate  $moved_region.left
    ${top}=             Evaluate  $moved_region.top
    ${right}=           Evaluate  $moved_region.right
    ${bottom}=          Evaluate  $moved_region.bottom
    Should Be True      ${left} == 150
    Should Be True      ${top} == 150
    Should Be True      ${right} == 350
    Should Be True      ${bottom} == 350

Test Resize Region All Dimensions
    ${region}=          Define Region  100  100  300  300
    ${moved_region}=    Resize Region  ${region}  left=50  top=50  right=50  bottom=50
    ${left}=            Evaluate  $moved_region.left
    ${top}=             Evaluate  $moved_region.top
    ${right}=           Evaluate  $moved_region.right
    ${bottom}=          Evaluate  $moved_region.bottom
    Should Be True      ${left} == 50
    Should Be True      ${top} == 50
    Should Be True      ${right} == 350
    Should Be True      ${bottom} == 350

Test Resize Region One Dimension
    ${region}=          Define Region  100  100  300  300
    ${moved_region}=    Resize Region  ${region}  right=50
    ${right}=           Evaluate  $moved_region.right
    ${width}=           Evaluate  $moved_region.width
    Should Be True      ${right} == 350
    Should Be True      ${width} == 250
