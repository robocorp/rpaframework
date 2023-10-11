*** Settings ***
Library         Collections
Library         Process
Library         RPA.FileSystem
Library         String

Suite Setup    Start Demo Application
Suite Teardown    Exit Demo Application
Task Setup      Init Library And Reset App

Default Tags      windows    skip


*** Variables ***
${RESOURCES}    ${CURDIR}${/}..${/}resources
${TEST_APP_PATH}     ${RESOURCES}${/}test-app
${TITLE}    Chat Frame
${JAVA_LIB}     ${None}


*** Keywords ***
Get App Dir
    ${test_app} =    Absolute Path    ${TEST_APP_PATH}
    ${lines} =      Get Lines Matching Pattern      ${test_app}     ${/}${/}*
    IF      "${lines}" != ""
        # Use relative paths for known issues with mounted drives.
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

Init Library And Reset App
    [Arguments]     ${ignore_callbacks}=${False}    ${disable_refresh}=${False}

    IF  not $JAVA_LIB
        Import Library      RPA.JavaAccessBridge
        ...     ignore_callbacks=${ignore_callbacks}
        ...     disable_refresh=${disable_refresh}
        ${java_lib} =   Get Library Instance    RPA.JavaAccessBridge
        Set Global Variable     ${JAVA_LIB}     ${java_lib}
    END

    # Ensure the right settings for already imported libraries with different options.
    ${JAVA_LIB.ignore_callbacks} =  Set Variable    ${ignore_callbacks}
    ${JAVA_LIB.disable_refresh} =  Set Variable    ${disable_refresh}
    ${JAVA_LIB.jab_wrapper} =  Set Variable    ${None}

    # Take window into focus, rebuild the element tree and clear text.
    Select Window By Title    ${TITLE}
    Click Element    role:push button and name:Clear


*** Tasks ***
Test click element
    Click Element    role:push button and name:Send

Test click push button
    Click Push Button    Send
    Click Push Button    Clear

Test print element tree
    ${tree} =    Print Element Tree

Test typing text
    [Tags]   manual  # flaky inconsistent behaviour

    Type Text    role:text    Textarea text
    Sleep   1s
    ${area_text} =    Get Element Text    role:text    ${0}
    Should Contain    ${area_text}    Textarea text

    Type Text    role:text    some-text
    ...     index=${1}    clear=${True}     typing=${False}
    ${input_text} =    Get Element Text    role:text    ${1}
    Sleep   1s
    Should Be Equal As Strings    some-text    ${input_text}

Test get elements
    @{elements} =    Get Elements    role:text
    ${len} =    Get Length    ${elements}
    Should Be Equal As Integers    ${len}    2
    ${first_text_elem} =    Set Variable    ${elements}[${0}]
    ${second_text_elem} =    Set Variable    ${elements}[${1}]

    Log    First text element: ${first_text_elem}
    Highlight Element    ${first_text_elem}
    Log    Second text element: ${second_text_elem}
    Highlight Element    ${second_text_elem}

    @{actions} =    Get Element Actions     ${first_text_elem}
    Log List    ${actions}

Test Java elements
    ${previous} =   Set Display Scale Factor    ${2}
    Set Display Scale Factor    ${previous}

    @{elements} =    Get Elements    role:table > role:label
    Log    Text elements inside the table:
    Log List    ${elements}

Test listing Java windows
    [Tags]  manual  # requires window with specific title
    @{window_list} =    List Java Windows
    FOR    ${window}    IN    @{window_list}
        IF    "${window.title}" == "my java window title"
            Select Window By PID    ${window.pid}
        END
    END
    IF    len($window_list)==1    Select Window By PID    ${window_list[0].pid}

Test closing Java window
    [Tags]  manual  # fails the other tests when closing the session app
    Select Window By Title    ${TITLE}
    Close Java Window

# Closer to real production scenarios, where callbacks are off and we need to manually
#  refresh elements after they get updated.

Test refreshing updated text area
    [Documentation]  Test the library with callbacks off and no automatic refresh.
    [Setup]     Init Library And Reset App   ignore_callbacks=${True}
    ...     disable_refresh=${True}  # just to make sure we don't get any at all

    # Get the initially empty text area as Java element.
    @{text_elems} =  Get Elements    role:text   java_elements=${True}
    ${text_elem} =      Set Variable    ${text_elems}[${0}]
    Refresh Element     ${text_elem}
    # Insert one line in the text area.
    Click Element    role:push button and name:Send

    # Now check if the text area really contains that line after the refresh happens.
    ${pre_refresh_text} =    Get Element Text    role:text
    Should Be Empty     ${pre_refresh_text}  # since there was nothing before
    ${text_elem} =      Refresh Element     role:text
    ${post_refresh_text} =    Get Element Text    ${text_elem}
    Should Not Be Empty     ${post_refresh_text}

Test table rows retrieval
    [Documentation]   Check for visible vs. all children.
    [Setup]     Init Library And Reset App   ignore_callbacks=${True}
    ...     disable_refresh=${False}  # for table auto-refresh

    @{visible_rows} =    Read Table    role:table
    Log List    ${visible_rows}
    @{all_rows} =    Read Table    role:table   visible_only=${False}
    Log List    ${all_rows}

    ${visible_count} =      Get Length   ${visible_rows}
    ${all_count} =      Get Length   ${all_rows}
    Should Not Be Equal As Integers     ${visible_count}    ${all_count}

Test clicking after moving window
    [Documentation]   Get a button and click it after moving the window to see if the
    ...     explicit refresh updates the coordinates accordingly.
    [Tags]   manual  # since it requires manual intervetion to prove useful
    [Setup]     Init Library And Reset App      ignore_callbacks=${True}

    @{send_elems} =     Get Elements    role:push button and name:Send
    ${send_elem} =  Set Variable    ${send_elems}[${0}]
    Log     Pre-refresh: ${send_elem}  # initial coordinates before moving the window

    Log To Console      Move the window within 5 seconds...
    Sleep   5s

    # Clicking works even without a refresh.
    Refresh Element     ${send_elem}
    Log     Post-refresh: ${send_elem}  # displays different coordinates now
    Click Element   ${send_elem}
    Sleep   2s      # to observe the result
