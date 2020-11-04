##############
Email.Exchange
##############

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Exchange` is a library for sending, reading, and deleting emails.
`Exchange` is interfacing with Exchange Web Services (EWS).

For more information about server settings, see
`this Microsoft support article <https://support.microsoft.com/en-us/office/server-settings-you-ll-need-from-your-email-provider-c82de912-adcc-4787-8283-45a1161f3cc3>`_.

********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library     RPA.Email.Exchange
    Task Setup  Authorize  username=${ACCOUNT}  password=${PASSWORD}

    *** Variables ***
    ${ACCOUNT}              ACCOUNT_NAME
    ${PASSWORD}             ACCOUNT_PASSWORD
    ${RECIPIENT_ADDRESS}    RECIPIENT
    ${IMAGES}               myimage.png
    ${ATTACHMENTS}          C:${/}files${/}mydocument.pdf

    *** Tasks ***
    Sending email
        Send Message  recipients=${RECIPIENT_ADDRESS}
        ...           subject=Exchange Message from RPA Robot
        ...           body=<p>Exchange RPA Robot message body<br><img src='myimage.png'/></p>
        ...           save=${TRUE}
        ...           html=${TRUE}
        ...           images=${IMAGES}
        ...           cc=EMAIL_ADDRESS
        ...           bcc=EMAIL_ADDRESS
        ...           attachments=${ATTACHMENTS}

Python
======

.. code-block:: python
    :linenos:

    from RPA.Email.Exchange import Exchange

    ex_account = "ACCOUNT_NAME"
    ex_password = "ACCOUNT_PASSWORD"

    mail = Exchange()
    mail.authorize(username=ex_account, password=ex_password)
    mail.send_message(
        recipients="RECIPIENT",
        subject="Message from RPA Python",
        body="RPA Python message body",
    )

*****************
API Documentation
*****************

See :download:`libdoc documentation <../../libdoc/RPA_Email_Exchange.html>`.

.. toctree::
   :maxdepth: 1

   ../../robot/Email/Exchange.rst
   python
