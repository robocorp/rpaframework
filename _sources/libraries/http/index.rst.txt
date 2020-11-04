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

The library extends Robot Framework `RequestsLibrary`_ functionality with
RPA-oriented keywords.

.. _RequestsLibrary: https://github.com/MarketSquare/robotframework-requests

********
Examples
********

Robot Framework
===============

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

.. code-block:: python
    :linenos:

    from RPA.HTTP import HTTP

    library = HTTP()
    url = "https://ec.europa.eu/energy/sites/ener/files/documents/EnergyDailyPricesReport-EUROPA_0.pdf"
    response = library.http_get(url, "prices.pdf")


*****************
API Documentation
*****************

See :download:`libdoc documentation <../../libdoc/RPA_HTTP.html>`.

.. toctree::
   :maxdepth: 1

   ../../robot/HTTP.rst
   python
