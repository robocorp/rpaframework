##########
Salesforce
##########

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Salesforce` is a library for accessing Salesforce using REST API.
The library extends `simple-salesforce library`_.

More information available at `Salesforce REST API Developer Guide`_.

Dataloader
==========

The keyword `execute_dataloader_import` can be used to mimic
`Salesforce Dataloader`_ import behaviour.

`input_object` can be given in different formats. Below is an example where
input is in `RPA.Table` format in **method a** and list format in **method b**.

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library     RPA.Salesforce
    Library     RPA.Database
    Task Setup  Authorize Salesforce

    *** Tasks ***
    # Method a
    ${orders}=        Database Query Result As Table
    ...               SELECT * FROM incoming_orders
    ${status}=        Execute Dataloader Insert
    ...               ${orders}  ${mapping_dict}  Tilaus__c
    # Method b
    ${status}=        Execute Dataloader Insert
    ...               ${WORKDIR}${/}orders.json  ${mapping_dict}  Tilaus__c


Example file **orders.json**

.. code-block:: json
    :linenos:

    [
        {
            "asiakas": "0015I000002jBLIQA2"
        },
        {
            "asiakas": "0015I000002jBLDQA2"
        },
    ]

`mapping_object` describes how the input data fields are mapped into Salesforce
object attributes. In the example, the mapping defines that `asiakas` attribute in the
input object is mapped into `Tilaaja__c` attribute of `Tilaus__c` custom Salesforce object.

.. code-block:: json
    :linenos:

    {
        "Tilaus__c": {
            "asiakas": "Tilaaja__c"
        },
    }

Object type could be, for example, `Tilaus__c`.

Salesforce object operations
============================

Following operations can be used to manage Salesforce object:

    * Get Salesforce Object By Id
    * Create Salesforce Object
    * Update Salesforce Object
    * Upsert Salesforce Object
    * Delete Salesforce Object
    * Get Salesforce Object Metadata
    * Describe Salesforce Object

.. _Salesforce REST API Developer Guide:
    https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_what_is_rest_api.htm

.. _simple-salesforce library:
    https://github.com/simple-salesforce/simple-salesforce

.. _Salesforce Dataloader:
    https://developer.salesforce.com/docs/atlas.en-us.dataLoader.meta/dataLoader/data_loader.htm

********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library     RPA.Salesforce
    Task Setup  Authorize Salesforce

    *** Variables ***
    ${ACCOUNT_NOKIA}    0015I000002jBLDQA2

    *** Tasks ***
    Change account details in Salesforce
        &{account}=      Get Salesforce Object By Id   Account  ${ACCOUNT_NOKIA}
        &{update_obj}=   Create Dictionary   Name=Nokia Ltd  BillingStreet=Nokia bulevard 1
        ${result}=       Update Salesforce Object  Account  ${ACCOUNT_NOKIA}  ${update_obj}

    *** Keywords ***
    Authorize Salesforce
        ${secrets}=     Get Secret   salesforce
        Auth With Token
        ...        username=${secrets}[USERNAME]
        ...        password=${secrets}[PASSWORD]
        ...        api_token=${secrets}[API_TOKEN]

Python
======

.. code-block:: python
    :linenos:
    :emphasize-lines: 2,9,10,16,24

    import pprint
    from RPA.Salesforce import Salesforce
    from RPA.Robocloud.Secrets import FileSecrets

    pp = pprint.PrettyPrinter(indent=4)
    filesecrets = FileSecrets("secrets.json")
    secrets = filesecrets.get_secret("salesforce")

    sf = Salesforce()
    sf.auth_with_token(
        username=secrets["USERNAME"],
        password=secrets["PASSWORD"],
        api_token=secrets["API_TOKEN"],
    )
    nokia_account_id = "0015I000002jBLDQA2"
    account = sf.get_salesforce_object_by_id("Account", nokia_account_id)
    pp.pprint(account)
    billing_information = {
        "BillingStreet": "Nokia Bulevard 1",
        "BillingCity": "Espoo",
        "BillingPostalCode": "01210",
        "BillingCountry": "Finland",
    }
    result = sf.update_salesforce_object("Account", nokia_account_id, billing_information)
    print(f"\nUpdate result: {result}")


*****************
API Documentation
*****************

See :download:`libdoc documentation <../../libdoc/RPA_Salesforce.html>`.

.. toctree::
   :maxdepth: 1

   ../../robot/Salesforce.rst
   python
