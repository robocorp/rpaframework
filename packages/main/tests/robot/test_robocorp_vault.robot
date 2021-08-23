*** Settings ***
Suite setup     Set mock data
Library         OperatingSystem
Default Tags    RPA.Robocorp.Vault

*** Variables ***
${RESOURCES}      ${CURDIR}/../resources

*** Tasks ***
Swaglabs process
    ${mysecret}=                Get secret   swaglabs
    Should Be Equal As Strings  "${mysecret}[username]"   "standard_user"
    Should Be Equal As Strings  "${mysecret}[password]"   "secret_sauce"

Get non existing secret
    Run Keyword And Expect Error   KeyError: 'Undefined secret: notexist'  Get secret  notexist

*** Keywords ***
Set mock data
    Set environment variable    RPA_SECRET_MANAGER    RPA.Robocorp.Vault.FileSecrets
    Set environment variable    RPA_SECRET_FILE       \${RESOURCES}/secrets.json
    Import library   RPA.Robocorp.Vault
