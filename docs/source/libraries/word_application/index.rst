#################
Word.Application
#################

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Word.Application` is a library for manipulating Word application.

********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library                 RPA.Word.Application
    Task Setup              Open Application
    Suite Teardown          Quit Application

    *** Tasks ***
    Open existing file
        Open File           old.docx
        Write Text          Extra Line Text
        Write Text          Another Extra Line of Text
        Save Document AS    ${CURDIR}${/}new.docx
        ${texts}=           Get all Texts
        Close Document


Python
======

.. code-block:: python
    :linenos:

    from RPA.Word.Application import Application

    def open_existing_file():
        app = Application()
        app.open_application()
        app.open_file('old.docx')
        app.write_text('Extra Line Text')
        app.save_document_as('new.docx')
        app.quit_application()

    if __name__ == "__main__":
        open_existing_file()

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../robot/Word/Application.rst
   python
