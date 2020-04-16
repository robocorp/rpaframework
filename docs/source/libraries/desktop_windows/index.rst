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

Running Windows applications
============================

Windows applications can be started in several ways and library supports
following keywords:
    - Open Application (dispatch Office applications)
    - Open File (open file as process which opens associated application)
    - Open Executable (uses pywinauto start)
    - Open Using Run Dialog (uses Windows run dialog)
    - Open From Search (uses Windows search dialog)

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

Current method of inspecting elements on Windows is `inspect.exe` which is part
of `Windows SDK <https://docs.microsoft.com/en-us/windows/win32/winauto/inspect-objects>`_.

Keyboard
========

Keyword `send_keys` can be used to send keys to active window and keyword
`type_keys` sends keys to active window element.

Special key codes are documented on `pywinauto <https://pywinauto.readthedocs.io/en/latest/code/pywinauto.keyboard.html#>`_
documentation page.

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
    Library          RPA.Desktop.Windows
    Suite Teardown   Close all applications

    *** Tasks ***
    Open Calculator using run dialog
        ${result}=              Open using run dialog    calc.exe   Calculator
        ${result}=              Get Window Elements
        Send Keys               5*2=
        ${result}=              Get element             partial name:Display is
        Log Many                ${result}
        ${result}=              Get element rich text   id:CalculatorResults
        Should Be Equal As Strings  ${result}  Display is 10
        ${result}=              Get element rectangle   partial name:Display is
        ${result}=              Is Element Visible      CalculatorResults
        ${result}=              Is Element Enabled      partial name:Display is


Python
======

This is a section which describes how to use the library in your
own Python modules.

.. code-block:: python
    :linenos:

    from RPA.Desktop.Windows import Windows

    win = Windows()

    def open_calculator():
        win.open_from_search("calc.exe", "Calculator")
        elements = win.get_window_elements()

    def make_calculations(expression):
        win.send_keys(expression)
        result = win.get_element_rich_text('id:CalculatorResults')
        return int(result.strip('Display is '))

    if __name__ == "__main__":
        open_calculator()
        exp = '5*2='
        result = make_calculations(exp)
        print(f"Calculation result of '{exp}' is '{result}'")
        win.close_all_applications()

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Desktop/Windows.rst
   python

****
Todo
****

- Inspecter tool for identifying Windows locators
