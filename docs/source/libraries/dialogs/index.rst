#######
Dialogs
#######

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

The `Dialogs` library provides a way to ask for user input during executions
through HTML forms. Form elements can be built with library keywords or they can
be defined in a static JSON file.

How the library works
=====================

The main keyword of the library is ``Request Response`` which works as follows:

1. It starts an HTTP server in the background
2. The HTML form is generated either according to a JSON file or the
   keywords called during the task
3. It opens a browser and shows the created form (The browser is opened with
   the ``Open Available Browser`` keyword from the ``RPA.Browser`` library)
4. Once the form is filled and submitted by the user, the server will process
   the response and extract the field values, which in turn are returned by the keyword
5. In the end, the browser is closed and the HTTP server is stopped

``Request Response`` can be invoked in two ways:

1. Without any parameters. This means that form shown is the one created
   by other library keywords. If no form elements have been added with
   keywords then the form will contain just one submit button. Form building
   must be started with the keyword ``Create Form``.
2. Giving a path to a JSON file (using the parameter **formspec**) which
   specifies the elements that form should include.

The keyword has optional parameters to specify form window **width** and **height**.
The default size is 600px wide and 1000px high.

Setting library arguments
=========================

Library has arguments ``server_port`` and ``stylesheet``. The ``server_port`` argument
takes integer value, which defines port where HTTP server will be run. By default port is 8105.
The ``stylesheet`` can be used to point CSS file, which will be used to modify style of form,
which is shown to the user. Defaults to built-in Robocorp stylesheet.

Supported element types
=======================

As a bare minimum, the form is displayed with a submit button when the
``Request Response`` keyword is called.

The supported input elements and their corresponding HTML tags are:

- form (``<form>``)
- title (``<h3>``)
- text (``<p>``)
- radiobutton  (``<input type='radio'>``)
- checkbox (``<input type='checkbox'>``)
- dropdown (``<select>``)
- textarea (``<textarea>``)
- textinput (``<input type='text'>``)
- fileinput (``<input type='file'>``)
- hiddeninput (``<input type='hidden'>``)
- submit (``<input type='submit'>``)

An example JSON file which contains all possible form elements and their attributes:

.. literalinclude:: /attachments/questionform.json
  :language: JSON

About file types
================

The ``Add File Input`` keyword has parameter ``filetypes``. Parameter sets filter
for file types that can be uploaded via element. Parameter can be set to ``filetypes=${EMPTY}``
to accept all files. Multiple types are separated with comma ``filetypes=image/jpeg,image/png``.

Some common filetypes:

- image/* (all image types)
- audio/* (all audio types)
- video/* (all video types)
- application/pdf (PDFs)
- application/vnd.ms-excel (.xls, .xlsx)

The list of all possible `MIME-types <http://www.iana.org/assignments/media-types/media-types.xhtml>`_.

********
Examples
********

Robot Framework
===============

Examples of creating forms through keywords and a JSON file:

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Dialogs

    *** Keywords ***
    Ask Question From User By Form Built With Keywords
        Create Form     questions
        Add Text Input  label=What is your name?  name=username
        &{response}=    Request Response
        Log             Username is "${response}[username]"

    Ask Question From User By Form Specified With JSON
        &{response}=    Request Response  /path/to/myform.json
        Log             Username is "${response}[username]"

Python
======

The library can also be used inside Python:

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

See :download:`libdoc documentation <../../libdoc/RPA_Dialogs.html>`.

.. toctree::
   :maxdepth: 1

   ../../robot/Dialogs.rst
   python
