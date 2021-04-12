*** Settings ***
Library           RPA.HTTP

*** Variables ***
${RESOURCES}      ${CURDIR}${/}..${/}resources

*** Tasks ***
Download with verify false
    [Tags]    skip
    Download    https://api.github.com/users/mikahanninen
    ...    verify=${FALSE}
    ...    overwrite=${TRUE}
    ...    force_new_session=${TRUE}

Download with verify cert path
    [Tags]    skip
    Download    https://api.github.com/users/mikahanninen
    ...    verify=${RESOURCES}${/}cacert.pem
    ...    overwrite=${TRUE}
    ...    force_new_session=${TRUE}

Download with verify true
    [Tags]    skip
    Download    https://api.github.com/users/mikahanninen
    ...    verify=${TRUE}
    ...    overwrite=${TRUE}
    ...    force_new_session=${TRUE}

HTTP Get with verify false
    [Tags]    skip
    HTTP Get    https://api.github.com/users/mikahanninen
    ...    verify=${FALSE}
    ...    overwrite=${TRUE}
    ...    force_new_session=${TRUE}

HTTP Get with verify cert path
    [Tags]    skip
    HTTP Get    https://api.github.com/users/mikahanninen
    ...    verify=${RESOURCES}${/}cacert.pem
    ...    overwrite=${TRUE}
    ...    force_new_session=${TRUE}

HTTP Get with verify true
    [Tags]    skip
    HTTP Get    https://api.github.com/users/mikahanninen
    ...    verify=${TRUE}
    ...    overwrite=${TRUE}
    ...    force_new_session=${TRUE}
