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

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Desktop.Clipboard

    *** Tasks ***
    Clipping
        Copy To Clipboard   Text from Robot to clipboard
        ${var}=             Paste From Clipboard
        Clear Clipboard

Python
======

.. code-block:: python
    :linenos:

    from RPA.Desktop.Clipboard import Clipboard

    clip = Clipboard()
    clip.copy_to_clipboard('Text from Python to clipboard')
    text = clip.paste_from_clipboard()
    print(f"clipboard had text: '{text}'")
    clip.clear_clipboard()

*****************
API Documentation
*****************

See `libdoc documentation <../../libdoc/RPA_Desktop_Clipboard.html>`_.

.. toctree::
   :maxdepth: 1

   ../../robot/Desktop/Clipboard.rst
   python
