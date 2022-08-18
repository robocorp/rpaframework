*** Settings ***
Library           Collections
Library           DateTime
Library           RPA.Tables
Library           RPA.FileSystem
Library           RPA.Excel.Files

*** Variables ***
${ORDERS_FILE}    ${CURDIR}${/}..${/}resources${/}excels${/}example.xlsx

*** Tasks ***
Create table literal
    ${table}=    Create table    [[1,2,3],[4,5,6]]
    Should be true    $table.size == 2

Files to Table
    ${files}=    List files in directory    ${CURDIR}
    ${files}=    Create table    ${files}
    Filter table by column    ${files}    size    >=    ${1024}
    FOR    ${file}    IN    @{files}
        Log    ${file}[name]
    END
    Write table to CSV    ${files}    ${OUTPUT_DIR}${/}files.csv

Excel to Table
    ${workbook}=    Open workbook    ${ORDERS_FILE}
    ${worksheet}=    Read worksheet    header=${TRUE}
    ${table}=    Create table    ${worksheet}
    ${groups}=    Group table by column    ${table}    Date
    FOR    ${rows}    IN    @{groups}
        List group IDs    ${rows}
    END

Table With Non-identifier Columns
    ${data}=    Create dictionary    123=asd    _\\1=33    cool key=value
    ${table}=    Create table    ${data}
    FOR    ${row}    IN    @{table}
        Log    ${row}[123]
        Log    ${row}[_\\1]
        Log    ${row}[cool key]
    END

Get Table Cell Errors
    ${table}=    Create table
    ...   [[1,2,3], [4,5,6]]
    ...   columns=["One","Two","Three"]

    Assert cell value    ${table}    0     0        ${1}
    Assert cell value    ${table}    1     1        ${5}
    Assert cell value    ${table}    1     Three    ${6}

    Assert cell error    ${table}    5     0       *out of range*
    Assert cell error    ${table}    1     3       *out of range*
    Assert cell error    ${table}    1     Four    *Unknown column name*
    Assert cell error    ${table}    Test  0       *not a number*

Convert Column Values
    ${table}=    Create table
    ...   [[1,"one","45"],[2,"two","102"],[3,"three",100]]
    ...   columns=["ID","User","Price"]

    Map Column Values    ${table}    Price    Convert to integer
    Map Column Values    ${table}    User     Find user name

    Assert cell value    ${table}    0     Price    ${45}
    Assert cell value    ${table}    2     Price    ${100}
    Assert cell value    ${table}    0     User     Teppo
    Assert cell value    ${table}    2     User     Cosmin

Remove Rows With Filtering
    ${table}=    Create table
    ...    [["One", "5/3/22 9:44"], ["Two", "5/4/22 9:25"], ["Three", "5/3/22 10:21"]]
    ...    columns=["ID", "Submit Date"]

    Filter Table With Keyword    ${table}
    ...     Match Date    target=05.03.2022  # kwarg passed as string arg
    Assert cell value    ${table}    0    ID    One
    Assert cell value    ${table}    1    ID    Three

*** Keywords ***
List group IDs
    [Arguments]    ${rows}
    FOR    ${row}    IN    @{rows}
        Log    ${row}[Id]
    END

Assert cell value
    [Arguments]    ${table}    ${row}    ${column}    ${value}
    ${result}=    Get table cell    ${table}    ${row}    ${column}
    Should be equal    ${result}    ${value}

Assert cell error
    [Arguments]    ${table}    ${row}    ${column}    ${error}
    Run keyword and expect error    ${error}
    ...    Get table cell    ${table}    ${row}    ${column}

Find user name
    [Arguments]    ${key}
    ${mapping}=    Create dictionary
    ...    one=Teppo
    ...    two=Mika
    ...    three=Cosmin
    ${output}=     Get from dictionary    ${mapping}    ${key}
    [Return]     ${output}

Match Date
    [Arguments]    ${row}    ${target}
    ${submit_date}=    Convert date
    ...    ${row}[Submit Date]
    ...    date_format=%d/%m/%y %H:%M
    ...    result_format=%d.%m.%Y
    ${target_date}=    Convert date
    ...    ${target}
    ...    date_format=%d.%m.%Y
    ...    result_format=%d.%m.%Y
    ${is_same_date}=    Evaluate    $submit_date == $target_date
    [Return]    ${is_same_date}
