#######
Archive
#######

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Archive` is a library for operating with ZIP and TAR
packages.

See `API documentation` for detailed examples how to use
library.

********
Examples
********

.. code-block:: robotframework
   :linenos:

   *** Settings ***
   Library  RPA.Archive

   *** Tasks ***
   Creating a ZIP archive
      Archive Folder With ZIP   ${CURDIR}${/}tasks  tasks.zip   recursive=True  include=*.robot  exclude=/.*
      @{files}                  List Archive             tasks.zip
      FOR  ${file}  IN  ${files}
         Log  ${file}
      END
      Add To Archive            .${/}..${/}missing.robot  tasks.zip
      &{info}                   Get Archive Info


.. code-block:: python
    :linenos:

    from RPA.Archive import Archive

    lib = Archive()
    lib.archive_folder_with_tar('./tasks', 'tasks.tar', recursive=True)
    files = lib.list_archive('tasks.tar')
    for file in files:
       print(file)


*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../robot/Archive.rst
   python
