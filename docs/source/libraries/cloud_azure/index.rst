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

List of supported language locales - `Azure locale list`_.
List of supported region identifiers - `Azure region list`_.

List of supported service names:

   - computervision (Azure `Computer Vision`_ API)
   - face (Azure `Face`_ API)
   - speech (Azure `Speech Services`_ API)
   - textanalytics (Azure `Text Analytics`_ API)

.. _Computer Vision: https://docs.microsoft.com/en-us/azure/cognitive-services/computer-vision/
.. _Face: https://docs.microsoft.com/en-us/azure/cognitive-services/face/
.. _Speech Services: https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/
.. _Text Analytics: https://docs.microsoft.com/en-us/azure/cognitive-services/text-analytics/
.. _Azure locale list: https://docs.microsoft.com/en-gb/azure/cognitive-services/speech-service/language-support#speech-to-text
.. _Azure region list: https://docs.microsoft.com/en-gb/azure/cognitive-services/speech-service/regions#speech-to-text-text-to-speech-and-translation

********
Examples
********

Robot Framework
===============

This is a section which describes how to use the library in your
Robot Framework tasks.




Python
======

This is a section which describes how to use the library in your
own Python modules.



*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Cloud/Azure.rst
   python
