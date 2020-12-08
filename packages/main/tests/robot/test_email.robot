*** Settings ***
Library       RPA.Email.ImapSmtp
Library       RPA.HTTP
Library       RPA.Robocloud.Secrets
Library       RPA.Tables
Force tags    skip
Task Setup    Init GMail

*** Variables ***
${BODY_IMG1}      ${CURDIR}${/}..${/}resources${/}approved.png
${BODY_IMG2}      ${CURDIR}${/}..${/}resources${/}invoice.png
${EMAIL_BODY}     <h1>Heading</h1><p>Status: <img src='approved.png' alt='approved image'/></p>
...               <p>INVOICE: <img src='invoice.png' alt='invoice image'/></p>
${IMAGE_URL}     https://static1.squarespace.com/static/5c37bbd23e2d090f4652b5b9/t/5e6b5afca55453445ebc451b/1586254429285/?format=1500w

*** Tasks ***
Sending HTML Email With Downloaded Image
    [Documentation]     Sending email with HTML content and attachment
    Download            ${IMAGE_URL}  target_file=logo.png  overwrite=${TRUE}
    Send Message
    ...                 sender=Robocorporation <robocorp.tester@gmail.com>
    ...                 recipients=mika@robocorp.com
    ...                 subject=HTML email with body images (2) plus one attachment
    ...                 body=${EMAIL_BODY}
    ...                 html=${TRUE}
    ...                 images=${BODY_IMG1}, ${BODY_IMG2}
    ...                 attachments=logo.png

Sending HTML Email With Image
    [Documentation]     Sending email with HTML content and attachment
    Send Message
    ...                 sender=Robocorporation <robocorp.tester@gmail.com>
    ...                 recipients=mika@robocorp.com
    ...                 subject=HTML email with body images (2) plus one attachment
    ...                 body=${EMAIL_BODY}
    ...                 html=${TRUE}
    ...                 images=${BODY_IMG1}, ${BODY_IMG2}
    ...                 attachments=/Users/mika/koodi/syntax_example.png

Sending email with inline images
    [Documentation]     Sending email with inline images
    Send Message
    ...                 sender=Robocorporation <robocorp.tester@gmail.com>
    ...                 recipients=mika@robocorp.com
    ...                 subject=11 Email with inline images and attachment
    ...                 body=Normal body content
    ...                 images=${BODY_IMG1}, ${BODY_IMG2}
    ...                 attachments=/Users/mika/koodi/syntax_example.png

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
        Log    ${msg}[Subject]
        Log    ${msg}[From]
    END

Getting emails
    List messages       criterion=SUBJECT "rpa"

Saving attachments
    Save attachments    criterion=SUBJECT "rpa"  target_folder=../temp

Move messages empty criterion
    Run Keyword And Expect Error    KeyError*    Move Messages    ${EMPTY}

Move messages empty target
    Run Keyword And Expect Error    KeyError*    Move Messages    SUBJECT 'RPA'

Move messages to target folder from inbox
    ${result}=    Move Messages
    ...    criterion=SUBJECT "order confirmation"
    ...    target_folder=yyy

Move messages from subfolder to another
    ${result}=    Move Messages
    ...    criterion=ALL
    ...    source_folder=yyy
    ...    target_folder=XXX

Performing message actions
    ${actions}=    Create List    msg_unflag    msg_read    msg_save    msg_attachment_save
    Do Message Actions    SUBJECT "Order confirmation"
    ...    ${actions}
    ...    source_folder=XXX
    ...    target_folder=${CURDIR}
    ...    overwrite=True

*** Keywords ***
Init GMail
    ${email}=           Get secret     gmail
    Authorize SMTP      ${email}[account]   ${email}[password]  ${email}[smtpserver]
    Authorize IMAP      ${email}[account]   ${email}[password]  ${email}[imapserver]
