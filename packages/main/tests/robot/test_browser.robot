*** Settings ***
Library             Collections
Library             OperatingSystem
Library             RPA.Browser.Selenium    locators_path=${LOCATORS}
Library             RPA.FileSystem
Library             RPA.RobotLogListener

Suite Setup         Open Available Browser    about:blank    headless=${True}
...                     browser_selection=Chrome
Suite Teardown      RPA.Browser.Selenium.Close All Browsers

Default Tags        rpa.browser


*** Variables ***
${RESOURCES}        ${CURDIR}${/}..${/}resources
${RESULTS}          ${CURDIR}${/}..${/}results
${BROWSER_DATA}     ${RESULTS}${/}browser
${LOCATORS}         ${RESOURCES}${/}locators.json
${ALERT_HTML}       file://${RESOURCES}${/}alert.html
${USER_AGENT}       Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/1337.0.0.0 Safari/1337.36


*** Keywords ***
My Custom Keyword
    Get Value    id:notexist

Create Browser Data Directory
    ${data_dir} =    Absolute Path    ${BROWSER_DATA}
    RPA.FileSystem.Create Directory    ${data_dir}    parents=${True}
    RPA.FileSystem.Empty Directory     ${data_dir}
    RETURN    ${data_dir}

Download With Specific Browser
    [Arguments]    ${browser}
    Close Browser

    Set Download Directory    ${OUTPUT_DIR}
    Open Available Browser    https://robocorp.com/docs/security
    ...    browser_selection=${browser}
    ...    headless=${True}    # PDF downloading now works in headless as well
    Click Link    Data protection whitepaper

    ${file_path} =    Set Variable
    ...    ${OUTPUT_DIR}${/}security-and-data-protection-whitepaper.pdf
    Wait Until Keyword Succeeds    3x    1s    File Should Exist    ${file_path}

    [Teardown]    Run Keyword And Ignore Error
    ...    RPA.FileSystem.Remove File    ${file_path}


# Tasks which rely on the already open browser in headless mode.
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
    # NOTE(cmin764): As of 19.05.2023 this test passes in CI, Mac, Windows and
    #  Control Room, without any consent popup blocker.
    # NOTE(mikahanninen): Skipped on 02.06.2023 as this fails on the local build on
    #  consent form, which for me is also using the Finnish Google site.
    [Tags]  skip  # since this might fail in the future if the website changes
    Go To    www.google.com
    Click Element If Visible    xpath://button[2]  # test fails if this is missed
    Wait Until Element Is Visible    q

    Input Text    q    Robocorp
    Click Element    q
    Sleep   1s
    Press Keys    q    ENTER
    Wait Until Element Is Visible    css:div.logo

    ${output_path} =    Screenshot    css:div.logo
    ...    filename=${BROWSER_DATA}${/}google-logo.png
    File Should Exist    ${output_path}

    ${output_path} =    Screenshot
    ...    filename=${BROWSER_DATA}${/}google-robocorp-result.png
    File Should Exist    ${output_path}
    Log To Console    Full page screenshot: ${output_path}

Check button value
    Go To    https://www.easytestmaker.com

    ${locator} =    Set Variable    xpath://input[@type='hidden']
    ${element} =    Get WebElement    ${locator}
    ${value} =    Get Value    ${element}
    Log To Console    Token: ${value}

Locator aliases
    Go To    https://robotsparebinindustries.com/

    Input Text    alias:RobotSpareBin.Username    maria
    Input Text    alias:RobotSpareBin.Password    thoushallnotpass
    Submit Form

    Click Button When Visible    id:logout
    Click Element When Visible    alias:RobotSpareBin.Order
    Click Button When Visible    alias:RobotSpareBin.Yep

Print page as PDF document
    Go To    https://robotsparebinindustries.com/
    ${data_dir} =    Create Browser Data Directory
    ${destination_path} =    Set Variable    ${data_dir}${/}printed-page.pdf
    Log To Console    Printing page into: ${destination_path}
    ${output_path} =    Print To Pdf    ${destination_path}
    File Should Exist    ${output_path}
    [Teardown]    Run Keyword And Ignore Error
    ...    RPA.FileSystem.Remove File    ${output_path}

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
    [Setup]    Go To    https://robotsparebinindustries.com/

    Mute run on failure    My Custom Keyword
    Run keyword and expect error    *    My Custom Keyword
    Run keyword and expect error    *    Get Value    id:notexist

Get and set an attribute
    [Setup]    Go To    https://robotsparebinindustries.com/

    ${button_locator} =    Set Variable    xpath://button[@type="submit"]
    ${button} =    Get WebElement    ${button_locator}
    ${class} =    Get Element Attribute    ${button}    class
    Should Be Equal    ${class}    btn btn-primary

    Set Element Attribute    ${button}    class    btn btn-secondary
    ${class} =    Get Element Attribute    ${button_locator}    class
    Should Be Equal    ${class}    btn btn-secondary

Set user agent with CDP command
    &{params} =    Create Dictionary    userAgent    ${USER_AGENT}
    Execute CDP    Network.setUserAgentOverride    ${params}
    Go To    https://robocorp.com

Test enhanced clicking
    [Setup]    Go To    ${ALERT_HTML}

    Click Element When Clickable    //button
    Does Alert Contain    after

