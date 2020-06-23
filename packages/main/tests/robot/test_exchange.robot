*** Settings ***
Library       RPA.Email.Exchange
Library       RPA.Robocloud.Secrets
Library       RPA.Tables
Force tags    skip

*** Variables ***
@{recipients}       robocorp.tester@gmail.com

*** Tasks ***
Sending Email
    [Documentation]     Sending email with Exchange
    [Setup]             Init Exchange
    Send Message
    ...                 recipients=${recipients}
    ...                 subject=Order confirmation
    ...                 body=Thank you for the order!


*** Keywords ***
Init Exchange
    ${email}=                   Get secret     exchange
    Connect With Credentials    AdeleV@beissi.onmicrosoft.com   ${email}[password]
