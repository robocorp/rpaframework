*** Settings ***
Library     Collections
Library     OperatingSystem
Library     RPA.Robocorp.Storage

Suite Setup     Load Mocked Library
# Skip all tests by default since they rely on a real working API URL & token
#  simulating the cloud environment not provided yet in CI.
Default Tags    manual


*** Variables ***
${RESOURCES}        ${CURDIR}${/}..${/}resources
${RESULTS}        ${CURDIR}${/}..${/}results


*** Keywords ***
Use Local Vault
    Set Environment Variable    RPA_SECRET_MANAGER    RPA.Robocorp.Vault.FileSecrets
    Set Environment Variable    RPA_SECRET_FILE       ${RESOURCES}${/}secrets.yaml

    Import Library      RPA.Robocorp.Vault

Load Mocked Library
    Use Local Vault
    ${secret} =    Get Secret    asset_storage

    Set Environment Variable    RC_API_URL_V1   ${secret}[api_url]
    Set Environment Variable    RC_API_TOKEN_V1   ${secret}[api_token]
    Set Environment Variable    RC_WORKSPACE_ID     ${secret}[workspace_id]


Delete All Assets
    [Arguments]     ${assets}   ${pattern}

    FOR    ${asset}    IN    @{assets}
        ${matches} =    Evaluate    fnmatch.fnmatch('${asset}', '${pattern}')
        ...     modules=fnmatch
        IF    ${matches}
            Delete Asset    ${asset}
        END
    END


*** Tasks ***
Manage Assets
    # NOTE(cmin764; 18 Jul 2023): Placed all the atomic tests into a bigger integration
    #  one for the following reasons: reducing overall time given the assets listing
    #  check and giving time for the resources to settle in the cloud memory.

    # Set assets with a common prefix and various types.
    ${data} =      Evaluate    b"Cosmin" + b" Poieana"
    Set Bytes Asset     cosmin-data    ${data}
    Set Text Asset      cosmin-text      cosmin@robocorp.com
    &{entries} =    Create Dictionary   country    Romania
    Set JSON Asset    cosmin-dict    ${entries}
    Set File Asset    cosmin-file      ${RESOURCES}${/}faces.jpeg

    # Check if the assets are present in CR.
    @{expected_assets} =    Create List     cosmin-data     cosmin-text
    ...     cosmin-dict     cosmin-file
    @{assets} =    List Assets
    List Should Contain Sub List    ${assets}    ${expected_assets}

    # Now retrieve & check the value for every asset.
    ${value} =      Get Bytes Asset   cosmin-data
    Should Be Equal As Strings    ${value}    ${data}
    ${value} =      Get Text Asset   cosmin-text
    Should Be Equal As Strings    ${value}    cosmin@robocorp.com
    &{value} =      Get JSON Asset       cosmin-dict
    Should Be Equal As Strings    ${value}[country]    Romania
    ${path} =      Get File Asset       cosmin-file    ${RESULTS}${/}faces.jpeg
    ...     overwrite=${True}
    ${content} =   Get Binary File    ${path}
    ${image_mark} =     Convert To Bytes    JFIF
    Should Contain    ${content}    ${image_mark}

    [Teardown]      Delete All Assets   ${assets}   cosmin-*
