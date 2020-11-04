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
which can be iterated over later in a Robot Framework keyword or task:

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

Processing all worksheets in the Excel file and checking row count:

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Excel.Files

    *** Variables ***
    ${EXCEL_FILE}   /path/to/excel.xlsx

    *** Tasks ***
    Rows in the sheet
        [Setup]      Open Workbook    ${EXCEL_FILE}
        @{sheets}=   List Worksheets
        FOR  ${sheet}  IN   @{sheets}
            ${count}=  Get row count in the sheet   ${sheet}
            Log   Worksheet '${sheet}' has ${count} rows
        END

    *** Keywords ***
    Get row count in the sheet
        [Arguments]      ${SHEET_NAME}
        ${sheet}=        Read Worksheet   ${SHEET_NAME}
        ${rows}=         Get Length  ${sheet}
        [Return]         ${rows}

Creating a new Excel file with a dictionary:

.. code-block:: robotframework
    :linenos:

    *** Tasks ***
    Creating new Excel
        Create Workbook  my_new_excel.xlsx
        FOR    ${index}    IN RANGE    20
            &{row}=       Create Dictionary
            ...           Row No   ${index}
            ...           Amount   ${index * 25}
            Append Rows to Worksheet  ${row}  header=${TRUE}
        END
        Save Workbook

Creating a new Excel file with a list:

.. code-block:: robotframework
    :linenos:

    *** Variables ***
    @{heading}   Row No   Amount
    @{rows}      @{heading}

    *** Tasks ***
    Creating new Excel
        Create Workbook  my_new_excel.xlsx
        FOR    ${index}    IN RANGE   1  20
            @{row}=         Create List   ${index}   ${index * 25}
            Append To List  ${rows}  ${row}
        END
        Append Rows to Worksheet  ${rows}
        Save Workbook

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

See :download:`libdoc documentation <../../libdoc/RPA_Excel_Files.html>`.

.. toctree::
   :maxdepth: 1

   ../../robot/Excel/Files.rst
   python
