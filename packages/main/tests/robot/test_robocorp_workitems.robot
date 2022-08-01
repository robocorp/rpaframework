*** Settings ***
Library        RPA.Email.ImapSmtp
Library        RPA.FileSystem
Library        OperatingSystem      WITH NAME   OS

Task Setup     Load mock library


*** Variables ***
${RESOURCES}    ${CURDIR}/../resources/work-items
${RESULTS}      ${CURDIR}/../results
${temp_in}      ${RESOURCES}/temp_items.json
${temp_out}     ${RESULTS}/output_dir/temp_items.json
${first_item}   ${None}

${err_state_set}        Can't create any more output work items since the last input was released, get a new input work item first
${err_item_released}    Input work item already released
${err_fail_without_type}     Must specify failure type from: BUSINESS, APPLICATION


*** Keywords ***
Load mock library
    OS.Copy file    ${RESOURCES}/items.json    ${temp_in}
    Set environment variable    RPA_INPUT_WORKITEM_PATH    ${temp_in}
    Set environment variable    RPA_OUTPUT_WORKITEM_PATH    ${temp_out}
    Import library    RPA.Robocorp.WorkItems    autoload=${False}    default_adapter=FileAdapter

    IF  ${first_item}
        Set Current Work Item     ${first_item}
        ${work_items} =    Get Library Instance    RPA.Robocorp.WorkItems
        ${namespace} =      Create Dictionary   adapter=${work_items.adapter}
        Evaluate    setattr(adapter, "index", 1)   namespace=${namespace}
    ELSE
        ${item} =     Get Input Work Item  # because auto-load is disabled with this test
        Set Global Variable     ${first_item}   ${item}
    END


Log Payload
    ${payload} =     Get Work Item Payload
    Log    Payload: ${payload}
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

    [Teardown]  OS.Remove file     ${temp_out}


Explicit state set
    ${payload} =     Get Work Item Payload
    Log     ${payload}

    Create Output Work Item
    Set Work Item Variables    user=Another2    mail=another2@company.com
    Save work item

    Release Input Work Item     DONE
    Run Keyword And Expect Error    ${err_state_set}        Create Output Work Item
    Run Keyword And Expect Error    ${err_item_released}    Release Input Work Item     DONE


Create output work item with variables and files
    Get Input Work Item  # output gets created over a non-released input

    &{customer_vars} =    Create Dictionary    user=Another3    mail=another3@company.com
    ${test_file} =      Set Variable    ${RESULTS}${/}test.txt
    ${content} =    Set Variable    Test output work item
    RPA.FileSystem.Create File    ${test_file}   ${content}  overwrite=${True}
    Create Output Work Item     variables=${customer_vars}  files=${test_file}  save=${True}

    ${user_value} =     Get Work Item Variable      user
    Should Be Equal     ${user_value}      Another3

    ${path_out} =      Absolute Path   ${RESULTS}${/}test-out.txt
    ${path} =   Get Work Item File  test.txt    path=${path_out}
    Should Be Equal    ${path}      ${path_out}
    File should exist    ${path}
    ${obtained_content} =   Read File    ${path}
    Should Be Equal     ${obtained_content}      ${content}


Consume queue
    @{results} =     For Each Input Work Item    Log Payload    items_limit=1
    Log   Items keys length: @{results}
    Length should be    ${results}  1


Failed release with exception
    Get Input Work Item
    Run Keyword And Expect Error    ${err_fail_without_type}    Release Input Work Item     FAILED      code=LOGIN_PORTAL_DOWN
    Release Input Work Item     FAILED      exception_type=BUSINESS   code=LOGIN_PORTAL_DOWN     message=Unable to login into the portal – not proceeding


Consume queue with and without results
    # Since the first item might be released already or not.
    Run Keyword And Ignore Error    Release Input Work Item     DONE

    @{expected_results} =   Create List     ${4}    ${2}
    ${results} =     For Each Input Work Item    Log Payload    return_results=${True}      items_limit=${2}
    Should Be Equal     ${results}      ${expected_results}

    ${results} =     For Each Input Work Item    Log Payload    return_results=${False}
    Should Be Equal     ${results}      ${None}


Get payload given e-mail process triggering
    ${parsed_email} =    Get Work Item Variable    parsedEmail
    Set Work Item Variables    &{parsed_email}[Body]
    Save Work Item
    ${message} =     Get Work Item Variable     message
    Should Be Equal     ${message}      from email
    Should Be True    ${parsed_email}[Has-Attachments]
    ${raw_email} =    Get Work Item Variable    rawEmail
    ${message} =    Evaluate    email.message_from_string($raw_email)     modules=email
    Save Attachment     ${message}    ${RESULTS}    overwrite=${True}
    ${path} =   Set Variable    ${RESULTS}${/}test.txt
    File Should Exist   ${path}
    ${data} =   Read File    ${path}
    Should Be Equal     ${data}    My Cool Attachment   strip_spaces=${True}

    # The newly parsed e-mail trigger option enabled.
    Get Input Work Item
    ${parsed_email} =   Get Work Item Variable    parsedEmail
    Should Contain    ${parsed_email}[Body]    from email
    ${email_parsed} =   Get Work Item Variable    email
    Should Contain    ${email_parsed}[body]    from email
