*** Settings ***
Library         OperatingSystem
Library         RPA.Browser.Selenium    locators_path=${LOCATORS}
Library         RPA.FileSystem
Library         RPA.RobotLogListener

Suite Setup     Open Available Browser  about:blank  headless=${TRUE}
Suite Teardown  Close Browsers And Cleanup

Default Tags    RPA.Browser


*** Variables ***
${RESOURCES}    ${CURDIR}${/}..${/}resources
${RESULTS}      ${CURDIR}${/}..${/}results
${BROWSER}      ${RESULTS}${/}browser
${LOCATORS}     ${RESOURCES}${/}locators.json
${ALERT_HTML}   file://${RESOURCES}${/}alert.html


*** Keywords ***
My Custom Keyword
    Get Value    id:notexist

Close Browsers And Cleanup
    Close All Browsers
    Remove directory    ${BROWSER}      recursive=${True}


*** Tasks ***
Does alert contain
    Go To                 ${ALERT_HTML}
    Click Element         //button
    ${res}                Does Alert Contain  after
    Handle Alert          DISMISS

Does alert not contain
    Go To                 ${ALERT_HTML}
    Click Element         //button
    ${res}                Does Alert Not Contain  afterx
    Handle Alert          DISMISS

Basic browser open and usage
    [Tags]  skip
    Open available browser          www.google.com    headless=${TRUE}
    Wait Until Element Is Visible   q
    Input Text                      q  Robocorp
    Click Element                   q
    Press keys                      q    ENTER
    Sleep                           3s
    Screenshot

Check span value
    [Tags]  skip
    Open available Browser    https://www.w3schools.com/tags/att_span.asp    headless=${TRUE}
    ${val}=    Get Value        class:dotcom
    ${elem}=   Get WebElement   class:dotcom
    Log        ${elem.text}

Locator aliases
    [Tags]  skip
    Open Available Browser    https://robotsparebinindustries.com/    headless=${TRUE}
    Input Text      alias:RobotSpareBin.Username    maria
    Input Text      alias:RobotSpareBin.Password    thoushallnotpass
    Submit Form
    Click button when visible   id:logout

Set download directory
    [Tags]  skip
    Set Download Directory  ${OUTPUT_DIR}
    Open Available Browser  https://cdn.robocorp.com/legal/Robocorp-EULA-v1.0.pdf  headless=${TRUE}
    File Should Exist       ${OUTPUT_DIR}${/}Robocorp-EULA-v1.0.pdf
    [Teardown]  Run Keyword And Ignore Error   Remove File  ${OUTPUT_DIR}${/}Robocorp-EULA-v1.0.pdf

Highlight elements
    # TODO: test somehow that the outline is really drawn.
    [Setup]  Open available browser  https://robocorp.com/docs/quickstart-guide  headless=${TRUE}
    Highlight Elements               xpath://h2
    Page Should Contain Element      xpath://h2[@rpaframework-highlight]

Clear all highlights
    [Setup]  Open available browser  https://robocorp.com/docs/quickstart-guide  headless=${TRUE}
    Highlight Elements               xpath://h2
    Clear All Highlights
    Page Should Contain Element      xpath://h2
    Page Should Not Contain Element  xpath://h2[@rpaframework-highlight]

Mute browser failures
    Mute run on failure    My Custom Keyword
    Open Available Browser    https://robotsparebinindustries.com/    headless=${TRUE}
    Run keyword and expect error    *    My Custom Keyword
    Run keyword and expect error    *    Get Value    id:notexist

Open In Incognito
    Close Browser
    ${data_dir} =   Absolute Path   ${BROWSER}
    ${data_dir_op} =   Set Variable     "user-data-dir=${data_dir}"
    Open Available Browser    https://robocorp.com    browser_selection=Chrome
    ...     headless=${True}
    ...     options=add_argument(${data_dir_op});add_argument("--incognito")

    ${visible} =    Is Element Visible      xpath://button[2]
    Should Be True    ${visible}
    Directory Should Exist      ${data_dir}
