*** Settings ***
Library         RPA.Outlook.Application

Default Tags    skip


*** Tasks ***
Save email as draft
    Open Application
    Send Email    recipient@domain.com    Drafted message    Containing draft body
    ...    attachments=${CURDIR}${/}test_outlook_application.robot
    ...    save_as_draft=True

Send email with cc recipients
    Open Application
    Sleep    15s
    ${cc}=    Create List    robocorp.developer@gmail.com    robocorp.tester@gmail.com
    Send Email
    ...    mika@robocorp.com;robocorp.tester@gmail.com
    ...    All recipient fields - message from rpaframwork tests - part 3
    ...    Contained body
    ...    attachments=${CURDIR}${/}test_outlook_application.robot;${CURDIR}${/}test_calendar.robot
    ...    cc_recipients=${cc}
    ...    bcc_recipients=robocorp.tester.2@gmail.com;mika@beissi.onmicrosoft.com
