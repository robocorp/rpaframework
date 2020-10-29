####
JSON
####

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`JSON` is a library for reading and writing `JSON`_ files and objects.
Locating specific elements in the structure is done using `JSONPath`_.

.. _JSON: http://json.org/
.. _JSONPath: http://goessner.net/articles/JsonPath/

********
Examples
********

.. code-block:: robotframework
   :linenos:

   *** Settings ***
   Library           RPA.JSON

   *** Tasks ***
   Read JSON and update values
      ${customers}    Load JSON From File    customers.json
      ${customer}     Create Dictionary    name=John Doe    address=Main Road 12
      ${customers}    Add To JSON    ${customers}    $    ${customer}
      ${customers}    Update Value To JSON
      ...             ${customers}
      ...             $.customers[?(@.name='Tim Thompson')].address
      ...             New Location 2
      Save JSON To File    ${customers}    customers.json


.. code-block:: python
    :linenos:

    from RPA.JSON import JSON

    lib = JSON()
    customers = lib.load_json_from_file('customers.json')
    customers = lib.delete_from_json(customers, "$.customers[?(@.name='Tim Thompson')]")
    lib.save_json_to_file('customers.json')

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/JSON.rst
   python
