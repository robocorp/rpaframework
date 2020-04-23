########
Netsuite
########

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Netsuite` is library for accessing Netsuite using NetSuite SOAP web service SuiteTalk.
Library extends `netsuitesdk library`_.

More information available at `NetSuite SOAP webservice SuiteTalk`_.


.. _netsuitesdk library:
    https://github.com/fylein/netsuite-sdk-py

.. _NetSuite SOAP webservice SuiteTalk:
    http://www.netsuite.com/portal/platform/developer/suitetalk.shtml

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
    Library     RPA.Netsuite
    Library     RPA.Excel.Files
    Library     RPA.Tables
    Task Setup  Authorize Netsuite

    *** Tasks ***
    Get data from Netsuite and Store into Excel files
        ${accounts}=        Get Accounts   account_type=_expense
        ${accounts}=        Create table    ${accounts}
        Create Workbook
        Append Rows To Worksheet  ${accounts}
        Save Workbook       netsuite_accounts.xlsx
        Close Workbook
        ${bills}=           Get Vendor Bills
        ${bills}=           Create table    ${bills}
        Create Workbook
        Append Rows To Worksheet  ${bills}
        Save Workbook       netsuite_accounts.xlsx
        Close Workbook


    *** Keywords ***
    Authorize Netsuite
        ${secrets}=     Get Secret   netsuite
        Connect
        ...        account=${secrets}[ACCOUNT]
        ...        consumer_key=${secrets}[CONSUMER_KEY]
        ...        consumer_secret=${secrets}[CONSUMER_KEY]
        ...        token_key=${secrets}[CONSUMER_SECRET]
        ...        token_secret=${secrets}[TOKEN_KEY]

Python
======

This is a section which describes how to use the library in your
own Python modules.

.. code-block:: python
    :linenos:

    from RPA.Netsuite import Netsuite

    ns = Netsuite()
    ns.connect()
    accounts = ns.get_accounts()
    currencies = ns.get_currencies()


*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Netsuite.rst
   python
