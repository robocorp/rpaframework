*** Settings ***
Library     Collections
Library     OperatingSystem
Library     RPA.Robocorp.Storage

Suite Setup     Load Mocked Library


*** Variables ***
${RESOURCES}        ${CURDIR}${/}..${/}resources


*** Keywords ***
Use Local Vault
    Set Environment Variable    RPA_SECRET_MANAGER    RPA.Robocorp.Vault.FileSecrets
    Set Environment Variable    RPA_SECRET_FILE       ${RESOURCES}${/}secrets.yaml

    Import Library      RPA.Robocorp.Vault

Load Mocked Library
    Use Local Vault
    ${secret} =    Get Secret    asset_storage

    Set Environment Variable    RC_API_URL_V1   ${secret}[api_url]
    Set Environment Variable    RC_WORKSPACE_ID     ${secret}[workspace_id]


*** Tasks ***
Manage Assets
    [Tags]    manual  # since it relies on a real working API key not provided in CI
    [Setup]     Set Asset   cosmin      cosmin@robocorp.com

    @{assets} =    List Assets
    @{asset_names} =    Evaluate    [asset['name'] for asset in ${assets}]
    List Should Contain Value    ${asset_names}    cosmin

    ${value} =      Get Asset   cosmin
    Should Be Equal As Strings    ${value}    cosmin@robocorp.com

    [Teardown]      Delete Asset    cosmin
