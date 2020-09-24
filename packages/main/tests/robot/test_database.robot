*** Settings ***
Library          RPA.Database
Force Tags       database  database-sqlite3
Suite Setup      Initialize sqlite3 database
Suite Teardown   Disconnect From Database

*** Variables ***
${RESOURCE_DIR}   ${CURDIR}${/}..${/}resources${/}
${SQLITE_FILE}    ${RESOURCE_DIR}orders.db
${SQLITE_INIT}    ${RESOURCE_DIR}sqllite3_init.sql

*** Keywords ***
Initialize sqlite3 database
    Connect to Database  sqlite3  database=${SQLITE_FILE}
    Execute SQL Script   ${SQLITE_INIT}

*** Tasks ***
Select data from sqlite3 database
    @{results}=   Query  SELECT * FROM incoming_orders
    Length Should Be  ${results}   2

Get table description
    Run Keyword And Expect Error    Operation not supported for 'sqlite3' type database    Description  incoming_orders

Select data with assertion
    @{results}=   Query  SELECT * FROM incoming_orders  row_count == 2
    @{results}=   Query  SELECT * FROM incoming_orders  'asiakas' in columns
    @{results}=   Query  SELECT * FROM incoming_orders  columns == ['index', 'asiakas', 'amount']

Select data with failing assertion
    Run Keyword And Expect Error   Query assertion row_count == 0 failed*   Query  SELECT * FROM incoming_orders  row_count == 0

Insert and delete table data
    Query  INSERT INTO incoming_orders(asiakas,amount) VALUES ('tester51',66)
    Query  SELECT * FROM incoming_orders  row_count == 3
    Query  DELETE FROM incoming_orders WHERE asiakas = 'tester51'
    Query  SELECT * FROM incoming_orders  row_count == 2

Get Rows From Table
    @{rows}   Get Rows  incoming_orders
    Length Should Be  ${rows}   2
    @{rows}   Get Rows  incoming_orders  conditions=asiakas='nokia'
    Length Should Be  ${rows}   1
    @{rows}   Get Rows  incoming_orders  columns=amount  conditions=asiakas='microsoft'
    Should Be Equal As Integers    ${rows[0]}[amount]   3

Get Number of Rows From Table
    ${count}   Get Number Of Rows   incoming_orders
    Should Be Equal As Integers  ${count}   2
    ${count}   Get Number Of Rows   incoming_orders  asiakas='nokia'
    Should Be Equal As Integers  ${count}   1
    ${count}   Get Number Of Rows   incoming_orders  asiakas='amazon'
    Should Be Equal As Integers  ${count}   0
