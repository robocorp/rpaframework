*** Settings ***
Library           RPA.Excel.Files
Library           RPA.FileSystem
Library           Collections
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
    [Arguments]    ${rows}    ${target_filepath}    ${expected_empty_row}    ${formatting}=${False}
    Open Workbook    ${target_filepath}
    Append Rows to Worksheet    ${rows}    formatting_as_empty=${formatting}
    Save Workbook
    Close Workbook
    Open Workbook    ${target_filepath}
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

Test appending XLSX content when formatted cell is considered empty
    ${target_file}=    Set Variable    ${OUTPUT_DIR}${/}target1.xlsx
    Copy File    ${EXCELS}${/}data_template.xlsx    ${target_file}
    ${rows1}=    Read Rows From Worksheet    data1.xlsx
    Append Rows To Target    ${rows1}    ${target_file}    42    ${True}
    ${rows2}=    Read Rows From Worksheet    data2.xlsx
    Append Rows To Target    ${rows2}    ${target_file}    42    ${True}

Test default appending content
    ${target_file}=    Set Variable    ${OUTPUT_DIR}${/}target2.xlsx
    Copy File    ${EXCELS}${/}data_template.xlsx    ${target_file}
    ${rows1}=    Read Rows From Worksheet    data1.xlsx
    Append Rows To Target    ${rows1}    ${target_file}    52
    ${rows2}=    Read Rows From Worksheet    data2.xlsx
    Append Rows To Target    ${rows2}    ${target_file}    62

Test append rows to a target file
    @{rows} =    Create List
    FOR    ${counter}    IN RANGE    1    51
        &{row} =    Create Dictionary
        ...    Name    Cosmin
        ...    Age    29
        ...    E-mail    cosmin@robocorp.com
        Append To List    ${rows}    ${row}
    END
    ${workbook} =    Set Variable    ${OUTPUT_DIR}${/}emails.xlsx
    Copy File    ${EXCELS}${/}data_template.xlsx    ${workbook}
    Open Workbook    ${workbook}
    Append Rows to Worksheet    ${rows}    formatting_as_empty=${True}
    ${empty_row_number}=    Find Empty Row
    Save Workbook
    Should Be Equal As Integers    52    ${empty_row_number}

Test appending XLS content when formatted cell is considered empty
    ${target_file}=    Set Variable    ${OUTPUT_DIR}${/}target1.xls
    Copy File    ${EXCELS}${/}data_template.xls    ${target_file}
    ${rows1}=    Read Rows From Worksheet    data1.xls
    Append Rows To Target    ${rows1}    ${target_file}    12    ${True}
    ${rows2}=    Read Rows From Worksheet    data2.xls
    Append Rows To Target    ${rows2}    ${target_file}    22    ${True}
