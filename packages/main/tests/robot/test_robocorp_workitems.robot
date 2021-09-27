*** Settings ***
Suite setup    Load mock library
Library        OperatingSystem

*** Variables ***
${RESOURCES}    ${CURDIR}/../resources
${RESULTS}      ${CURDIR}/../results
${temp_in}      ${RESOURCES}/temp_items.json
${temp_out}     ${RESULTS}/output_dir/temp_items.json

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
    File should exist    ${temp_out}

    [Teardown]  Remove file     ${temp_out}

*** Keywords ***
Load mock library
    Copy file    ${RESOURCES}/items.json    ${temp_in}
    Set environment variable    RPA_INPUT_WORKITEM_PATH    ${temp_in}
    Set environment variable    RPA_OUTPUT_WORKITEM_PATH    ${temp_out}
    Import library    RPA.Robocorp.WorkItems    autoload=${FALSE}    default_adapter=FileAdapter
