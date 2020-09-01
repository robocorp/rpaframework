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

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Archive.rst
   python
