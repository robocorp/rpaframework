*** Settings ***
Library           Collections
Library           OperatingSystem
Library           RPA.Email.ImapSmtp
Library           RPA.FileSystem
Library           RPA.HTTP
Library           RPA.Tables

Suite Setup       Init GMail

Default Tags      skip


*** Variables ***
${RESOURCES}      ${CURDIR}${/}..${/}resources
${RESULTS}        ${CURDIR}${/}..${/}results
${BODY_IMG1}      ${RESOURCES}${/}approved.png
${BODY_IMG2}      ${RESOURCES}${/}invoice.png
${EMAIL_BODY}     <h1>Heading</h1><p>Status: <img src='approved.png' alt='approved image'/></p>
...               <p>INVOICE: <img src='invoice.png' alt='invoice image'/></p>
${IMAGE_URL}      https://static1.squarespace.com/static/5c37bbd23e2d090f4652b5b9/t/5e6b5afca55453445ebc451b/1586254429285/?format=1500w
${MAIL_FILE}      ${RESOURCES}${/}emails${/}work-item-documentation.eml


*** Keywords ***
Init GMail
    Set Environment Variable    RPA_SECRET_MANAGER    RPA.Robocorp.Vault.FileSecrets
    Set Environment Variable    RPA_SECRET_FILE       ${RESOURCES}${/}secrets.yaml
    Import library      RPA.Robocorp.Vault

    ${email} =    Get Secret    gmail
    ${status}   ${ret} =     Run Keyword And Ignore Error    Authorize
    ...     ${email}[account]    ${email}[password]     is_oauth=${email}[is_oauth]
    ...     smtp_server=smtp.gmail.com    imap_server=imap.gmail.com
    IF    "${status}" == "FAIL"
        Pass Execution      ${ret}
    END


*** Tasks ***
Sending HTML Email With Downloaded Image
    [Documentation]    Sending email with HTML content and attachment

    Download    ${IMAGE_URL}    target_file=logo.png    overwrite=${TRUE}
    Send Message
    ...    sender=Robocorporation <robocorp.tester@gmail.com>
    ...    recipients=mika@robocorp.com
    ...    subject=HTML email with body images (2) plus one attachment
    ...    body=${EMAIL_BODY}
    ...    html=${TRUE}
    ...    images=${BODY_IMG1}, ${BODY_IMG2}
    ...    attachments=logo.png


Sending HTML Email With Image
    [Documentation]    Sending email with HTML content and attachment

    Send Message
    ...    sender=Robocorporation <robocorp.tester@gmail.com>
    ...    recipients=mika@robocorp.com
    ...    subject=HTML email with body images (2) plus one attachment
    ...    body=${EMAIL_BODY}
    ...    html=${TRUE}
    ...    images=${BODY_IMG1}, ${BODY_IMG2}
    ...    attachments=/Users/mika/koodi/syntax_example.png


Sending email with inline images
    [Documentation]    Sending email with inline images

    Send Message
    ...    sender=Robocorporation <robocorp.tester@gmail.com>
    ...    recipients=mika@robocorp.com
    ...    subject=11 Email with inline images and attachment
    ...    body=Normal body content
    ...    images=${BODY_IMG1}, ${BODY_IMG2}
    ...    attachments=/Users/mika/koodi/syntax_example.png


Sending Email
    [Documentation]    Sending email with GMail account

    Send Message
    ...    sender=Robocorporation <robocorp.tester@gmail.com>
    ...    recipients=mika@robocorp.com
    ...    subject=Order confirmationäöäöä
    ...    body=Thank you for the order!


Filtering emails
    [Documentation]    Filter emails by some criteria

    ${messages}=    List messages    SUBJECT "rpa"
    ${msgs}=    Create table    ${messages}
    Filter table by column    ${msgs}    From    contains    mika@robocorp.com
    FOR    ${msg}    IN    @{msgs}
        Log    ${msg}[Subject]
        Log    ${msg}[From]
    END


Getting emails
    List messages    criterion=SUBJECT "rpa"


Saving attachments
    Save attachments    criterion=SUBJECT "rpa"    target_folder=../temp


Move messages empty criterion
    Run Keyword And Expect Error    KeyError*    Move Messages    ${EMPTY}


Move messages empty target
    Run Keyword And Expect Error    KeyError*    Move Messages    SUBJECT 'RPA'


Move messages to target folder from inbox
    ${result} =    Move Messages
    ...    criterion=SUBJECT "order confirmation"
    ...    target_folder=yyy


Move messages from subfolder to another
    ${result} =    Move Messages
    ...    criterion=ALL
    ...    source_folder=yyy
    ...    target_folder=XXX


Performing message actions
    ${actions} =    Create List    msg_unflag    msg_read    msg_save    msg_attachment_save
    Do Message Actions    SUBJECT "Order confirmation"
    ...    ${actions}
    ...    source_folder=XXX
    ...    target_folder=${CURDIR}
    ...    overwrite=True


Move messages by their IDS
    [Documentation]    Use case could be one task parsing emails and then passing
    ...    the Message-IDS to another task to process further

    # task 1
    ${messages} =    List Messages    SUBJECT "incoming orders"
    @{idlist} =    Create List
    FOR    ${msg}    IN    @{messages}
        Append To List    ${idlist}    ${msg}[Message-ID]
    END
    # task 2
    Move Messages By IDs    ${idlist}    target_folder


Convert email to docx
    ${mail_name} =      Get File Name   ${MAIL_FILE}
    ${output_doc} =     Set Variable    ${OUTPUT_DIR}${/}${mail_name}.docx
    Email To Document    ${MAIL_FILE}   ${output_doc}

    File Should Exist   ${output_doc}
    File Should Not Be Empty    ${output_doc}
    [Teardown]  RPA.FileSystem.Remove file     ${output_doc}


Send Self Email
    ${email} =    Get Secret    gmail
    ${auth_type} =  Set Variable    basic
    IF    ${email}[is_oauth]
        ${auth_type} =  Set Variable    OAuth2
    END

    Send Message    sender=${email}[account]    recipients=${email}[account]
    ...    subject=E-mail sent through the ${auth_type} flow
    ...    body=I hope you find this flow easy to understand and use.


Download Duplicate Attachment
    ${name} =   Set Variable    exchange-oauth2
    ${ext} =    Set Variable    pdf
    @{files} =  Find Files  ${RESULTS}${/}${name}*
    RPA.FileSystem.Remove Files    @{files}

    @{all_paths} =      Save Attachments    criterion=SUBJECT "Duplicate attachment"
    ...     target_folder=${RESULTS}
    @{paths} =      Save Attachments    criterion=SUBJECT "Duplicate attachment"
    ...     target_folder=${RESULTS}
    Append To List      ${all_paths}    @{paths}

    @{expected_paths} =     Create List
    ...     ${RESULTS}${/}${name}.${ext}    ${RESULTS}${/}${name}-2.${ext}
    Lists Should Be Equal   ${all_paths}    ${expected_paths}
    FOR     ${path}     IN      @{all_paths}
        File Should Exist   ${path}
    END
