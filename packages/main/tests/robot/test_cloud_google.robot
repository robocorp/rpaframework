*** Settings ***
Documentation     Test script for RPA.Google.Cloud
Library           RPA.Cloud.Google
Library           RPA.HTTP
Suite Setup       Set up authentication using vault
Force Tags  skip

*** Variables ***
${SERVICE_ACCOUNT}    /path/to/service_account.json
${CREDENTIALS_JSON}   /path/to/credentials.json
@{SCRIPT_SCOPES}    forms    spreadsheets

*** Keywords ***
Set up authentication using vault
    Set Robocloud Vault  vault_name=googlecloud
    Init Apps Script Client    use_robocloud_vault=True
    Init Drive Client    use_robocloud_vault=True

*** Tasks ***
Upload File
    Drive Upload File   mylocalfile.txt  folder=target_folder
    Drive Upload File   mylocalfile.txt  folder=target_folder  overwrite=True

Delete files
    ${files}=    Drive Search Files    query=name contains 'rpaframework'    folder_name=releases
    FOR    ${f}    IN    @{files}
        Drive Delete File    file_dict=${f}
    END

Update files
    ${updated}=    Drive Update File    query=name contains '.yaml' and '${folder_id}' in parents
    ...    action=untrash
    ...    multiple_ok=True

Create Directory
    ${result}=    Drive Create Directory    rpaframework-builds2
    Run Keyword And Expect Error  Drive Create Directory  ${EMPTY}

Download files
    ${files}=    Drive Search Files    query=name contains '.yaml' and '${folder_id}' in parents    recurse=True
    FOR    ${f}    IN    @{files}
        Run Keyword If    ${f}[size] < 200    Drive Download Files  file_dict=${f}
    END
    Drive Download Files    query=mimeType contains 'image/'    limit=2

Move files
    ${target_id}=    Drive Create Directory    target_directory
    Drive Move File    query=name contains '.yaml' and '${folder_id}' in parents    folder=target_directory    multiple_ok=True

Searching files
    ${files}=    Drive Search Files    query=name contains 'hello'
    ${len}=    Get Length    ${files}
    ${files}=    Drive Search Files    query=modifiedTime > '2020-06-04T12:00:00'
    ${len}=    Get Length    ${files}
    ${files}=    Drive Search Files    query=mimeType contains 'image/' or mimeType contains 'video/'    recurse=True
    ${len}=    Get Length    ${files}
    ${files}=    Drive Search Files    query=name contains '.yaml'    recurse=True
    ${len}=    Get Length    ${files}
    ${files}=    Drive Search Files    query=name contains '.yaml'    folder_name=target_directory
    ${len}=    Get Length    ${files}
    Run Keyword And Expect Error   Drive Search Files  query=mimetype contains 'image/'