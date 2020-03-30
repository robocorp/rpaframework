*** Settings ***
Library         RPA.Browser
Suite Teardown  Close All Browsers
Default Tags    RPA.Browser
Force tags      skip

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
    Open available browser      https://www.w3schools.com/tags/att_span.asp    headless=${TRUE}
    ${val}=    Get Value        class:dotcom
    ${elem}=   Get WebElement   class:dotcom
    Log        ${elem.text}