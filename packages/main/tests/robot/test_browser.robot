*** Settings ***
Library         RPA.Browser    locators_path=${LOCATORS}
Suite Teardown  Close All Browsers
Default Tags    RPA.Browser
Force Tags      skip

*** Variables ***
${LOCATORS}    ${CURDIR}${/}..${/}resources${/}locators.json

*** Tasks ***
Basic browser open and usage
    Open available browser          https://www.google.com/    headless=${TRUE}
    Wait Until Element Is Visible   q
    Input Text                      q  Robocorp
    Click Element                   q
    Press keys                      q    ENTER
    Sleep                           3s
    Screenshot

Check span value
    Open available Browser    https://www.w3schools.com/tags/att_span.asp    headless=${TRUE}
    ${val}=    Get Value        class:dotcom
    ${elem}=   Get WebElement   class:dotcom
    Log        ${elem.text}

Locator aliases
    Open Available Browser    https://robotsparebinindustries.com/    headless=${TRUE}
    Input Text      alias:RobotSpareBin.Username    maria
    Input Text      alias:RobotSpareBin.Password    thoushallnotpass
    Submit Form
    Wait Until Page Contains Element    id:logout
