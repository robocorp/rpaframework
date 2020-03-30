.. _library-desktop-windows:

###############
Desktop.Windows
###############

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Windows` is a library for managing Windows operating system.

Locators
========

`Locator` is used to identify element for interaction - usually for mouse click.

Locators can investigated for application once it has been opened by calling
keyword `get_windows_elements` which can also store locator information into `json` file
and `screenshot` of the element into image file.

Identifying locator
===================

Element needs to be identified by unique method for example "Three" for button 3
in the Calculator application. It can be given either by `Three` or `name:Three`.

Possible search criterias:
    - name
    - class (class_name)
    - type (control_type)
    - id (automation_id)
    - any if none was defined

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
    Library    RPA.Desktop.Windows

    *** Tasks ***
    Open application
        Open Process  calc.exe    Calculator
        Type Keys     6*55=
        Sleep         3s
        Mouse Click   Clear

Python
======

This is a section which describes how to use the library in your
own Python modules.

.. code-block:: python
    :linenos:

    from RPA.Desktop.Windows import Windows, delay

    def use_calculator():
        win = Windows()
        win.open_process("calc.exe", "Calculator")
        win.type_keys("6*55=")
        delay(3)
        win.mouse_click("Clear")
        delay(3)
        win.quit()

    if __name__ == "__main__":
        use_calculator()

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Desktop/Windows.rst
   python
