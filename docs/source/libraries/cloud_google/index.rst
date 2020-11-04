############
Cloud.Google
############

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Google` is a library for operating with Google API endpoints.

Usage requires the following steps:

- Create a GCP project
- Create a service account key file (JSON) and save it to a place the robot
  can use it
- Enable APIs
- Install rpaframework[google]

Google authentication
======================

Authentication for Google is set with `service credentials JSON file` which can be given to the library
in three different ways.

- Method 1 as environment variables, ``GOOGLE_APPLICATION_CREDENTIALS`` with path to JSON file.
- Method 2 as keyword parameter to ``Init Storage Client`` for example.
- Method 3 as Robocloud vault secret. The vault name and secret key name needs to be given in library init
  or with keyword ``Set Robocloud Vault``. Secret value should contain JSON file contents.

Method 1. service credentials using environment variable

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.Google

    *** Tasks ***
    Init Google services
        # NO parameters for Vision Client, expecting to get JSON
        # with GOOGLE_APPLICATION_CREDENTIALS environment variable
        Init Vision Client

Method 2. service credentials with keyword parameter

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.Google

    *** Tasks ***
    Init Google services
        Init Speech To Text Client  /path/to/service_credentials.json

Method 3. setting Robocloud Vault in the library init

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.Google
    ...       robocloud_vault_name=googlecloud
    ...       robocloud_vault_secret_key=servicecreds

    *** Tasks ***
    Init Google services
        Init Storage Client   use_robocloud_vault=${TRUE}

Method 3. setting Robocloud Vault with keyword

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.Google

    *** Tasks ***
    Init Google services
        Set Robocloud Vault   vault_name=googlecloud  vault_secret_key=servicecreds
        Init Storage Client   use_robocloud_vault=${TRUE}

Requirements
============

Due to number of dependencies related to Google Cloud services this library has been set as
an optional package for ``rpaframework``.

This can be installed by opting in to the `google` dependency:

``pip install rpaframework[google]``

********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.Google

    *** Variables ***
    ${SERVICE CREDENTIALS}    ${/}path${/}to${/}service_credentials.json
    ${BUCKET_NAME}            testbucket12213123123

    *** Tasks ***
    Upload a file into a new storage bucket
        [Setup]   Init Storage Client   ${SERVICE CREDENTIALS}
        Create Bucket    ${BUCKET_NAME}
        Upload File      ${BUCKET_NAME}   ${/}path${/}to${/}file.pdf  myfile.pdf
        @{files}         List Files   ${BUCKET_NAME}
        FOR   ${file}  IN   @{files}
            Log  ${file}
        END

Python
======

.. code-block:: python
    :linenos:

    from RPA.Cloud.Google import Google

    library = Google
    service_credentials = '/path/to/service_credentials.json'

    library.init_vision_client(service_credentials)
    library.init_text_to_speech(service_credentials)

    response = library.detect_text('imagefile.png', 'result.json')
    library.synthesize_speech('I want this said aloud', target_file='said.mp3')

*****************
API Documentation
*****************

See :download:`libdoc documentation <../../libdoc/RPA_Cloud_Google.html>`.

.. toctree::
   :maxdepth: 1

   ../../robot/Cloud/Google.rst
   python
