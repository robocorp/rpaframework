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

``Request Response`` can be invoked in two ways:

    1. Without any parameters. This means that form shown is the one created
       by other library keywords. If no form elements have been added with
       keywords then the form will contain just one submit button. Form building
       must be started with keyword ``Create Form``.
    2. Giving filepath to JSON (parameter **formspec**) which specifies the
       elements that form should include.

Keyword has optional parameters to specify form window **width** and **height**,
default size is 600px width and 1000px height.


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
    - hiddeninput (HTML <input type='hidden'>)
    - submit (HTML <input type='submit'>)

Example JSON file which contains all possible form elements and their attributes.

.. literalinclude:: /attachments/questionform.json
  :language: JSON

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
    Ask Question From User By Build a Form
        Create Form     questions
        Add Text Input  label=What is your name?  name=username
        &{response}=    Request Response
        Log             Username is "${response}[username]"

    Ask Question From User By Form Specified by JSON
        &{response}=    Request Response  /path/to/myform.json
        Log             Username is "${response}[username]"

Python
======

The library can also be used inside Python.

.. code-block:: python
    :linenos:

    from RPA.Dialogs import Dialogs

    def ask_question_from_user(question, attribute):
        d = Dialogs()
        d.create_form('questions')
        d.add_text_input(label=question, name=attribute)
        response = request_response()
        return response

    response = ask_question_from_user('What is your name ?', 'username')
    print(f"Username is '{response['username']}'")



*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Dialogs.rst
   python
