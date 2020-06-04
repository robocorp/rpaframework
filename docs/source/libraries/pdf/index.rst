###
PDF
###

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`PDF` is a library for managing PDF documents.

It provides an easy method of generating a PDF document from an HTML formatted
template file.

********
Examples
********

Robot Framework
===============

.. literalinclude:: order.template
    :linenos:
    :caption: order.template
    :language: html

.. code-block:: robotframework
    :linenos:
    :caption: example.robot

    *** Settings ***
    Library    RPA.PDF

    *** Variables ***
    ${TEMPLATE}    order.template
    ${PDF}         result.pdf
    &{VARS}        name=Robot Generated
    ...            email=robot@domain.com
    ...            zip=00100
    ...            items=Item 1, Item 2

    *** Tasks ***
    Create PDF from HTML template
        Template HTML to PDF   ${TEMPLATE}  ${PDF}  ${VARS}

Python
======

.. code-block:: python
    :linenos:
    :caption: example.py

    from RPA.PDF import PDF

    p = PDF()
    orders = ["item 1", "item 2", "item 3"]
    vars = {
        "name": "Robot Process",
        "email": "robot@domain.com",
        "zip": "00100",
        "items": "<br/>".join(orders),
    }
    p.template_html_to_pdf("order.template", "order.pdf", vars)

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/PDF.rst
   python
