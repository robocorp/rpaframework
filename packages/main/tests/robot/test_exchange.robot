*** Settings ***
Library           DateTime
Library           OperatingSystem
Library           RPA.Email.Exchange
Library           RPA.FileSystem
Library           RPA.Tables

Force Tags        skip

Task Setup        Init Variables


*** Variables ***
${RESOURCES}      ${CURDIR}${/}..${/}resources
${RESULTS}        ${CURDIR}${/}..${/}results


*** Keywords ***
Init Exchange
    Set Environment Variable    RPA_SECRET_MANAGER    RPA.Robocorp.Vault.FileSecrets
    Set Environment Variable    RPA_SECRET_FILE       ${RESOURCES}${/}secrets.yaml
    Import library      RPA.Robocorp.Vault

    ${email} =      Get secret    exchange
    Authorize
    ...    username=${email}[account]
    ...    password=${email}[password]
    ...    autodiscover=${False}
    ...    server=outlook.office365.com


Init Variables
    ${timestamp}=    Get Current Date
    Set Global Variable    ${EMAIL_SUBJECT}    From rpaframework tests - ${timestamp}


*** Tasks ***
Sending Email Without Authorize
    Run Keyword And Expect Error    AuthenticationError: Not authorized to any Exchange account
    ...    Send Message
    ...    recipients=robocorp.tester@gmail.com
    ...    subject=${EMAIL_SUBJECT}
    ...    body=${TEST_NAME}


Sending Email For Single Recipient
    Init Exchange
    Send Message
    ...    recipients=robocorp.tester@gmail.com
    ...    subject=${EMAIL_SUBJECT}
    ...    body=${TEST_NAME}


Sending Email For Multiple Recipients as List
    Init Exchange
    @{recipients}=    Create List    robocorp.tester@gmail.com    robocorp.tester.2@gmail.com
    Send Message
    ...    recipients=${recipients}
    ...    subject=${EMAIL_SUBJECT}
    ...    body=${TEST_NAME}


Sending Email For Multiple CC as List
    Init Exchange
    @{recipients}=    Create List    robocorp.tester@gmail.com    robocorp.tester.2@gmail.com
    Send Message
    ...    cc=${recipients}
    ...    subject=${EMAIL_SUBJECT}
    ...    body=${TEST_NAME}


Sending Email For Multiple BCC as List
    Init Exchange
    @{recipients}=    Create List    robocorp.tester@gmail.com    robocorp.tester.2@gmail.com
    Send Message
    ...    bcc=${recipients}
    ...    subject=${EMAIL_SUBJECT}
    ...    body=${TEST_NAME}


Sending Email For Multiple Recipients as String
    Init Exchange
    Send Message
    ...    recipients=robocorp.tester@gmail.com,robocorp.tester.2@gmail.com
    ...    subject=${EMAIL_SUBJECT}
    ...    body=${TEST_NAME}


Sending Email With Multiple Attachments as List
    Init Exchange
    @{attachments}=    Create List
    ...    ${RESOURCES}${/}approved.png
    ...    ${RESOURCES}${/}faces.jpeg
    Send Message
    ...    recipients=robocorp.tester@gmail.com
    ...    subject=${EMAIL_SUBJECT}
    ...    body=${TEST_NAME}
    ...    attachments=${attachments}


Sending Email With Multiple Attachments as String
    Init Exchange
    Send Message
    ...    recipients=robocorp.tester@gmail.com
    ...    subject=${EMAIL_SUBJECT}
    ...    body=${TEST_NAME}
    ...    attachments=${RESOURCES}${/}approved.png,${RESOURCES}${/}faces.jpeg


Sending Email Without Addresses
    Init Exchange
    Run Keyword And Expect Error    NoRecipientsError: Atleast one address is required for 'recipients', 'cc' or 'bcc' parameter
    ...    Send Message
    ...    subject=${EMAIL_SUBJECT}
    ...    body=${TEST_NAME}


Download Duplicate Attachment
    # Initially save one e-mail with attachment to local disk. (can be used offline
    #  afterwards indefinitely)
#    Init Exchange

    ${name} =   Set Variable    exchange-oauth2
    ${ext} =    Set Variable    pdf
    @{files} =  Find Files  ${RESULTS}${/}${name}*
    RPA.FileSystem.Remove Files    @{files}

    ${eml_file} =   Set Variable    ${RESOURCES}${/}emails${/}exchange-mail.eml
#    @{msgs} =   List Messages   criterion=body:RPA   count=${1}
#    Save Message    ${msgs}[0]      ${eml_file}

    # Now save attachments from the given offline e-mail.
    Save Attachments    ${eml_file}     save_dir=${RESULTS}
    Save Attachments    ${eml_file}     save_dir=${RESULTS}

    # And check their duplicate behaviour.
    File Should Exist   ${RESULTS}${/}${name}.${ext}
    File Should Exist   ${RESULTS}${/}${name}-2.${ext}
