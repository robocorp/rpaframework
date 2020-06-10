#########
Cloud.AWS
#########

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`AWS` is a library for operating with Amazon AWS services S3, SQS, Textract and Comprehend.

Services are initialized with keywords like ``Init S3 Client`` for S3.

AWS authentication
======================

Authentication for AWS is set with `key id` and `access key` which can be given to the library
in three different ways.

    - Method 1 as environment variables, ``AWS_KEY_ID`` and ``AWS_KEY``.
    - Method 2 as keyword parameters to ``Init Textract Client`` for example.
    - Method 3 as Robocloud vault secret. The vault name needs to be given in library init or
      with keyword ``Set Robocloud Vault``. Secret keys are expected to match environment variable
      names.

Method 1. credentials using environment variable

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.AWS

    *** Tasks ***
    Init AWS services
        # NO parameters for client, expecting to get credentials
        # with AWS_KEY and AWS_KEY_ID environment variable
        Init S3 Client

Method 2. credentials with keyword parameter

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.AWS

    *** Tasks ***
    Init AWS services
        Init S3 Client  aws_key_id=${AWS_KEY_ID}  aws_key=${AWS_KEY}

Method 3. setting Robocloud Vault in the library init

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.AWS  robocloud_vault_name=aws

    *** Tasks ***
    Init AWS services
        Init S3 Client  use_robocloud_vault=${TRUE}

Method 3. setting Robocloud Vault with keyword

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.AWS

    *** Tasks ***
    Init Azure services
        Set Robocloud Vault         vault_name=aws
        Init Textract Client  use_robocloud_vault=${TRUE}

Requirements
============

The default installation depends on `boto3`_ library. Due to the size of the
dependency, this library has been set as an optional package for ``rpaframework``.

This can be installed by opting in to the `aws` dependency:

``pip install rpaframework[aws]``

.. _boto3:
    https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library   RPA.Cloud.AWS   region=us-east-1

    *** Variables ***
    ${BUCKET_NAME}        testbucket12213123123

    *** Tasks ***
    Upload a file into S3 bucket
        [Setup]   Init S3 Client
        Upload File      ${BUCKET_NAME}   ${/}path${/}to${/}file.pdf
        @{files}         List Files   ${BUCKET_NAME}
        FOR   ${file}  IN   @{files}
            Log  ${file}
        END


Python
======

.. code-block:: python
    :linenos:

    from RPA.Cloud.AWS import AWS

    library = AWS(region="us-east-1")
    library.init_s3_client()

    test_bucket = "testbucket12213123123"
    buckets = library.list_buckets()
    for b in buckets:
        print(b)

    status, error = library.upload_file(test_bucket, "/path/to/myfile.txt")
    print(status, error)

    filelist = [
        "/path/to/file1.pdf",
        "/path/to/file2.xls",
        "/path/to/file3.jpg",
    ]
    ret = library.upload_files(test_bucket, filelist)
    print('upload file count: ', ret)

    files = library.list_files(test_bucket)
    for f in files:
        print(f)

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Cloud/AWS.rst
   python
