*** Settings ***
Suite setup     Set mock data
Library         OperatingSystem
Default Tags    RPA.Robocloud.Secrets

*** Variables ***
${SECRETS_FILE}                 ${CURDIR}${/}..${/}resources${/}secrets.json

*** Tasks ***
Swaglabs process
    ${mysecret}=                Get secret   swaglabs
    Should Be Equal As Strings  "${mysecret}[username]"   "standard_user"
    Should Be Equal As Strings  "${mysecret}[password]"   "secret_sauce"

Get non existing secret
    Run Keyword And Expect Error   KeyError: 'Undefined secret: robocorp'  Get secret  robocorp

*** Keywords ***
Set mock data
    Set environment variable    RPA_SECRET_MANAGER    RPA.Robocloud.Secrets.FileSecrets
    Set environment variable    RPA_SECRET_FILE       ${SECRETS_FILE}
    Import library   RPA.Robocloud.Secrets