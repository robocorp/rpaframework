#######################
Desktop.OperatingSystem
#######################

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`OperatingSystem` is a cross platform library for managing
computer properties and actions.

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
    Library    RPA.Desktop.OperatingSystem

    *** Tasks ***
    Get computer information
        ${boot_time}=   Get Boot Time  as_datetime=${TRUE}
        ${machine}=     Get Machine Name
        ${username}=    Get Username
        &{memory}=      Get Memory Stats
        Log Many        ${memory}

Python
======

This is a section which describes how to use the library in your
own Python modules.

.. code-block:: python
    :linenos:

    from RPA.Desktop.OperatingSystem import OperatingSystem

    def get_computer_information():
        ops = OperatingSystem()
        print(f"Boot time    : { ops.get_boot_time(as_datetime=True) }\n"
              f"Machine name : { ops.get_machine_name() }\n"
              f"Username     : { ops.get_username() }\n"
              f"Memory       : { ops.get_memory_stats() }\n")

    if __name__ == "__main__":
        get_computer_information()

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Desktop/OperatingSystem.rst
   python