Test Shadow Root
    [Tags]    skip  # flaky test during async runs
    [Setup]    Is Alert Present

    Go To    http://watir.com/examples/shadow_dom.html

    ${shadow_elem} =    Get WebElement    css:#shadow_host    shadow=${True}
    ${elem} =    Get WebElement    css:#shadow_content    parent=${shadow_elem}
    ${text} =    Get Text    ${elem}
    Should Be Equal    ${text}    some text

Maximize window in headless mode
    Maximize Browser Window     force=${False}  # forcing it works locally only


# Tasks which close the already open browser and opens a new one, most probably in
#  non-headless mode.
*** Tasks ***
Download PDF in custom Firefox directory
    [Tags]    manual  # no guaranteed support for the Firefox browser in CI/dev env
    Download With Specific Browser    Firefox

Download PDF in custom Chrome directory
    [Tags]    skip  # flaky test in CI, mainly on Windows with Python 3.8
    Download With Specific Browser    Chrome

Open Browser With Dict Options
    [Tags]    skip  # flaky test in CI, on Windows and Linux, but not on Mac
    [Setup]    Close Browser

    @{args} =    Create List    --headless=new  # this is a newly introduced argument
    &{caps} =    Create Dictionary    acceptInsecureCerts    ${True}
    &{options} =    Create Dictionary
    ...     arguments    ${args}
    ...     capabilities    ${caps}

    ${driver_path} =    Evaluate    RPA.core.webdriver.download("Chrome")
    ...    modules=RPA.core.webdriver
    Log To Console    Downloaded webdriver path: ${driver_path}

    ${log_path} =   Set Variable    ${BROWSER_DATA}${/}browser.log
    Open Browser    https://robocorp.com/docs    browser=Chrome    options=${options}
    ...    executable_path=${driver_path}   service_log_path=${log_path}
    ${visible} =    Is Element Visible    xpath://button[contains(@class, "desktop")]
    Should Be True    ${visible}

Open In Incognito With Custom Options
    [Documentation]    Test Chrome with custom options (incognito), port and explicit
    ...    profile directory.
    [Setup]    Close Browser
    # NOTE(cmin764): In CI, Chrome may attract a buggy webdriver which makes the custom
    #  profile usage to break in headless mode. (unknown error: unable to discover open
    #  pages)

    ${data_dir} =    Create Browser Data Directory
    ${options} =    Set Variable    add_argument("--incognito")

    Open Available Browser    https://robocorp.com/docs    browser_selection=Chrome
    ...    headless=${True}    options=${options}    port=${18888}
    # Custom profile usage now works in headless mode as well. (but not guaranteed
    #  with older browser versions)
    ...    use_profile=${True}    profile_path=${data_dir}

    ${visible} =    Is Element Visible    xpath://button[contains(@class, "desktop")]
    Should Be True    ${visible}
    Directory Should Not Be Empty    ${data_dir}

    Close Browser
    [Teardown]    RPA.FileSystem.Remove Directory    ${data_dir}    recursive=${True}

Open Edge in IE mode with profile
    [Documentation]     Prove that we have support for profile usage since the IE
    ...    webdriver still opens Edge but in IE mode and still supports setting an user
    ...    data dir.
    [Setup]     Close Browser
    [Tags]      windows     skip  # windows specific test without headless support

    ${data_dir} =    Create Browser Data Directory
    Open Available Browser    https://robocorp.com/docs    browser_selection=Ie
    ...    use_profile=${True}    profile_path=${data_dir}    profile_name=Default
    # NOTE(cmin764; 14 Sep 2023): Currently there's a patch in the webdriver binary not
    #  overriding the user data dir we're trying to set.
    Run Keyword And Ignore Error    Directory Should Not Be Empty    ${data_dir}

    [Teardown]      RPA.FileSystem.Remove Directory    ${data_dir}    recursive=${True}

Open Edge in normal and IE mode without closing
    [Documentation]     Downloads fresh webdrivers and starts Edge in normal and IE
    ...    mode on a Windows machine without auto-closing the browser at the end of
    ...    the execution. (on Windows the webdrivers will be closed but the browser
    ...    stays open)
    [Tags]      windows     skip  # requires Windows OS with UI
    [Setup]    Close Browser

    ${webdrivers_dir} =     Evaluate    RPA.core.webdriver.DRIVER_ROOT
    ...     modules=RPA.core.webdriver
    RPA.FileSystem.Remove Directory    ${webdrivers_dir}    recursive=${True}

    ${msg} =    Catenate    SEPARATOR=${SPACE}   This test will leave the browsers open
    ...     intentionally in order to test the driver shutdown without affecting the
    ...     left open browser instances.
    Log To Console     ${msg}
    Import Library      RPA.Browser.Selenium    auto_close=${False}
    ...     WITH NAME   Selenium

    &{edge_check} =  Create Dictionary
    ...    browser     Edge
    ...    url   https://robocorp.com/docs
    ...    text     Portal
    &{ie_check} =  Create Dictionary
    ...    browser     Ie
    ...    url   https://demos.telerik.com/aspnet-ajax/salesdashboard/views/about.aspx
    ...    text     Telerik
    @{checks} =   Create List    ${edge_check}     ${ie_check}

    FOR    ${check}    IN    @{checks}
        Selenium.Open Available Browser   ${check}[url]
        ...     browser_selection=${check}[browser]
        ...     headless=${False}   download=${True}
        Selenium.Page Should Contain   ${check}[text]
    END
