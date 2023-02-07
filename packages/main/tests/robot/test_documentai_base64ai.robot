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
    ${ref_image} =  Set Variable    ${AI_RESOURCES}${/}signature-license.jpg
    ${query_image} =  Set Variable    ${AI_RESOURCES}${/}signature-check.png
    ${sigs} =   Get Matching Signatures     ${ref_image}    ${query_image}
    &{matches} =   Filter Matching Signatures      ${sigs}
    Log Dictionary    ${matches}
