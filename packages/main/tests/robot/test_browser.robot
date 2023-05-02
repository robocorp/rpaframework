*** Settings ***
Library             OperatingSystem
Library             RPA.Browser.Selenium    locators_path=${LOCATORS}
Library             RPA.FileSystem
Library             RPA.RobotLogListener

Suite Setup         Open Available Browser    about:blank    headless=${True}
Suite Teardown      Close All Browsers

Default Tags        rpa.browser


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
    Go To    ${ALERT_HTML}
    Click Element    //button
    ${res} =    Does Alert Contain    after
    Handle Alert    DISMISS

Does alert not contain
    Go To    ${ALERT_HTML}
    Click Element    //button
    ${res} =    Does Alert Not Contain    afterx
    Handle Alert    DISMISS

Screenshot Robocorp Google search result
    [Tags]    skip
    # Marked as SKIP on 2.5.2023 as this test does not
    # handle Google consent popup and thus fails
    Go To    www.google.com
    Wait Until Element Is Visible    q

    Input Text    q    Robocorp
    Click Element    q
    Press Keys    q    ENTER
    Wait Until Element Is Visible   css:div.logo

    ${output_path} =    Screenshot      css:div.logo
    ...     filename=${BROWSER_DATA}${/}google-logo.png
    File Should Exist   ${output_path}

    ${output_path} =    Screenshot
    ...     filename=${BROWSER_DATA}${/}google-robocorp-result.png
    File Should Exist   ${output_path}
    Log To Console     Full page screenshot: ${output_path}

Check button value
    Go To    https://www.easytestmaker.com

    ${locator} =    Set Variable    xpath://input[@type='hidden']
    ${element} =   Get WebElement       ${locator}
    ${value} =    Get Value     ${element}
    Log To Console  Token: ${value}

Locator aliases
    Go To    https://robotsparebinindustries.com/

    Input Text    alias:RobotSpareBin.Username    maria
    Input Text    alias:RobotSpareBin.Password    thoushallnotpass
    Submit Form

    Click Button When Visible    id:logout
    Click Element When Visible      alias:RobotSpareBin.Order
    Click Button When Visible   alias:RobotSpareBin.Yep

Print page as PDF document
    Go To    https://robotsparebinindustries.com/

    ${destination_path} =      Set Variable    ${BROWSER_DATA}${/}printed-page.pdf
    Log To Console     Printing page into: ${destination_path}
    ${output_path} =    Print To Pdf    ${destination_path}
    File Should Exist   ${output_path}

Download PDF in custom directory
    [Setup]     Close Browser

    Set Download Directory    ${OUTPUT_DIR}
    ${file_name} =   Set Variable    Robocorp-EULA-v1.0.pdf
    Open Available Browser    https://cdn.robocorp.com/legal/${file_name}
    ...    headless=${True}  # PDF downloading now works in headless as well
    Go To   robocorp.com  # this starts after the PDF above gets downloaded
    ${file_path} =      Set Variable    ${OUTPUT_DIR}${/}${file_name}
    File Should Exist   ${file_path}

    [Teardown]    Run Keyword And Ignore Error
    ...     RPA.FileSystem.Remove File   ${file_path}

Highlight elements
    [Setup]    Go To    https://robocorp.com/docs/quickstart-guide

    # TODO: test somehow that the outline is really drawn.
    Highlight Elements    xpath://h2
    Page Should Contain Element    xpath://h2[@rpaframework-highlight]

Clear all highlights
    [Setup]    Go To    https://robocorp.com/docs/quickstart-guide

    Highlight Elements    xpath://h2
    Clear All Highlights
    Page Should Contain Element    xpath://h2
    Page Should Not Contain Element    xpath://h2[@rpaframework-highlight]

Mute browser failures
    [Setup]     Go To   https://robotsparebinindustries.com/

    Mute run on failure    My Custom Keyword
    Run keyword and expect error    *    My Custom Keyword
    Run keyword and expect error    *    Get Value    id:notexist

Open In Incognito With Custom Options
    [Documentation]     Test Chrome with custom options (incognito), port and explicit
    ...     profile directory.
    # In CI, Chrome may attract a buggy webdriver which makes the custom profile usage
    #  to break in headless mode. (unknown error: unable to discover open pages)
#    [Tags]  skip
    [Setup]     Close Browser

    ${data_dir} =    Absolute Path    ${BROWSER_DATA}
    RPA.FileSystem.Create Directory    ${data_dir}    parents=${True}
    ${options} =    Set Variable    add_argument("--incognito")

    Open Available Browser    https://robocorp.com    browser_selection=Chrome
    ...    headless=${True}    options=${options}    port=${18888}
    # Custom profile usage now works in headless mode as well. (but not guaranteed
    #  with older browser versions)
    ...    use_profile=${True}      profile_path=${data_dir}

    ${visible} =    Is Element Visible    xpath://button[2]
    Should Be True    ${visible}
    Directory Should Not Be Empty    ${data_dir}

    Close Browser
    [Teardown]  RPA.FileSystem.Remove directory    ${data_dir}    recursive=${True}

Open Browser With Dict Options
    [Setup]     Close Browser

    @{args} =    Create List    --headless=new
    &{caps} =    Create Dictionary    acceptInsecureCerts    ${True}
    &{options} =    Create Dictionary    arguments    ${args}    capabilities    ${caps}

    ${driver_path} =    Evaluate    RPA.core.webdriver.download("Chrome")
    ...    modules=RPA.core.webdriver
    Log To Console    Downloaded webdriver path: ${driver_path}

    Open Browser    https://robocorp.com    browser=Chrome    options=${options}
    ...    executable_path=${driver_path}
    ${visible} =    Is Element Visible    xpath://button[2]
    Should Be True    ${visible}
