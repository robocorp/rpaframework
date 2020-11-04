###
FTP
###

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`FTP` library can be used to access FTP server.

The library is based Python `ftplib`_ functionality.

.. _ftplib: https://docs.python.org/3/library/ftplib.html

********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.FTP

    *** Variables ***
    ${HOST}       127.0.0.1
    ${PORT}       27345
    ${USER}       user
    ${PASS}       12345

    *** Tasks ***
    List files on the server directory
        Connect   ${HOST}  ${PORT}  ${USER}  ${PASS}
        @{files}  List Files
        FOR  ${file}  IN  @{files}
            Log  ${file}
        END


Python
======

.. code-block:: python
    :linenos:

    from RPA.FTP import FTP

    library = FTP()
    library.connect('127.0.0.1', 27345, 'user', '12345')
    files = library.list_files()
    for f in files:
        print(f)

*****************
API Documentation
*****************

See :download:`libdoc documentation <../../libdoc/RPA_FTP.html>`.

.. toctree::
   :maxdepth: 1

   ../../robot/FTP.rst
   python
