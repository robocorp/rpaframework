#######
Browser
#######

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Browser` is a library for interfacing with web browsers like Chrome,
Firefox, Safari, Edge, and Opera. The library extends `SeleniumLibrary`_.

.. _SeleniumLibrary:
    https://robotframework.org/SeleniumLibrary/SeleniumLibrary.html

********
Examples
********

Robot Framework
===============

The library provides a special keyword `Open Available Browser`.

The keyword opens the first available webdriver in the running environment.
For example, for `Windows`, the browser list in preference order
is Chrome, Firefox, Edge, IE, and Opera. The opening is tried in three
different ways for each webdriver type.

    1. Try to open the webdriver "normally"
    2. Download the driver if the browser has driver available and try to open the webdriver again
    3. Try to open the webdriver in "headless" mode if that was not the original intention
    4. Move to the next webdriver type if steps 1-3 fail


.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Browser

    *** Tasks ***
    Opening page
        Open Available Browser  https://www.google.com

Python
======

.. code-block:: python
    :linenos:

    from RPA.Browser import Browser

    br = Browser()
    br.open_available_browser("https://www.google.com", headless=True)
    br.input_text("//input[@name='q']", "robocorp")
    br.screenshot(page=True, locator="//input[@name='q']")

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Browser.rst
   python
