##############
Email.Exchange
##############

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Exchange` is a library for sending, reading, and
deleting emails. `Exchange` is interfacing with
Exchange Web Services (EWS).


********
Examples
********

Robot Framework
===============

This section describes how to use the library in your Robot Framework tasks.

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

This section describes how to use the library in your own Python modules.

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

.. toctree::
   :maxdepth: 1

   ../../libdoc/Email/Exchange.rst
   python
