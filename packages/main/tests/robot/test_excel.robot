*** Settings ***
Library     RPA.Excel.Files
Library     RPA.FileSystem

Task Teardown   Close Workbook


*** Variables ***
${RESOURCES}    ${CURDIR}${/}..${/}resources


*** Keywords ***
Append Content To Sheet
    [Arguments]    ${excel_file}    ${content}
    ${src} =    Set Variable    ${RESOURCES}${/}${excel_file}
    ${dest} =    Set Variable    ${OUTPUT_DIR}${/}${excel_file}
    Copy File    ${src}    ${dest}
    Open Workbook    ${dest}
    Append Rows To Worksheet    ${content}    header=${True}
    Save Workbook
    ${data} =    Read Worksheet    Sheet    header=${True}
    Should Be Equal    ${data}    ${content}
    Close Workbook


*** Tasks ***
Test single row sheet
    # "Single" in this case acts like header for a 1x1 table.
    &{row} =    Create Dictionary    Single    Test
    @{content} =    Create List    ${row}

    Append Content To Sheet    one-row.xlsx    ${content}
    Append Content To Sheet    one-row.xls    ${content}
    Append Content To Sheet    empty.xlsx    ${content}
    Append Content To Sheet    empty.xls    ${content}
