*** Settings ***
Documentation     Test script for RPA.Cloud.Google
Library           RPA.Robocloud.Secrets
Library           Collections
Suite Setup       Init all Google Services
Force Tags        skip

*** Variables ***
${USE_ROBOCORP_VAULT}    %{GOOGLE_TEST_USE_VAULT=${FALSE}}
${PROJECT_ID}     %{GOOGLE_TEST_PROJECT_ID}
${SHEET_ID}       %{GOOGLE_TEST_SHEET}
${SERVICE_ACCOUNT_FILEPATH}    %{GOOGLE_TEST_SERVICE_ACCOUNT}
${SCRIPT_ID}      %{GOOGLE_TEST_SCRIPT_ID}
${STORAGE_BUCKET}    %{GOOGLE_TEST_STORAGE_BUCKET}
${VAULT_NAME}     %{GOOGLE_TEST_VAULT_NAME}
${VAULT_KEY}      %{GOOGLE_TEST_VAULT_KEY}
${AUTH_TYPE}      %{GOOGLE_TEST_AUTH_TYPE}
${RESOURCES}      %{GOOGLE_TEST_RESOURCE_DIR=${CURDIR}${/}..${/}resources}

*** Keywords ***
Init all Google services
    Import Library    RPA.Cloud.Google
    ...    vault_name=${VAULT_NAME}
    ...    vault_secret_key=${VAULT_KEY}
    ...    cloud_auth_type=${AUTH_TYPE}
    Init Apps Script
    Init Drive
    Init Gmail
    Init Natural Language
    Init Sheets
    Init Speech To Text
    Init Storage    ${SERVICE_ACCOUNT_FILEPATH}    use_robocorp_vault=${USE_ROBOCORP_VAULT}
    Init Text To Speech
    Init Translation    project_identifier=${PROJECT_ID}
    Init Video Intelligence
    Init Vision    ${SERVICE_ACCOUNT_FILE_PATH}    use_robocorp_vault=${USE_ROBOCORP_VAULT}

*** Tasks ***
Using Google Sheets
    [Setup]    Clear Sheet Values    ${SHEET_ID}    A2:F30
    ${values}    Evaluate    [[11, 12, 13], ['aa', 'bb', 'cc']]
    ${result}=    Insert Sheet Values    ${SHEET_ID}    A2:B2    ${values}    ROWS
    ${row}    Evaluate    [[22, 33 ,44]]
    Sleep    2s
    ${result}=    Update Sheet Values    ${SHEET_ID}    A3:C3    ${row}    ROWS
    Log Many    ${result}
    ${values}=    Get Sheet Values    ${SHEET_ID}    A1:C1
    Log Many    ${values}

Using Google Drive
    ${root_id}=    Get Drive Folder Id    acceptance testing
    ${id1}=    Create Drive Directory    testing3    acceptance testing
    ${id2}=    Get Drive Folder Id    testing2
    ${fileid}=    Upload Drive File    acceptance testing
    ${fileid}=    Upload Drive File    ${RESOURCES}${/}source.png    testing3
    Delete Drive File    query=name contains 'testing2' and '${root_id}' in parents
    ${files}=    Download Drive Files    query=name contains 'source.png'    source=testing3
    ${files}=    Search Drive Files    query=name contains 'Brochure'    source=acceptance testing
    ${path}=    Export Drive File    file_dict=${files}[0]    target_file=out.pdf
    ${moved}=    Move Drive File    query=name contains 'conda.yaml'    source=acceptance testing    target=testing3
    Update Drive File    query=name contains 'Brochure'    source=acceptance testing    action=star
    Update Drive File    query=name contains 'okta.png'    source=acceptance testing    action=star
    Update Drive File    query=name contains 'Getting started'    action=star

Using Natural Language
    ${text}=    Set Variable    This is pretty angry text which basically
    ...    amounts to almost nothing because this service requires longer text to analyze.
    ${textfile}=    Set Variable    ${RESOURCES}${/}text_extract_from_pywinauto.txt
    ${response}=    Analyze Sentiment    text_file=${textfile}
    Log Many    ${response}
    ${response}=    Classify Text    text_file=${textfile}
    Log Many    ${response}

Using Vision
    ${image1}=    Set Variable    ${RESOURCES}${/}vertical_banner.png
    ${image3}=    Set Variable    ${RESOURCES}${/}faces.jpeg
    ${files}=    List Storage Files    ${STORAGE_BUCKET}
    ${result}=    Face Detection    image_uri=gs://${STORAGE_BUCKET}/faces.jpeg
    ...    json_file=${CURDIR}${/}faces_result.json
    Log Many    ${result}
    Log Many    ${files}
    ${result}=    Detect Text    image_file=${image1}    json_file=${CURDIR}${/}result1.json
    ${result}=    Detect Labels    image_file=${image2}    json_file=${CURDIR}${/}result2.json
    ${result}=    Detect Document    image_file=${image1}    json_file=${CURDIR}${/}result3.json

Using translation
    ${text}=    Set Variable    This is pretty angry text which basically
    ...    amounts to almost nothing because this service requires longer text to analyze.
    ${result}    Translate    ${text}    target_language=fi

Using text to speech and speech to text
    ${text}    Recognize Text From Audio    ${RESOURCES}${/}out.wav    audio_channel_count=1
    Log Many    ${text}

Using video intelligence
    ${result}=    Upload Storage File    ${STORAGE_BUCKET}    ${RESOURCES}${/}movie.mp4    movie.mp4
    ${result}=    Annotate Video    video_file=${RESOURCES}${/}movie.mp4
    ${result}=    Annotate Video    video_uri=gs://${STORAGE_BUCKET}/movie.mp4
    ...    features=TEXT_DETECTION
    ...    output_uri=gs://${STORAGE_BUCKET}/movie_annons.json
    ...    json_file=${CURDIR}${/}videoannotations.json
    Log Many    ${result}

Using cloud storage
    ${files}    Create List    movie_annons.json
    Download Storage Files    ${STORAGE_BUCKET}    ${files}
    ${result}=    Delete Storage Files    ${STORAGE_BUCKET}    movie_annons.json,movie.mp4

Using Apps Script
    [Setup]    Clear Sheet Values    ${SHEET_ID}    Settings!A2:B20
    ${values}    Evaluate    [['Ylänkötie 21, Järvenpää, Finland', 'Mannerheimintie 10, Helsinki, Finland']]
    ${result}=    Insert Sheet Values    ${SHEET_ID}    Settings!A2:B2    ${values}    ROWS
    ${response}=    Run Script    ${SCRIPT_ID}    generateStepByStep
    Log Many    ${response}

Using Gmail
    Send Message    me
    ...    mika@robocorp.com
    ...    viesti
    ...    viestin body
    ...    ["${CURDIR}${/}synthesized.mp3"]
