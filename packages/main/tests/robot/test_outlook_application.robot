*** Settings ***
Library           RPA.Outlook.Application
Default Tags      skip

*** Tasks ***
Save email as draft
    Open Application
    Send Email    recipient@domain.com    Drafted message    Containing draft body
    ...    attachments=${CURDIR}${/}test_outlook_application.robot
    ...    save_as_draft=True
