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

.. toctree::
   :maxdepth: 1

   ../../libdoc/Cloud/Google.rst
   python
