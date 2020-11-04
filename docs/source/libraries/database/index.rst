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

All database operations are supported. Keywords `Query` and `Get Rows`
return values by default in `RPA.Table` format.

Library is compatible with any Database API Specification 2.0 module.

References:
    + Database API Specification 2.0 - http://www.python.org/dev/peps/pep-0249/
    + Lists of DB API 2.0 - http://wiki.python.org/moin/DatabaseInterfaces
    + Python Database Programming - http://wiki.python.org/moin/DatabaseProgramming/

********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   		RPA.Database

    *** Tasks ***
    Get Orders From Database
        Connect To Database  pymysql  tester  user  password  127.0.0.1
        @{orders}            Query    Select * FROM incoming_orders
        FOR   ${order}  IN  @{orders}
            Handle Order  ${order}
        END

Python
======

.. code-block:: python
    :linenos:


    from RPA.Database import Database
    from RPA.Robocloud.Secrets import FileSecrets

    filesecrets = FileSecrets("secrets.json")
    secrets = filesecrets.get_secret("databasesecrets")

    db = Database()
    db.connect_to_database('pymysql',
                        secrets["DATABASE"],
                        secrets["USERNAME"],
                        secrets["PASSWORD"],
                        '127.0.0.1'
                        )
    orders = db.query("SELECT * FROM incoming_orders")
    for order in orders:
        print(order)

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../robot/Database.rst
   python
