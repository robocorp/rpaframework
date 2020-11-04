###########
Cloud.Azure
###########

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Azure` is a library for operating with Microsoft Azure API endpoints.

List of supported service names:

- computervision (`Azure Computer Vision API`_)
- face (`Azure Face API`_)
- speech (`Azure Speech Services API`_)
- textanalytics (`Azure Text Analytics API`_)

Azure authentication
======================

Authentication for Azure is set with `service subscription key` which can be given to the library
in two different ways.

- Method 1 as environment variables, either service specific environment variable
  for example ``AZURE_TEXTANALYTICS_KEY`` or with common key ``AZURE_SUBSCRIPTION_KEY`` which
  will be used for all the services.
- Method 2 as Robocloud vault secret. The vault name needs to be given in library init or
  with keyword ``Set Robocloud Vault``. Secret keys are expected to match environment variable
  names.

Method 1. subscription key using environment variable

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.Azure

    *** Tasks ***
    Init Azure services
        # NO parameters for client, expecting to get subscription key
        # with AZURE_TEXTANALYTICS_KEY or AZURE_SUBSCRIPTION_KEY environment variable
        Init Text Analytics Service

Method 2. setting Robocloud Vault in the library init

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.Azure  robocloud_vault_name=azure

    *** Tasks ***
    Init Azure services
        Init Text Analytics Service  use_robocloud_vault=${TRUE}

Method 2. setting Robocloud Vault with keyword

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.Azure

    *** Tasks ***
    Init Azure services
        Set Robocloud Vault          vault_name=googlecloud
        Init Text Analytics Service  use_robocloud_vault=${TRUE}

References
==========

List of supported language locales - `Azure locale list`_

List of supported region identifiers - `Azure region list`_

.. _Azure Computer Vision API: https://docs.microsoft.com/en-us/azure/cognitive-services/computer-vision/
.. _Azure Face API: https://docs.microsoft.com/en-us/azure/cognitive-services/face/
.. _Azure Speech Services API: https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/
.. _Azure Text Analytics API: https://docs.microsoft.com/en-us/azure/cognitive-services/text-analytics/
.. _Azure locale list: https://docs.microsoft.com/en-gb/azure/cognitive-services/speech-service/language-support#speech-to-text
.. _Azure region list: https://docs.microsoft.com/en-gb/azure/cognitive-services/speech-service/regions#speech-to-text-text-to-speech-and-translation

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
   Library  RPA.Cloud.Azure

   *** Variables ***
   ${IMAGE_URL}   IMAGE_URL
   ${FEATURES}    Faces,ImageType

   *** Tasks ***
   Visioning image information
      Init Computer Vision Service
      &{result}   Vision Analyze  image_url=${IMAGE_URL}  visual_features=${FEATURES}
      @{faces}    Set Variable  ${result}[faces]
      FOR  ${face}  IN   @{faces}
         Log  Age: ${face}[age], Gender: ${face}[gender], Rectangle: ${face}[faceRectangle]
      END

Python
======

This is a section which describes how to use the library in your
own Python modules.

.. code-block:: python
   :linenos:

   library = Azure()
   library.init_text_analytics_service()
   library.init_face_service()
   library.init_computer_vision_service()
   library.init_speech_service("westeurope")

   response = library.sentiment_analyze(
      text="The rooms were wonderful and the staff was helpful."
   )
   response = library.detect_face(
      image_file=PATH_TO_FILE,
      face_attributes="age,gender,smile,hair,facialHair,emotion",
   )
   for item in response:
      gender = item["faceAttributes"]["gender"]
      age = item["faceAttributes"]["age"]
      print(f"Detected a face, gender:{gender}, age: {age}")

   response = library.vision_analyze(
      image_url=URL_TO_IMAGE,
      visual_features="Faces,ImageType",
   )
   meta = response['metadata']
   print(
      f"Image dimensions meta['width']}x{meta['height']} pixels"
   )

   for face in response["faces"]:
      left = face["faceRectangle"]["left"]
      top = face["faceRectangle"]["top"]
      width = face["faceRectangle"]["width"]
      height = face["faceRectangle"]["height"]
      print(f"Detected a face, gender:{face['gender']}, age: {face['age']}")
      print(f"\tFace rectangle: (left={left}, top={top})")
      print(f"\tFace rectangle: (width={width}, height={height})")

   library.text_to_speech(
       text="Developer tools for open-source RPA leveraging the Robot Framework ecosystem",
       neural_voice_style="cheerful",
       target_file='output.mp3'
   )

*****************
API Documentation
*****************

See :download:`libdoc documentation <../../libdoc/RPA_Cloud_Azure.html>`.

.. toctree::
   :maxdepth: 1

   ../../robot/Cloud/Azure.rst
   python
