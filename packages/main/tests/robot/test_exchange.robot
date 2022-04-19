*** Settings ***
Library           RPA.Email.Exchange
Library           RPA.Robocorp.Vault
Library           RPA.Tables
Library           DateTime
Force Tags        skip
Task Setup        Init Variables

*** Variables ***
${RESOURCES}      ${CURDIR}${/}..${/}resources

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

*** Keywords ***
Init Exchange
    ${email}=    Get secret    Exchange
    Authorize
    ...    username=${email}[account]
    ...    password=${email}[password]
    ...    autodiscover=False
    ...    server=outlook.office365.com

Init Variables
    ${timestamp}=    Get Current Date
    Set Global Variable    ${EMAIL_SUBJECT}    From rpaframework tests - ${timestamp}
