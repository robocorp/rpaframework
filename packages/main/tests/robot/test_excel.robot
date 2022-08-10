*** Settings ***
Library           RPA.Excel.Files
Library           RPA.FileSystem
Task Teardown     Close Workbook

*** Variables ***
${RESOURCES}      ${CURDIR}${/}..${/}resources
${EXCELS}         ${RESOURCES}${/}excels

*** Keywords ***
Append Content To Sheet
    [Arguments]    ${excel_file}    ${content}
    ${src} =    Set Variable    ${EXCELS}${/}${excel_file}
    ${dest} =    Set Variable    ${OUTPUT_DIR}${/}${excel_file}
    Copy File    ${src}    ${dest}
    Open Workbook    ${dest}
    Append Rows To Worksheet    ${content}    header=${True}
    Save Workbook
    ${data} =    Read Worksheet    Sheet    header=${True}
    Should Be Equal    ${data}    ${content}
    Close Workbook

Read Rows From Worksheet
    [Arguments]    ${excel_file}
    ${src} =    Set Variable    ${EXCELS}${/}${excel_file}
    ${dest} =    Set Variable    ${OUTPUT_DIR}${/}${excel_file}
    Copy File    ${src}    ${dest}
    Open Workbook    ${dest}
    ${rows}=    Read Worksheet    header=True
    Close Workbook
    [Return]    ${rows}

Append Rows to Target
    [Arguments]    ${rows}    ${target_filepath}    ${expected_empty_row}
    Open Workbook    ${target_filepath}
    Append Rows to Worksheet    ${rows}    #formatting_as_empty=True
    Save Workbook
    ${empty_row_number}=    Find Empty Row
    Should Be Equal As Integers    ${expected_empty_row}    ${empty_row_number}
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

Test appending content from source files to single target
    Copy File    ${EXCELS}${/}data_template.xlsx    ${OUTPUT_DIR}${/}target1.xlsx
    ${rows1}=    Read Rows From Worksheet    data1.xlsx
    Append Rows To Target    ${rows1}    ${OUTPUT_DIR}${/}target1.xlsx    52
    ${rows2}=    Read Rows From Worksheet    data1.xlsx
    Append Rows To Target    ${rows1}    ${OUTPUT_DIR}${/}target1.xlsx    62
