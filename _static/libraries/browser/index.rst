#######
Browser
#######

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Browser` is library for interfacing with web browsers like Chrome,
Firefox, Safari, Edge and Opera. Library extends `SeleniumLibrary <https://hub.robocorp.com/libraries/robotframework-SeleniumLibrary/>`_.

********
Examples
********

Robot Framework
===============

This is a section which describes how to use the library in your
Robot Framework tasks.

Library provides special keyword `Open Available Browser` which
requires an explanation.

Keyword opens the first available webdriver in the running environment
which it can. For example for `Windows` the browser list in preference order
is Chrome, Firefox, Edge, IE and Opera. Opening is tried in three different
ways for each webdriver type.

    1. Try to open webdriver "normally"
    2. Download browser driver if browser has driven available and try open webdriver again
    3. Try to open webdriver in "headless" mode if that was not original intention
    4. Move to the next webdriver type if none of the steps 1-3 succeeds


.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Browser

    *** Tasks ***
    Opening page
        Open Available Browser  https://www.google.fi

Python
======

This is a section which describes how to use the library in your
own Python modules.

.. code-block:: python
    :linenos:

    from RPA.Browser import Browser

    br = Browser()
    br.open_available_browser("https://www.google.fi", headless=True)
    br.input_text("//input[@name='q']", "robocorp")
    br.screenshot(page=True, locator="//input[@name='q']")

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Browser.rst
   python
