*** Settings ***
Library         RPA.Desktop.Clipboard
Library         String
Default Tags    RPA.Desktop.Clipboard
Force tags      skip  # TODO. Does not work on Github Action Ubuntu

*** Variable ***
${DEFAULT_CLIPBOARD_CONTENT}   copying test text into clipboard

*** Tasks ***
Text from clipboard
    [Tags]    RPA.Browser
    Copy To Clipboard           ${DEFAULT_CLIPBOARD_CONTENT}
    ${textfromclipboard}=       Paste From Clipboard
    Should Be Equal As Strings  ${textfromclipboard}  ${DEFAULT_CLIPBOARD_CONTENT}

Special characters
    Set Task Variable           ${CLIPBOARD_TEXT}   äöåÖÅÄ¢¢4$$$€€€è
    Copy To Clipboard           ${CLIPBOARD_TEXT}
    ${textfromclipboard}=       Paste From Clipboard
    Should Be Equal As Strings  ${textfromclipboard}  ${CLIPBOARD_TEXT}

Clear clipboard
    Copy To Clipboard           ${DEFAULT_CLIPBOARD_CONTENT}
    ${textfromclipboard}=       Paste From Clipboard
    Should Be Equal As Strings  ${textfromclipboard}  ${DEFAULT_CLIPBOARD_CONTENT}
    Clear Clipboard
    ${textfromclipboard}=       Paste From Clipboard
    Should Be True              "${textfromclipboard}" == "${NONE}" or "${textfromclipboard}" == "${EMPTY}"