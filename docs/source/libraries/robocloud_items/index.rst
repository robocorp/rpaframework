###############
Robocloud.Items
###############

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`WorkItems` is a library for managing data that goes through multiple
activities in an RPA process. Each execution of an activity receives
a work item from the previous activity, and after the activity is finished, it
is forwarded to the next one. During the execution, it can freely
read and update the data contained in an item.

The default implementation uses Robocloud to store the data, but the library
allows using custom adapters.

********
Examples
********

Robot Framework
===============

.. literalinclude:: ../../../../tests/robot/test_robocloud_items.robot
    :language: robotframework
    :end-before: Keywords

Python
======

.. code-block:: python
    :linenos:

    from RPA.WorkItems import WorkItem

    def show_values(item_id):
        """Load work item and show current variables"""
        item = WorkItem(item_id)
        item.load()
        logging.info("Current variables: %s", item.variables)

    def update_with_context(name, value):
        """Update value using context manager"""
        with WorkItem() as item:
            item.update({name: value})

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Robocloud/Items.rst
   python
