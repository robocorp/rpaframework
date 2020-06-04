########
Database
########

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Database` is a library for handling different database operations.

The library extends `robotframework-databaselibrary`_.

.. _robotframework-databaselibrary:
    http://franz-see.github.io/Robotframework-Database-Library/api/1.2.2/DatabaseLibrary.html

********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   		RPA.Database
    Library   		RPA.Robocloud.Secrets.FileSecrets  secrets.json

    *** Tasks ***
    Get Orders From Database
        ${secrets}=     Get Secret   ordersecrets
        Connect To Database Using Custom Params    sqlite3    database="${secrets}[DATABASE]"
        ${orders}=   Database Query Result As Table  SELECT * FROM incoming_orders

Python
======

.. code-block:: python
    :linenos:

    import pprint
    from RPA.Database import Database
    from RPA.Robocloud.Secrets import FileSecrets

    pp = pprint.PrettyPrinter(indent=4)
    filesecrets = FileSecrets("secrets.json")
    secrets = filesecrets.get_secret("databasesecrets")

    db = Database()
    database_file = secrets["DATABASE_FILE"]
    db.connect_to_database_using_custom_params(
        "sqlite3", f"'{database_file}'",
    )
    orders = db.database_query_result_as_table("SELECT * FROM incoming_orders")
    for order in orders:
        print(order)

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Database.rst
   python
