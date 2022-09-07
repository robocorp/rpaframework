*** Settings ***
Library         OperatingSystem
Library         RPA.Browser.Selenium    locators_path=${LOCATORS}
Library         RPA.FileSystem
Library         RPA.RobotLogListener

Suite Setup     Open Available Browser  about:blank  headless=${TRUE}
Suite Teardown  Close All Browsers

Default Tags    RPA.Browser


*** Variables ***
${RESOURCES}        ${CURDIR}${/}..${/}resources
${RESULTS}          ${CURDIR}${/}..${/}results
${BROWSER_DATA}     ${RESULTS}${/}browser
${LOCATORS}         ${RESOURCES}${/}locators.json
${ALERT_HTML}       file://${RESOURCES}${/}alert.html


*** Keywords ***
My Custom Keyword
    Get Value    id:notexist


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

Open In Incognito With Custom Options
    Close Browser
    ${non_windows} =    Evaluate    not sys.platform.startswith("win")    modules=sys

    ${options} =    Set Variable    add_argument("--incognito")
    IF    ${non_windows}
        ${data_dir} =   Absolute Path   ${BROWSER_DATA}
        RPA.FileSystem.Create Directory    ${data_dir}     parents=${True}
        ${data_dir_op} =   Set Variable     "user-data-dir=${data_dir}"
        ${options} =    Catenate    SEPARATOR=;    ${options}
        ...     add_argument(${data_dir_op})
    END

    Open Available Browser    https://robocorp.com    browser_selection=Chrome
    ...     headless=${True}    options=${options}  port=${18888}

    ${visible} =    Is Element Visible      xpath://button[2]
    Should Be True    ${visible}

    Close Browser
    IF    ${non_windows}
        Directory Should Not Be Empty      ${data_dir}
        RPA.FileSystem.Remove directory    ${data_dir}      recursive=${True}
    END

Open Browser With Dict Options
    @{args} =   Create List     --headless
    &{caps} =   Create Dictionary   acceptInsecureCerts     ${True}
    &{options} =    Create Dictionary   arguments   ${args}     capabilities    ${caps}

    ${driver_path} =   Evaluate    RPA.core.webdriver.download("Chrome")
    ...     modules=RPA.core.webdriver
    Log To Console      Downloaded webdriver path: ${driver_path}
    Open Browser    https://robocorp.com    browser=Chrome      options=${options}
    ...     executable_path=${driver_path}
