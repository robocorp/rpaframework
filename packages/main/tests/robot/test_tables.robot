*** Settings ***
Library    RPA.Tables
Library    RPA.FileSystem
Library    RPA.Excel.Files

*** Variables ***
${ORDERS_FILE}    ${CURDIR}${/}..${/}resources${/}example.xlsx

*** Tasks ***
Create table literal
    ${table}=    Create table    [[1,2,3],[4,5,6]]
    Should be true    $table.size == 2

Files to Table
    ${files}=    List files in directory    ${CURDIR}
    ${files}=    Create table    ${files}
    Filter table by column    ${files}    size  >=  ${1024}
    FOR    ${file}    IN    @{files}
        Log    ${file}[name]
    END
    Write table to CSV    ${files}    ${OUTPUT_DIR}${/}files.csv

Excel to Table
    ${workbook}=      Open workbook    ${ORDERS_FILE}
    ${worksheet}=     Read worksheet   header=${TRUE}
    ${table}=         Create table     ${worksheet}
    ${groups}=        Group table by column    ${table}    Date
    FOR    ${rows}    IN    @{groups}
        List group IDs    ${rows}
    END

Table With Non-identifier Columns
    ${data}=    Create dictionary    123=asd    _\\1=33    cool key=value
    ${table}=   Create table    ${data}
    FOR    ${row}    IN    @{table}
        Log    ${row}[123]
        Log    ${row}[_\\1]
        Log    ${row}[cool key]
    END

Get Table Cell Errors
    ${table}=    Create table   [[1,2,3], [4,5,6]]    columns=['One','Two','Three']

    Assert cell value    ${table}    0     0        1
    Assert cell value    ${table}    1     1        5
    Assert cell value    ${table}    1     Three    6

    Assert cell error    ${table}    5     0       *out of range*
    Assert cell error    ${table}    1     3       *out of range*
    Assert cell error    ${table}    1     Four    *Unknown column name*
    Assert cell error    ${table}    Test  0       *integer*

*** Keywords ***
List group IDs
    [Arguments]    ${rows}
    FOR    ${row}    IN    @{rows}
        Log    ${row}[Id]
    END

Assert cell value
    [Arguments]    ${table}  ${row}  ${column}  ${value}
    ${result}=    Get table cell   ${table}  ${row}  ${column}
    Should be equal as integers    ${result}    ${value}


Assert cell error
    [Arguments]    ${table}  ${row}  ${column}    ${error}
    Run keyword and expect error     ${error}
    ...    Get table cell   ${table}  ${row}  ${column}
