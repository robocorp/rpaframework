#################
Desktop.Clipboard
#################

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Clipboard` is a library for managing clipboard - **copy** text to,
**paste** text from and **clear** clipboard contents.

********
Examples
********

Robot Framework
===============

This section describes how to use the library in your Robot Framework tasks.

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Desktop.Clipboard

    *** Tasks ***
    Clipping
        Copy To Clipboard   text from Robot to clipboard
        ${var}=             Paste From Clipboard
        Clear Clipboard

Python
======

This section describes how to use the library in your own Python modules.

.. code-block:: python
    :linenos:

    from RPA.Desktop.Clipboard import Clipboard

    clip = Clipboard()
    clip.copy_to_clipboard('text from Python to clipboard')
    text = clip.paste_from_clipboard()
    print(f"clipboard had text: '{text}'")
    clip.clear_clipboard()

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Desktop/Clipboard.rst
   python
