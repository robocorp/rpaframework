*** Settings ***
Library         Collections
Library         RPA.Outlook.Application   autoexit=${False}

Suite Setup         Open Application    visible=${True}     display_alerts=${True}
Suite Teardown      Quit Application

Default Tags      windows   skip  # no Outlook app in CI


*** Variables ***
${RESOURCES}    ${CURDIR}${/}..${/}resources


*** Tasks ***
Save email as draft
    Send Email    recipient@domain.com    Drafted message    Containing draft body
    ...    attachments=${RESOURCES}${/}vero2.pdf
    ...    save_as_draft=${True}

Send email with cc recipients
    ${cc} =    Create List    robocorp.developer@gmail.com    robocorp.tester@gmail.com
    Send Email
    ...    mika@robocorp.com;cosmin@robocorp.com;robocorp.tester@gmail.com
    ...    All recipient fields - message from rpaframwork tests - part 3
    ...    Contained body
    ...    attachments=${RESOURCES}${/}vero2.pdf;${RESOURCES}${/}invoice.png
    ...    cc_recipients=${cc}
    ...    bcc_recipients=robocorp.tester.2@gmail.com;mika@beissi.onmicrosoft.com

Retrieve emails
    @{emails} =     Get Emails      folder_name=Sent Items
    Log List    ${emails}
    ${length} =     Get Length    ${emails}
    Log To Console    Sent e-mails: ${length}
