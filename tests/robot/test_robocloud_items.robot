*** Settings ***
Suite setup    Set mock data
Library        OperatingSystem
Library        RPA.Robocloud.Items    load_env=${FALSE}    default_adapter=FileAdapter

*** Variables ***
${ITEMS_FILE}    ${CURDIR}${/}..${/}resources${/}items.json

*** Tasks ***
Use variables from Robocloud
    Set task variables from work item
    Log   Using variables from workspace ${workspace} for user ${user_id}
    Set work item variables    user=Dude    mail=address@company.com
    Save work item

*** Keywords ***
Set mock data
    Remove file    ${ITEMS_FILE}
    Set environment variable    RC_WORKSPACE_ID       1
    Set environment variable    RC_WORKITEM_ID        1
    Set environment variable    RPA_WORKITEMS_PATH    ${ITEMS_FILE}
    Load work item from environment
    Set work item variables   workspace=1    user_id=123
    Save work item
