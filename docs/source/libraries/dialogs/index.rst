#######
Dialogs
#######

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

The `Dialogs` library provides features for building form to request for
user input. Form elements can be built with library keywords or form can
be defined in a JSON file.

How library works
=================

Main keyword of the library is ``Request Response`` working in following steps:

    1. starts HTTP server on the background
    2. creates HTML form either according to JSON or to
     one built with keywords
    3. opens browser and the created form for the user (browser is opened with
     ``Open Available Browser`` keyword from ``RPA.Browser`` library)
    4. once form is submitted the server will process the post
     and returns response which will be returned by the keyword
    5. at the end the browser is closed and HTTP server is stopped


Supported element types
=======================

As a bare minimum the form is displayed with a submit button, when ``Request Response``
keyword is called.

    - form (HTML <form>)
    - title (HTML <h3>)
    - text (HTML <p>)
    - radiobutton  (HTML <input type='radio'>)
    - checkbox (HTML <input type='checkbox'>)
    - dropdown (HTML <select>)
    - textarea (HTML <textarea>)
    - textinput (HTML <input type='text'>)
    - fileinput (HTML <input type='file'>)
    - submit (HTML <input type='submit'>)

********
Examples
********

Robot Framework
===============

The library allows, for instance, iterating over files and inspecting them.

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Dialogs

    *** Keywords ***
    Ask Question From User
        No Operation

Python
======

The library can also be used inside Python.

.. code-block:: python
    :linenos:

    from RPA.Dialogs import Dialogs

    def ask_question_from_user():
        pass


*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Dialogs.rst
   python
