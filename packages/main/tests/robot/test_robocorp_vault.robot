*** Settings ***
Library         OperatingSystem
Default Tags    RPA.Robocorp.Vault
Suite setup     Set mock data
Task Template   File secrets


*** Variables ***
${RESOURCES}      ${CURDIR}${/}..${/}resources


*** Keywords ***
Set mock data
    Set environment variable    RPA_SECRET_MANAGER    RPA.Robocorp.Vault.FileSecrets
    Import library   RPA.Robocorp.Vault


File secrets
    [Arguments]     ${secrets_file}
    Set environment variable    RPA_SECRET_FILE       ${secrets_file}

    ${mysecret}=                Get secret   swaglabs
    Should Be Equal As Strings  "${mysecret}[username]"   "standard_user"
    Should Be Equal As Strings  "${mysecret}[password]"   "secret_sauce"

    Run Keyword And Expect Error   KeyError: 'Undefined secret: notexist'  Get secret  notexist


*** Tasks ***                        SECRETS_FILE
JSON secrets file                    ${RESOURCES}${/}secrets.json
YAML secrets file                    ${RESOURCES}${/}secrets.yaml
