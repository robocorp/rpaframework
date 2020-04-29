####
HTTP
####

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`HTTP` library can be used to make HTTP requests.

Library will be extended by keywords that are more RPA-oriented.

Library is wrapping Robot Framework `RequestsLibrary`_ functionality.

.. _RequestsLibrary: https://hub.robocorp.com/libraries/bulkan-robotframework-requests

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
    Library    RPA.HTTP

    *** Variables ***
    ${URL}       https://ec.europa.eu/energy/sites/ener/files/documents/EnergyDailyPricesReport-EUROPA_0.pdf
    ${PDF_FILE}  prices.pdf

    *** Tasks ***
    Get Energy Prices
        HTTP GET   ${URL}  ${PDF_FILE}


Python
======

This is a section which describes how to use the library in your
own Python modules.
.. code-block:: python
    :linenos:

    from RPA.HTTP import HTTP

    h = HTTP()
    url = "https://ec.europa.eu/energy/sites/ener/files/documents/EnergyDailyPricesReport-EUROPA_0.pdf"
    response = h.http_get(url, "prices.pdf")


*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/HTTP.rst
   python
