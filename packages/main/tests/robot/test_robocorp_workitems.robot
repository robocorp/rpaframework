*** Settings ***
Suite setup    Load mock library
Library        OperatingSystem

*** Variables ***
${RESOURCES}     ${CURDIR}/../resources

*** Tasks ***
Read input and write output
    Get input work item
    Set task variables from work item
    Log   Using variables from workspace ${workspace} for user ${user_id}
    Set work item variables    user=Dude    mail=address@company.com
    Save work item

    Create output work item
    Set work item variables    use=Another    mail=another@company.com
    Save work item
    File should exist    ${RESOURCES}/temp_items.output.json

*** Keywords ***
Load mock library
    Copy file    ${RESOURCES}/items.json    ${RESOURCES}/temp_items.json
    Set environment variable    RPA_WORKITEMS_PATH    \${RESOURCES}/temp_items.json
    Import library    RPA.Robocorp.WorkItems    autoload=${FALSE}    default_adapter=FileAdapter
