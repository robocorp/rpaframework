*** Settings ***
Library     RPA.Word.Application    autoexit=${False}

Suite Setup         Open Application    visible=${True}     display_alerts=${True}
Suite Teardown      Quit Application

Default Tags      windows   skip  # no Word app in CI


*** Variables ***
${RESULTS}      ${CURDIR}${/}..${/}results
${DOC}          ${RESULTS}${/}robocorp_story.docx


*** Keywords ***
Ensure Document
    Create New Document

    Set Header          11.03.2020
    Write Text          This is an educational story of a company called Robocorp.
    Set Footer          Author: Mika Hänninen
    Save Document As    ${DOC}

    [Teardown]      Close Document      save_changes=${True}


*** Tasks ***
Create document and export as PDF
    [Setup]     Ensure Document

    Open File    ${DOC}     read_only=${False}
    ${out_pdf} =    Set Variable    ${RESULTS}${/}robocorp_story.pdf
    Export To PDF   ${out_pdf}  # export initially as it is
    Replace Text        educational  inspirational
    Export To PDF   ${out_pdf}  # export one more time to check replacement
    Log To Console      Output PDF: ${out_pdf}

    [Teardown]      Close Document  # not saving changes this time
