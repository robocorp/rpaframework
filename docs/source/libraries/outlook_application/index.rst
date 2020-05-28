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

This is a section which describes how to use the library in your
Robot Framework tasks.

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
        ...                subject=Message from RPA
        ...                body=Sending message body contains more details
        ..                 attachments=approved.png

Python
======

This is a section which describes how to use the library in your
own Python modules.

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
