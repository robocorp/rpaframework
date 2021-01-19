*** Settings ***
Documentation     Test cases for for Crypto library CLI
Suite setup       Create test data
Library           OperatingSystem
Library           Process

*** Variables ***
${PLAINTEXT_FILE}    ${OUTPUT_DIR}${/}plaintext.txt

*** Tasks ***
Generate key
    ${result}=    Command    key
    Should not be empty      ${result.stdout}

Hash string defaults
    ${result}=    Command    hash  ${PLAINTEXT_FILE}
    Should be equal    ${result.stdout}    eNOTzEOqI0k2ijVhEmKow1YPFGo=

Hash string change method
    ${result}=    Command    hash  --method=MD5  ${PLAINTEXT_FILE}
    Should be equal    ${result.stdout}    3ObaKiohbtSuG4Q8+kIKTg==

Encrypt string
    ${key}=    Command  key
    ${enc}=    Command  encrypt  -t  "${key.stdout}"  ${PLAINTEXT_FILE}  ${OUTPUT_DIR}${/}encrypted.bin
    ${dec}=    Command  decrypt  -t  "${key.stdout}"  ${OUTPUT_DIR}${/}encrypted.bin
    Should be equal    ${dec.stdout}    avalue

*** Keywords ***
Create test data
    Create file    ${PLAINTEXT_FILE}    avalue

Command
    [Arguments]   @{args}
    ${is_win}=    Evaluate         platform.system() == "Windows"    platform
    ${script}=    Set variable if  ${is_win}    rpa-crypto.cmd    rpa-crypto
    ${result}=    Run process      ${script}    --verbose    @{args}
    Should be equal as integers    ${result.rc}    0    message=${result.stderr}
    [Return]      ${result}
