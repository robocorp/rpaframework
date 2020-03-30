*** Settings ***
Suite Teardown    Verify result
Library           RPA.Tasks

*** Variables ***
${CURRENT}      ${1}
${TARGET}       ${5}

*** Tasks ***
Check loop condition
    Log    I'm trying to count to ${TARGET}
    Set next task if    ${CURRENT} >= ${TARGET}
    ...    Target reached
    ...    Increment current number

This will not run
    Fail    This should never run

Increment current number
    Set suite variable    ${CURRENT}    ${CURRENT + 1}
    Log    Number is now ${CURRENT}
    Jump to task    Check loop condition

Target reached
    Log    Those are some good numbers!

*** Keywords ***
Verify result
    Should be equal as integers    ${CURRENT}    ${5}
