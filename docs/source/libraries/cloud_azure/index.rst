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

Authentication to Azure API is handled by `service subcription key` which
can set for all services using environment variable `AZURE_SUBSCRIPTION_KEY`.

If there are service specific subscription keys, these can be set using
environment variable `AZURE_SERVICENAME_KEY`. Replace `SERVICENAME` with service
name.

List of supported language locales - `Azure locale list`_

List of supported region identifiers - `Azure region list`_

List of supported service names:

   - computervision (`Azure Computer Vision API`_)
   - face (`Azure Face API`_)
   - speech (`Azure Speech Services API`_)
   - textanalytics (`Azure Text Analytics API`_)

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

.. toctree::
   :maxdepth: 1

   ../../libdoc/Cloud/Azure.rst
   python
