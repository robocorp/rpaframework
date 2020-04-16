*** Settings ***
Library       RPA.Email.ImapSmtp
Library       RPA.Robocloud.Secrets
Library       RPA.Tables
Force tags    skip
Task Setup    Init GMail

*** Tasks ***
Sending Email
    [Documentation]     Sending email with GMail account
    Send Message
    ...                 sender=Robocorporation <robocorp.tester@gmail.com>
    ...                 recipients=mika@robocorp.com
    ...                 subject=Order confirmationäöäöä
    ...                 body=Thank you for the order!

Filtering emails
    [Documentation]     Filter emails by some criteria
    ${messages}=        List messages   SUBJECT "rpa"
    ${msgs}=            Create table    ${messages}
    Filter table by column    ${msgs}    From  contains  mika@robocorp.com
    FOR    ${msg}    IN    @{msgs}
        Log    ${msg.Subject}
        Log    ${msg.From}
    END

Getting emails
    [Documentation]     Gettings emails
    List messages       criterion=SUBJECT "rpa"

Saving attachments
    [Documentation]     Saving email attachments
    Save attachments    criterion=SUBJECT "rpa"  target_folder=../temp

*** Keywords ***
Init GMail
    ${email}=           Get secret     gmail
    Authorize SMTP      robocorp.tester@gmail.com   ${email}[password]  smtp.gmail.com
    Authorize IMAP      robocorp.tester@gmail.com   ${email}[password]  smtp.gmail.com
