*** Settings ***
Library           RPA.Excel.Files
Library           RPA.FileSystem
Library           RPA.Tables
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

Create Extended Test Excel
    [Arguments]    ${target_filename}
    ${target_file}=    Set Variable    ${OUTPUT_DIR}${/}${target_filename}
    Copy File    ${EXCELS}${/}extended.xlsx    ${target_file}
    [Return]    ${target_file}

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

Test Clear Cell Ranges
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_clear_cells.xlsx
    Open Workbook    ${testfile}
    Clear Cell Range    A2
    Clear Cell Range    B3:C3
    Save Workbook

Test Styles
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_styles.xlsx
    Open Workbook    ${testfile}
    Set Styles    A1:G4
    ...    bold=True
    ...    cell_fill=lightblue
    ...    align_horizontal=center
    ...    number_format=h:mm
    ...    font_name=Arial
    ...    size=24
    Save Workbook

Test Auto Size
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_autosize.xlsx
    Open Workbook    ${testfile}
    Auto Size Columns    B    D    16
    Auto Size Columns    A    width=32
    Save Workbook

Test Delete Rows
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_delete_rows.xlsx
    Open Workbook    ${testfile}
    Delete Rows    2
    Save Workbook

Test Insert Column
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_insert_column.xlsx
    Open Workbook    ${testfile}
    Insert Columns After    C    2
    Insert Columns Before    C    2
    Save Workbook

Test Copy Cell Values
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_copy_cells.xlsx
    Open Workbook    ${testfile}
    Copy Cell Values    A1:D4    J5
    Save Workbook

Test Hide Columns
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_hidden.xlsx
    Open Workbook    ${testfile}
    Hide Columns    B
    Save Workbook

Test Unhide Columns
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_unhidden.xlsx
    Open Workbook    ${testfile}
    Unhide Columns    B
    Save Workbook

Test Set Cell Formula
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_formulas_transpose_true.xlsx
    Open Workbook    ${testfile}
    Set Cell Formula    E2:E10    =B2+5    True
    Save Workbook
    ${testfile}=    Create Extended Test Excel    test_formulas_transpose_false.xlsx
    Open Workbook    ${testfile}
    Set Cell Formula    E2:E10    =B2+5
    Save Workbook

Test Delete Columns
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_delete_columns.xlsx
    Open Workbook    ${testfile}
    Delete Columns    G
    Save Workbook

Test Insert Rows
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_insert_rows.xlsx
    Open Workbook    ${testfile}
    Insert Rows Before    1    3
    Insert Rows After    1    3
    Save Workbook

Test Move Range
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_move_range.xlsx
    Open Workbook    ${testfile}
    Move Range    A1:D4    3
    Save Workbook

Test Set Cell Values
    [Tags]    release-19.3.0
    ${testfile}=    Create Extended Test Excel    test_set_values.xlsx
    Open Workbook    ${testfile}
    @{all_rows}=    Create List
    ${headers}=    Create List    first    second    third    fourth
    FOR    ${num}    IN RANGE    1    20
        @{row}=    Create List    ${num}    ${num+1}    ${num*2}    ${num*4}
        Append To List    ${all_rows}    ${row}
    END
    ${table}=    Create Table    ${all_rows}    columns=${headers}
    @{values}=    Evaluate    [[1,2,3],[4,5,6],['a','b','c','d']]
    Set Cell Values    JJ1    ${values}
    Set Cell Values    G1    ${table}    True
    Save Workbook
