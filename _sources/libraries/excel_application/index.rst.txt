#################
Excel.Application
#################

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Excel.Application` is a library for manipulating Excel application.

********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library             RPA.Excel.Application
    Task Setup          Open Application
    Task Teardown       Quit Application

    *** Tasks ***
    Manipulate Excel application
        Open Workbook           workbook.xlsx
        Set Active Worksheet    sheetname=new stuff
        Write To Cells          row=1
        ...                     column=1
        ...                     value=my data
        Save Excel

    Run Excel Macro
        Open Workbook   orders_with_macro.xlsm
        Run Macro       Sheet1.CommandButton1_Click

Python
======

.. code-block:: python
    :linenos:

    from RPA.Excel.Application import Application

    def modify_excel():
        app = Application()
        app.open_application()
        app.open_workbook('workbook.xlsx')
        app.set_active_worksheet(sheetname='new stuff')
        app.write_to_cells(row=1, column=1, value='new data')
        app.save_excel()
        app.quit_application()

    if __name__ == "__main__":
        modify_excel()

*****************
API Documentation
*****************

See :download:`libdoc documentation <../../libdoc/RPA_Excel_Application.html>`.

.. toctree::
   :maxdepth: 1

   ../../robot/Excel/Application.rst
   python
