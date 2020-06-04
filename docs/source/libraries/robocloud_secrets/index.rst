#################
Robocloud.Secrets
#################

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`Secrets` is a library for interfacing secrets set in the Robocloud Vault
(used by default) or file-based secrets, which can be taken into use
by setting two environment variables below.

Robocloud Vault works together with Robocloud Worker or Robocode CLI.
Following three environment variables need to exist (these are set by
Robocloud Worker automatically and can be set manually with Robocode CLI).

    - RC_API_SECRET_HOST : URL to Robocloud Secrets API
    - RC_API_SECRET_TOKEN : API Token for Robocloud Secrets API
    - RC_WORKSPACE_ID : Robocloud Workspace ID

File based secrets can be set by defining two environment variables.

    - RPA_SECRET_MANAGER : 'RPA.Robocloud.Secrets.FileSecrets'
    - RPA_SECRET_FILE : Absolute path to the secrets JSON file.


.. code-block:: json
    :caption: Example secret json file
    :linenos:

    {
        "swaglabs": {
            "username": "standard_user",
            "password": "secret_sauce"
        }
    }

********
Examples
********

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library    RPA.Robocloud.Secrets

    *** Tasks ***
    Reading secrets
        ${secrets}=   Get Secret  swaglabs
        Log Many      ${secrets}


Python
======

.. code-block:: python
    :linenos:

    from RPA.Robocloud.Secrets import Secrets

    def read_secrets():
        """Read secrets from Robocloud Vault or FileSecrets."""

        secret = Secrets()
        print(f"My secrets: {secret.get_secret('swaglabs')}")

    if __name__ == "__main__":
        read_secrets()

*****************
API Documentation
*****************

.. toctree::
   :maxdepth: 1

   ../../libdoc/Robocloud/Secrets.rst
   python
