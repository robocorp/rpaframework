*** Settings ***
Library     Collections
Library     OperatingSystem

Suite Setup     Local Vault

Default Tags    skip


*** Variables ***
${RESOURCES}        ${CURDIR}${/}..${/}resources
${INVOICE_PNG}      ${RESOURCES}${/}invoice.png
${INVOICE_URL}      https://raw.githubusercontent.com/robocorp/rpaframework/master/packages/main/tests/resources/invoice.png


*** Keywords ***
Local Vault
    Set Environment Variable    RPA_SECRET_MANAGER    RPA.Robocorp.Vault.FileSecrets
    Set Environment Variable    RPA_SECRET_FILE       ${RESOURCES}${/}secrets.yaml

    Import Library      RPA.DocumentAI


Init Engines
    Init Engine    base64ai    vault=document_ai:base64ai
    Init Engine    nanonets    vault=document_ai:nanonets


*** Tasks ***
Predict With Multiple Engines
    [Setup]   Init Engines

    Switch Engine    base64ai
    Predict    ${INVOICE_URL}
    @{data} =    Get Result    extended=${True}
    Log List    ${data}

    Switch Engine    nanonets
    Predict    ${INVOICE_PNG}   model=858e4b37-6679-4552-9481-d5497dfc0b4a
    @{data} =    Get Result
    Log List    ${data}
