*** Settings ***
Library           RPA.Outlook.Application
Task Setup        Open Application
Default Tags      skip

*** Tasks ***
Save email as draft
    Send Email    recipient@domain.com    Drafted message    Containing draft body
    ...    attachments=${CURDIR}${/}test_outlook_application.robot
    ...    save_as_draft=True

Send email with cc and bcc
    Send Email    mika@beissi.onmicrosoft.com    Drafted message    Containing draft body
    ...    attachments=${CURDIR}${/}test_outlook_application.robot
    ...    recipients_cc=robocorp.tester@gmail.com,mika@robocorp.com
    ...    recipients_bcc=mika.hanninen@gmail.com
    ...    send_on_behalf_of_address=AdeleV@beissi.onmicrosoft.com

Get Emails
    ${emails}=    Get Emails    email_filter=[Subject]='Your digest email'
    FOR    ${email}    IN    @{emails}
        Log To Console    ${email}
    END
