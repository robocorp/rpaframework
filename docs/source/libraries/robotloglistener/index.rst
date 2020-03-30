################
RobotLogListener
################

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`RobotLogListener` is a library library which implements Robot Framework Listener v2 interface.

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
    Library         RPA.RobotLogListener

    *** Tasks ***
    Protecting keywords
       This will not output        # will output because called before register
       Register Protected Keywords    This will not output
       This will not output        # is now registered
       This will output

    *** Keywords ***
    This will not output
       Log   1

    This will output
       Log   2


Python
======

This is a section which describes how to use the library in your
own Python modules.

.. code-block:: python
    :linenos:

    from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
    from RPA.RobotLogListener import RobotLogListener

    try:
       BuiltIn().import_library("RPA.RobotLogListener")
    except RobotNotRunningError:
       pass

    class CustomLibrary:

       def __init__(self):
          listener = RobotLogListener()
          listener.register_protected_keywords(
                ["CustomLibrary.special_keyword"]
          )

       def special_keyword(self):
          print('will not be written to log')
          return 'not shown in the log'


*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/RobotLogListener.rst
   python
