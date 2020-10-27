*** Settings ***
Library           RPA.Dialogs    server_port=9201    stylesheet=${RESOURCE_DIR}dialogs.css
Force Tags        dialog    skip

*** Variables ***
${RESOURCE_DIR}    ${CURDIR}${/}..${/}resources${/}
${FORM_JSON}      ${RESOURCE_DIR}questionform.json

*** Keywords ***
Request By Form Constructed With Keywords
    ${options}    Create List    red    blue    green
    Create Form    My custom form
    Add Text Input    What is your name    name
    Add Dropdown    Select your color    color    ${options}    green
    Add Dropdown    Select your job    job    engineer,manager,technician
    Add Submit    myselection    yes,no
    &{response}    Request Response
    Log Many    ${response}

Request By Form Defined With JSON
    &{response}    Request Response    ${FORM_JSON}
    Log Many    ${response}

*** Tasks ***
Dialog built with keywords
    Request By Form Constructed With Keywords

Dialog built with JSON
    Request By Form Defined With JSON

Dialog including fileinput
    Create Form    My custom form
    Add Text Input    What is your name    name
    Add File Input    Upload a file    fileupload    fileupload    image/png
    &{response}    Request Response
    Log Many    ${response}
