#########
Cloud.AWS
#########

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`AWS` is a library for operating with Amazon AWS services.

Service initialization can be given as parameters for ``init_s3_service`` keyword
for example or keyword can read them in as environment variables:

    - `AWS_KEY_ID`
    - `AWS_KEY`

Requirements
============

The default installation depends on `boto3`_ library. Due to the size of the
dependency this has been set as optional package for ``rpa-framework``.

This can be installed by opting in to the `aws` dependency:

``pip install rpa-framework[aws]``

.. _boto3:
    https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

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
    Library   RPA.Cloud.AWS   region=us-east-1

    *** Variables ***
    ${BUCKET_NAME}        testbucket12213123123

    *** Tasks ***
    Upload file into S3 bucket
        [Setup]   Init S3 Client
        Upload File      ${BUCKET_NAME}   ${/}path${/}to${/}file.pdf
        @{files}         List Files   ${BUCKET_NAME}
        FOR   ${file}  IN   @{files}
            Log  ${file}
        END


Python
======

This is a section which describes how to use the library in your
own Python modules.

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
