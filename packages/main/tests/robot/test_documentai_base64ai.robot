*** Settings ***
Documentation   Integration tests for individual keywords of the `Base64AI` library.

Library     Collections
Library     OperatingSystem
Library     RPA.DocumentAI.Base64AI
Library     String

Library     RPA.JSON

Suite Setup     Auth With Local Vault
Default Tags    skip


*** Variables ***
${RESOURCES}        ${CURDIR}${/}..${/}resources
${AI_RESOURCES}     ${RESOURCES}${/}documentai


*** Keywords ***
Auth With Local Vault
    Set Environment Variable    RPA_SECRET_MANAGER    RPA.Robocorp.Vault.FileSecrets
    Set Environment Variable    RPA_SECRET_FILE       ${RESOURCES}${/}secrets.yaml

    Import Library      RPA.Robocorp.Vault

    ${secret} =     Get Secret    document_ai
    @{api_creds} =      Split String    ${secret}[base64ai]     ,
    Set Authorization    ${api_creds}[${0}]    ${api_creds}[${1}]


*** Tasks ***
Match Signatures With Driver License
    [Documentation]     Check a similar signature from a test document against a
    ...     trusted proof (like driving license).

    # We look for the reference signature(s) inside the queried one(s).
    ${ref_image} =  Set Variable    ${AI_RESOURCES}${/}signature-license.jpg
    ${query_image} =  Set Variable    ${AI_RESOURCES}${/}signature-check.png
    ${sigs} =   Get Matching Signatures     ${ref_image}    ${query_image}
    &{matches} =   Filter Matching Signatures      ${sigs}
    Log Dictionary    ${matches}

    # And we retrieve the first matching query signature with the reference one.
    @{ref_sigs} =   Get Dictionary Keys    ${matches}
    @{qry_sigs} =    Get From Dictionary    ${matches}    ${ref_sigs}[${0}]
    &{qry_sig} =    Set Variable    ${qry_sigs}[${0}]
    Should Be True    ${qry_sig}[similarity] >= 0.8

    # Even save and display the cropped image belonging to the queried signature.
    ${path} =   Get Signature Image     ${sigs}     index=${qry_sig}[index]
    Log To Console    Preview query signature image crop: ${path}
