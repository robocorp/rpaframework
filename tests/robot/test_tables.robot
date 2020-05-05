*** Settings ***
Library    RPA.Tables
Library    RPA.FileSystem
Library    RPA.Excel.Files


*** Variables ***
${ORDERS_FILE}    ${CURDIR}${/}..${/}resources${/}example.xlsx

*** Tasks ***
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

*** Keywords ***
List group IDs
    [Arguments]    ${rows}
    FOR    ${row}    IN    @{rows}
        Log    ${row}[Id]
    END
