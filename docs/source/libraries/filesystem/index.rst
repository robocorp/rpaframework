##########
FileSystem
##########

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

The `FileSystem` library can be used to interact with files and directories
on the local computer. It can inspect and list files, remove and create them,
read contents from files, and write data out.

It shadows the built-in `OperatingSystem` library but contains keywords
which are more RPA-oriented.

********
Examples
********

Robot Framework
===============

The library allows, for instance, iterating over files and inspecting them.

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.FileSystem

    *** Keywords ***
    Delete large files
        ${files}=    List files in directory    archive/orders/
        FOR    ${file}  IN  @{FILES}
            Run keyword if    ${file.size} > 10**8    Remove file    ${file}
        END

    Read process output
        Start external program
        Wait until modified    process.log
        ${output}=  Read file  process.log
        [Return]    ${output}

Python
======

The library can also be used inside Python.

.. code-block:: python
    :linenos:

    from RPA.FileSystem import FileSystem

    def move_to_archive():
        lib = FileSystem()

        matches = lib.find_files("**/*.xlsx")
        if matches:
            lib.create_directory("archive")
            lib.move_files(matches, "archive")


*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/FileSystem.rst
   python
