##############
Email.ImapSmtp
##############

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`ImapSmtp` is a library for sending, reading and
deleting emails. `ImapSmtp` is interfacing with SMTP and IMAP
protocols.

***************
Troubleshooting
***************

- Authentication error with Gmail - "Application-specific password required"
    see. https://support.google.com/mail/answer/185833?hl=en

********
Examples
********

Robot Framework
===============

This is a section which describes how to use the library in your
Robot Framework tasks.

It is highly recommended to secure your passwords and take care
that they are not stored in the version control by mistake.
See :py:mod:`RPA.Robocloud.Secrets` how to store RPA Secrets into Robocloud.

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library     RPA.Email.ImapSmtp   smtp_server=smtp.gmail.com  port=587
    Task Setup  Authorize  account=${GMAIL_ACCOUNT}  password=${GMAIL_PASSWORD}

    *** Variables ***
    ${GMAIL_ACCOUNT}        ACCOUNT_NAME
    ${GMAIL_PASSWORD}       ACCOUNT_PASSWORD
    ${RECIPIENT_ADDRESS}    RECIPIENT

    *** Tasks ***
    Sending email
        Send Message  sender=${GMAIL_ACCOUNT}
        ...           recipients=${RECIPIENT_ADDRESS}
        ...           subject=Message from RPA Robot
        ...           body=RPA Robot message body

Python
======

This is a section which describes how to use the library in your
own Python modules.

.. code-block:: python
    :linenos:

    from RPA.Email.ImapSmtp import ImapSmtp

    gmail_account = "ACCOUNT_NAME"
    gmail_password = "ACCOUNT_PASSWORD"
    sender = gmail_account

    mail = ImapSmtp(smtp_server="smtp.gmail.com", port=587)
    mail.authorize(account=gmail_account, password=gmail_password)
    mail.send_message(
        sender=gmail_account,
        recipients="RECIPIENT",
        subject="Message from RPA Python",
        body="RPA Python message body",
    )

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Email/ImapSmtp.rst
   python
