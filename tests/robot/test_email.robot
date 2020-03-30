*** Settings ***
Library       RPA.Email.ImapSmtp  smtp_server=smtp.gmail.com
Library       RPA.Robocloud.Secrets
Library       RPA.Tables
Force tags    skip

*** Tasks ***
Sending Email
    [Documentation]     Sending email with GMail account
    [Setup]             Init GMail
    Send Message
    ...                 sender=Robocorporation <robocorp.tester@gmail.com>
    ...                 recipients=mika.hanninen@gmail.com
    ...                 subject=Order confirmation
    ...                 body=Thank you for the order!
    ...                 html=${True}

Filtering emails
    [Documentation]     Filter emails by some criteria
    [Setup]             Init GMail
    ${messages}=        List messages   SUBJECT "rpa"
    ${msgs}=            Create table    ${messages}
    Filter table by column    ${msgs}    From  contains  mika@robocorp.com
    FOR    ${msg}    IN    @{msgs}
        Log    ${msg.Subject}
        Log    ${msg.From}
    END

Getting emails
    [Documentation]     Gettings emails
    [Setup]             Init GMail
    Get messages        criterion=SUBJECT "rpa"  target_folder=../temp

Saving attachments
    [Documentation]     Saving email attachments
    [Setup]             Init GMail
    Save attachments    criterion=SUBJECT "rpa"  target_folder=../temp

*** Keywords ***
Init GMail
    ${email}=           Get secret     gmail
    Authorize           robocorp.tester@gmail.com   ${email}[password]
