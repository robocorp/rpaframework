*** Settings ***
Suite Teardown    Verify result
Library           RPA.Tasks    schema=${SCHEMA_FILE}

*** Variables ***
${SCHEMA_FILE}  ${CURDIR}${/}..${/}resources${/}tasks_schema.json
${CURRENT}      ${1}
${TARGET}       ${5}

*** Tasks ***
Check loop condition
    Log    I'm trying to count to ${TARGET}

This will not run
    Fail    This should never run

Increment current number
    Set suite variable    ${CURRENT}    ${CURRENT + 1}
    Log    Number is now ${CURRENT}

Target reached
    Fail   Not a critical error

The final task
    Log    Those are some good numbers!

*** Keywords ***
Verify result
    Should be equal as integers    ${CURRENT}    ${5}
