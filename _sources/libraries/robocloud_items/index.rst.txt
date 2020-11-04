###############
Robocloud.Items
###############

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Items` is a library for interacting with RPA work items.
Work items are used for managing data that go through multiple
activities and tasks inside a process. Each execution of an activity receives
a work item from the previous activity, and after the activity is finished, it
is forwarded to the next one. During the execution, it can freely
read and update the data contained in an item.

The default implementation uses Robocloud to store the data, but the library
allows using custom adapters.

Default environment
===================

The library automatically loads the work item defined by its runtime
environment if the argument ``load_env`` is truthy (enabled by default).
This functionality is controlled by the following environment variables:

* ``RC_WORKSPACE_ID``: The ID for the Robocloud workspace
* ``RC_WORKITEM_ID``:  The ID for the Robocloud work item

These values are dynamic and should be set by Robocloud, but can be
overriden manually while developing an activity.

Item structure
==============

A work item's data payload is JSON and allows storing anything that is
serializable. This library creates an object with the key 'variables'
that contains key-value pairs of a variable name and its contents.
These variables can be exposed to the Robot Framework task to be used directly.

In addition to the data section, a work item can also contain files,
which are stored by default in Robocorp's cloud. Adding and using
files with work items requires no additional setup from the user.

Workflow
========

While a work item is loaded automatically when a suite starts, changes are
not automatically reflected back to the source. The work item will be modified
locally and then saved when the corresponding keyword is explicitly called.
It is recommended to defer all saves to the end of the task to prevent
leaving work items in a half-modified state after failures.

Custom adapters
===============

While Robocloud is the default implementation, it can also be replaced
with a custom adapter. The selection is based on either the ``default_adapter``
argument for the library, or the ``RPA_WORKITEMS_ADAPTER`` environment
variable. A custom implementation should inherit from the ``BaseAdapter``
class. The library has a built-in alternative adapter called FileAdapter for
storing work items to disk.

********
Examples
********

Robot Framework
===============

In the following example the work item is modified locally and then saved
back to Robocloud. Also note how the work item is loaded implicitly when
the suite starts.

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Robocloud.Items

    *** Tasks ***
    Save variables to Robocloud
        Add work item file    orders.xlsx
        Set work item variables    user=Dude    mail=address@company.com
        Save work item

Later in the process inside a different robot, we can use previously saved
work item variables and files. The library also allows injecting the variables
directly into the current task execution.

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Robocloud.Items

    *** Tasks ***
    Use variables from Robocloud
        Set task variables from work item
        Log    Variables are now available: ${user}, ${mail}
        ${path}=    Get work item file    orders.xlsx
        Log    Files are also stored to disk: ${path}

Python
======

The library can also be used through Python, but it does not implicitly
load the work item for the current execution.

.. code-block:: python
    :linenos:

    import logging
    from RPA.Robocloud.Items import Items

    def list_variables(item_id):
        """Load work item and log current variables"""
        library = Items()
        library.load_work_item_from_environment()

        for variable, value in library.get_work_item_variables().items():
            logging.info("%s = %s", variable, value)


*****************
API Documentation
*****************

See `libdoc documentation <../../libdoc/RPA_Robocloud_Items.html>`_.

.. toctree::
   :maxdepth: 1

   ../../robot/Robocloud/Items.rst
   python
