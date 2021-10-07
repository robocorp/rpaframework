*** Settings ***
Test Setup     Load mock library
Library        OperatingSystem


*** Variables ***
${RESOURCES}    ${CURDIR}/../resources
${RESULTS}      ${CURDIR}/../results
${temp_in}      ${RESOURCES}/temp_items.json
${temp_out}     ${RESULTS}/output_dir/temp_items.json
${first_item}   None

${err_state_set}        Can't create any more output work items since the last input was released, get a new input work item first
${err_item_released}    Input work item already released


*** Keywords ***
Load mock library
    Copy file    ${RESOURCES}/items.json    ${temp_in}
    Set environment variable    RPA_INPUT_WORKITEM_PATH    ${temp_in}
    Set environment variable    RPA_OUTPUT_WORKITEM_PATH    ${temp_out}

    Import library    RPA.Robocorp.WorkItems    autoload=${FALSE}    default_adapter=FileAdapter
    IF  ${first_item}
        Set Current Work Item     ${first_item}
    ELSE
        ${item} =     Get Input Work Item  # because auto-load is disabled with this test
        Set Global Variable     ${first_item}   ${item}
    END

Log Payload
    ${payload} =     Get Work Item Payload
    Log To Console    ${payload}
    ${len} =     Get Length    ${payload}
    [Return]    ${len}


*** Tasks ***
Read input and write output
    Set task variables from work item
    Log   Using variables from workspace ${workspace} for user ${user_id}
    Set work item variables    user=Dude    mail=address@company.com
    Save work item

    Create output work item
    Set work item variables    user=Another    mail=another@company.com
    Save work item
    File should exist    ${temp_out}

    [Teardown]  Remove file     ${temp_out}

Explicit state set
    ${payload} =     Get Work Item Payload
    Log     ${payload}

    Create Output Work Item
    Set Work Item Variables    user=Another2    mail=another2@company.com
    Save work item

    Release Input Work Item     DONE
    Run Keyword And Expect Error    ${err_state_set}        Create Output Work Item
    Run Keyword And Expect Error    ${err_item_released}    Release Input Work Item     DONE

Consume queue
    @{results} =     For Each Input Work Item    Log Payload
    Log   Items keys length: @{results}
    Length should be    ${results}  2
