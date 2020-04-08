*** Settings ***
Library         RPA.Database
Library         OperatingSystem
Force Tags      database

*** Variables ***
${NOT_AUTHENTICATED_ERROR}  SalesforceAuthenticationError: *
${AUTHENTICATION_FAILED}    SalesforceAuthenticationFailed: *
${SQLITE_FILE}              ${CURDIR}${/}..${/}resources${/}orders.db

*** Tasks ***
Connecting to sqlite3 database with params
    File Should Exist   ${SQLITE_FILE}
    Connect to sqlite3 database

Get data from sqlite3 database
    [Setup]  Connect to sqlite3 database
    @{results}=   Database Query Result As Table
    ...         Select * From incoming_orders
    Length Should Be  ${results}   2


*** Keywords ***
Connect to sqlite3 database
    Connect To Database Using Custom Params
    ...     sqlite3
    ...     database="${SQLITE_FILE}"