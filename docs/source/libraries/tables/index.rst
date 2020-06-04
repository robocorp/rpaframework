######
Tables
######

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Tables` is a library for manipulating tabular data inside Robot Framework.
It can import data from various sources and apply different operations to it.
Common use-cases are reading and writing CSV files, inspecting files in
directories, or running tasks using existing Excel data.

Import types
============

The data from which a table can be created can be of two main types:

1. An iterable of individual rows, like a list of lists, or list of dictionaries
2. A dictionary of columns, where each dictionary value is a list of values

For instance, these two input values:

.. code-block:: python

    data1 = [
        {"name": "Mark", "age": 58},
        {"name": "John", "age": 22},
        {"name": "Adam", "age": 67},
    ]

    data2 = {
        "name": ["Mark", "John", "Adam"],
        "age":  [    58,     22,     67],
    }

Would both result in the following table:

+-----------+----------+---------+
| **Index** | **Name** | **Age** |
+-----------+----------+---------+
|         1 |     Mark |      58 |
+-----------+----------+---------+
|         2 |     John |      22 |
+-----------+----------+---------+
|         3 |     Adam |      67 |
+-----------+----------+---------+

********
Examples
********

Robot Framework
===============

The `Tables` library can load tabular data from various other libraries
and manipulate it inside Robot Framework.

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Tables

    *** Keywords ***
    Files to Table
        ${files}=    List files in directory    ${CURDIR}
        ${files}=    Create table    ${files}
        Filter table by column    ${files}    size  >=  ${1024}
        FOR    ${file}    IN    @{files}
            Log    ${file}[name]
        END
        Write table to CSV    ${files}    ${OUTPUT_DIR}${/}files.csv

Python
======

The library is also available directly through Python, where it
is easier to handle multiple different tables or do more bespoke
manipulation operations.

.. code-block:: python
    :linenos:

    from RPA.Tables import Tables

    library = Tables()
    orders = library.read_table_from_csv(
        "orders.csv", columns=["name", "mail", "product"]
    )

    customers = library.group_table_by_column(rows, "mail")
    for customer in customers:
        for order in customer:
            add_cart(order)
        make_order()

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Tables.rst
   python
