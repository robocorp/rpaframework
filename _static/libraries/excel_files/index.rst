###########
Excel.Files
###########

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

The `Excel.Files` library can be used to read and write Excel
files without the need to start the actual Excel application.

It supports both legacy .xls files and modern .xlsx files.

********
Examples
********

Robot Framework
===============

A common use-case is to load an existing Excel file as a table,
which can be iterated over later in a Robot Framework keyword or task.

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Tables
    Library    RPA.Excel.Files

    *** Keywords ***
    Read orders as table
        Open workbook    ${ORDERS_FILE}
        ${worksheet}=    Read worksheet   header=${TRUE}
        ${orders}=       Create table     ${worksheet}
        [Return]         ${orders}
        [Teardown]       Close workbook

Python
======

The library can also be imported directly into Python.

.. code-block:: python
    :linenos:

    from RPA.Excel.Files import Files

    def read_excel_worksheet(path, worksheet):
        lib = Files()
        lib.open_workbook(path)
        try:
            return lib.read_worksheet(worksheet)
        finally:
            lib.close_workbook()

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Excel/Files.rst
   python
