###################
Outlook.Application
###################

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Outlook.Application` is a library for manipulating Outlook application.

********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library                 RPA.Outlook.Application
    Task Setup              Open Application
    Suite Teardown          Quit Application

    *** Variables ***
    ${RECIPIENT}            address@domain.com

    *** Tasks ***
    Send message
        Send Message       recipients=${RECIPIENT}
        ...                subject=This is the subject
        ...                body=This is the message body
        ..                 attachments=approved.png

Python
======

.. code-block:: python
    :linenos:

    from RPA.Outlook.Application import Application

    def send_message():
        app = Application()
        app.open_application()
        app.send_message(
            recipients='EMAILADDRESS_1, EMAILADDRESS_2',
            subject='email subject',
            body='email body message',
            attachments='../orders.csv'


*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Outlook/Application.rst
   python
