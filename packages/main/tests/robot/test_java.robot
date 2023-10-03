*** Settings ***
Library         Process
Library         RPA.FileSystem
Library         String

Suite Setup    Start Demo Application
Suite Teardown    Exit Demo Application
Task Setup      Init Task

Default Tags      windows    skip


*** Variables ***
${RESOURCES}    ${CURDIR}${/}..${/}resources
${TEST_APP_PATH}     ${RESOURCES}${/}test-app
${TITLE}    Chat Frame


*** Keywords ***
Get App Dir
    ${test_app} =    Absolute Path    ${TEST_APP_PATH}
    ${lines} =      Get Lines Matching Pattern      ${test_app}     ${/}${/}*
    IF      "${lines}" != ""
        ${prefix} =     Set Variable        tests${/}
        @{parts} =      Split String    ${test_app}     ${prefix}   ${1}
        ${test_app} =   Set Variable    ${prefix}${parts}[${1}]
    END
    Log To Console      Using Java test app current working directory: ${test_app}
    RETURN      ${test_app}

Start Demo Application
    ${test_app} =   Get App Dir
    Run Process     makejar.bat     shell=${True}    cwd=${test_app}
    Start Process   java    -jar    BasicSwing.jar    ${TITLE}      cwd=${test_app}

Exit Demo Application
    Select Window By Title    ${TITLE}
    Select Menu    FILE    Exit
    Select Window By Title    Exit
    Click Push Button    Exit ok

Init Task
    [Arguments]     ${ignore_callbacks}=${False}    ${disable_refresh}=${False}
    Import Library      RPA.JavaAccessBridge
    ...     ignore_callbacks=${ignore_callbacks}
    ...     disable_refresh=${disable_refresh}

    Select Window By Title    ${TITLE}
    Click Element    role:push button and name:Clear


*** Tasks ***
Test click element
    Click Element    role:push button and name:Send

Test click push button
    Click Push Button    Send
    Click Push Button    Clear

Test print element tree
    ${tree}=    Print Element Tree

Test typing text
    [Tags]   manual

    Type Text    role:text    Textarea text
    ${area_text} =    Get Element Text    role:text    ${0}
    Should Contain    ${area_text}    Textarea text

    Type Text    role:text    some-text
    ...     index=${1}    clear=${True}     typing=${False}
    ${input_text} =    Get Element Text    role:text    ${1}
    Sleep   1s
    Should Be Equal As Strings    some-text    ${input_text}

Test get elements
    ${elements}=    Get Elements    role:text
    ${len}=    Get Length    ${elements}
    Should Be Equal As Integers    ${len}    2
    Log Many    ${elements}[0]
    Log Many    ${elements}[1]
    Highlight Element    ${elements}[0]
    Highlight Element    ${elements}[1]

Test Java Elements
    ${elements}=    Get Elements    role:table > role:text
    Log    Text elements in the table: ${elements}

Test Listing Java Windows
    [Tags]  manual
    @{window_list}=    List Java Windows
    FOR    ${window}    IN    @{window_list}
        IF    "${window.title}" == "my java window title"
            Select Window By PID    ${window.pid}
        END
    END
    IF    len($window_list)==1    Select Window By PID    ${window_list[0].pid}

Test Closing Java Window
    [Tags]  manual
    Select Window By Title    ${TITLE}
    Close Java Window

# Closer to real production scenarios, where callbacks are off and we need to manually
#  refresh elements after they get updated.

Test refreshing updated text area
    [Documentation]  Test the library with callbacks off and no automatic refresh.
    [Tags]  manual
    [Setup]     Init Task   ignore_callbacks=${True}    disable_refresh=${True}

    @{text_elems} =  Get Elements    role:text   java_elements=${True}
    ${text_elem} =      Set Variable    ${text_elems}[${0}]
    Refresh Element     ${text_elem}

    # Insert one line in the text area.
    Click Element    role:push button and name:Send

    # Now check if the text area really contains that line after the refresh happens.
    ${pre_refresh_text} =    Get Element Text    ${text_elem}
    Should Be Empty     ${pre_refresh_text}  # since there was nothing before
    Refresh Element     ${text_elem}
    ${post_refresh_text} =    Get Element Text    ${text_elem}
    Should Not Be Empty     ${post_refresh_text}
