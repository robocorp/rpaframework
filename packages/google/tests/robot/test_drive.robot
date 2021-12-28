*** Settings ***
Library           RPA.Cloud.Google
Library           Collections
Force Tags        skip    drive
Suite Setup       Setup files and folders
Suite Teardown    Teardown files and folders

*** Variables ***
${FOLDER_NAME}    google-library-test-directory
${RESOURCE_FOLDER}    ${CURDIR}${/}..${/}resources
@{FILES_TO_ADD}
...               okta.png
...               out.wav
...               pywinauto.pdf
...               landscape_image.png
@{TEST_FILES_IN_DRIVE}    @{EMPTY}

*** Keywords ***
Setup files and folders
    Init Drive    %{ROBOT_ROOT}${/}serviceaccount2.json
    ${folder}=    Create Drive Directory    ${FOLDER_NAME}
    ${folder2}=    Create Drive Directory    subfolder    ${FOLDER_NAME}
    Set Global Variable    ${MAIN_TEST_FOLDER_ID}    ${folder}[id]
    Set Global Variable    ${MAIN_TEST_FOLDER_URL}    ${folder}[url]
    Log To Console    Created test directory: ${folder}
    FOR    ${f}    IN    @{FILES_TO_ADD}
        ${file_id}=    Upload Drive File    ${RESOURCE_FOLDER}${/}${f}    ${FOLDER_NAME}
        Append To List    ${TEST_FILES_IN_DRIVE}    ${file_id}
    END
    ${file_id}=    Upload Drive File    ${RESOURCE_FOLDER}${/}source.png    subfolder
    Append To List    ${TEST_FILES_IN_DRIVE}    ${file_id}
    Log To Console    List test files after upload
    ${test_files}=    Search Drive Files    source=${FOLDER_NAME}
    FOR    ${f}    IN    @{test_files}
        IF    ${f}[is_folder]
            Log To Console    FOLDER: ${f}[name] ${f}[id]
        ELSE
            Log To Console    FILE: ${f}[name] ${f}[id]
        END
    END
    ${test_files}=    Search Drive Files    source=subfolder
    FOR    ${f}    IN    @{test_files}
        IF    ${f}[is_folder]
            Log To Console    FOLDER: ${f}[name] ${f}[id]
        ELSE
            Log To Console    FILE: ${f}[name] ${f}[id]
        END
    END
    Append To List    ${TEST_FILES_IN_DRIVE}    ${MAIN_TEST_FOLDER_ID}

Teardown files and folders
    #Remove All Drive Shares    file_id=${MAIN_TEST_FOLDER_ID}
    No Operation

*** Tasks ***
Share file with user email address
    [Tags]    share
    ${file}=    Search Drive Files    name = 'okta.png'
    ${shared}=    Add Drive Share
    ...    query=name = 'okta.png'
    ...    email=robocorp.tester@gmail.com
    Log To Console    ${file}
    Log To Console    ${shared}

Share writer access to file with user email address
    [Tags]    share
    Add Drive Share
    ...    query=name = 'okta.png'
    ...    email=robocorp.tester@gmail.com
    ...    role=writer

Share file with domain
    [Tags]    share
    Add Drive Share
    ...    query=name = 'okta.png'
    ...    domain=robocorp.com
    ...    role=writer

Share file with email notification
    [Tags]    share
    Add Drive Share
    ...    query=name = 'okta.png'
    ...    email=robocorp.tester@gmail.com
    ...    notification=True
    ...    notification_message=Hello. I am sharing with you this interesting Okta image.

Share folder with user email address
    [Tags]    share
    Add Drive Share
    ...    file_id=${MAIN_TEST_FOLDER_ID}
    ...    email=robocorp.tester@gmail.com

Remove shares from user with specific email address
    [Tags]    share
    Add Drive Share
    ...    query=name = 'okta.png'
    ...    email=robocorp.tester@gmail.com
    ...    role=writer
    Add Drive Share
    ...    query=name = 'okta.png'
    ...    domain=robocorp.com
    ${removed}=    Remove Drive Share By Criteria
    ...    query=name = 'okta.png'
    ...    email=robocorp.tester@gmail.com
    ...    domain=robocorp.com
    FOR    ${r}    IN    @{removed}
        Log To Console    ${r}
    END

Remove shares from user with specific domain
    [Tags]    share
    Add Drive Share
    ...    query=name = 'okta.png'
    ...    domain=robocorp.com
    ...    role=writer
    Add Drive Share
    ...    query=name = 'okta.png'
    ...    domain=robocorp.com
    ${removed}=    Remove Drive Share By Criteria
    ...    domain=robocorp.com
    ...    source=${FOLDER_NAME}
    FOR    ${r}    IN    @{removed}
        Log To Console    ${r}
    END

Add share to folder and remove permission
    [Tags]    share
    ${share}=    Add Drive Share
    ...    query=name = '${FOLDER_NAME}' and mimeType = 'application/vnd.google-apps.folder'
    ...    email=robocorp.tester@gmail.com
    #
    # actions on shared files ....
    #
    Remove Drive Share By Permission Id    ${share}[permission_id]    ${share}[file_id]

List Shared Files
    [Tags]    share
    Add Drive Share
    ...    query=name = 'source.png'
    ...    domain=robocorp.com
    ${shared}=    List Shared Drive Files    source=subfolder
    FOR    ${file}    IN    @{shared}
        Log To Console    ${file}
    END
