RPA Framework
=============

REQUEST for user input!
-----------------------

We are looking at improving our keyword usage to cover situations where developer might be
struggling to smoothly write task for a Robot. Describe the situation where your **implementation speed slows** due to the lack of easier syntax.

`Comment HERE <https://github.com/robocorp/rpaframework/issues/738>`_

.. contents:: Table of Contents
   :local:
   :depth: 1

.. include-marker



Introduction
------------

`RPA Framework` is a collection of open-source libraries and tools for
Robotic Process Automation (RPA), and it is designed to be used with both
`Robot Framework`_ and `Python`_. The goal is to offer well-documented and
actively maintained core libraries for Software Robot Developers.

Learn more about RPA at `Robocorp Documentation`_.

**The project is:**

- 100% Open Source
- Sponsored by Robocorp_
- Optimized for Robocorp `Control Room`_ and `Developer Tools`_
- Accepting external contributions

.. _Robot Framework: https://robotframework.org
.. _Robot Framework Foundation: https://robotframework.org/foundation/
.. _Python: https://www.python.org/
.. _Robocorp: https://robocorp.com
.. _Robocorp Documentation: https://robocorp.com/docs/
.. _Control Room: https://robocorp.com/docs/control-room
.. _Developer Tools: https://robocorp.com/downloads
.. _Installing Python Packages: https://robocorp.com/docs/setup/installing-python-package-dependencies

Links
^^^^^

- Homepage: `<https://www.github.com/robocorp/rpaframework/>`_
- Documentation: `<https://rpaframework.org/>`_
- PyPI: `<https://pypi.org/project/rpaframework/>`_
- Release notes: `<https://rpaframework.org/releasenotes.html>`_
- RSS feed: `<https://rpaframework.org/releases.xml>`_

------------

.. image:: https://img.shields.io/github/workflow/status/robocorp/rpaframework/rpaframework?style=for-the-badge
   :target: https://github.com/robocorp/rpaframework/actions/workflows/main.yaml
   :alt: Status

.. image:: https://img.shields.io/pypi/dw/rpaframework?style=for-the-badge
   :target: https://pypi.python.org/pypi/rpaframework
   :alt: rpaframework

.. image:: https://img.shields.io/pypi/l/rpaframework.svg?style=for-the-badge&color=brightgreen
   :target: http://www.apache.org/licenses/LICENSE-2.0.html
   :alt: License

------------

Packages
--------

.. image:: https://img.shields.io/pypi/v/rpaframework.svg?label=rpaframework&style=for-the-badge
   :target: https://pypi.python.org/pypi/rpaframework
   :alt: rpaframework latest version



.. image:: https://img.shields.io/pypi/v/rpaframework-aws.svg?label=rpaframework-aws&style=for-the-badge
   :target: https://pypi.python.org/pypi/rpaframework-aws
   :alt: rpaframework-aws latest version



.. image:: https://img.shields.io/pypi/v/rpaframework-core.svg?label=rpaframework-core&style=for-the-badge
   :target: https://pypi.python.org/pypi/rpaframework-core
   :alt: rpaframework-core latest version



.. image:: https://img.shields.io/pypi/v/rpaframework-dialogs.svg?label=rpaframework-dialogs&style=for-the-badge&color=blue
   :target: https://pypi.python.org/pypi/rpaframework-dialogs
   :alt: rpaframework-dialogs latest version



.. image:: https://img.shields.io/pypi/v/rpaframework-google.svg?label=rpaframework-google&style=for-the-badge&color=blue
   :target: https://pypi.python.org/pypi/rpaframework-google
   :alt: rpaframework-google latest version



.. image:: https://img.shields.io/pypi/v/rpaframework-pdf.svg?label=rpaframework-pdf&style=for-the-badge&color=blue
   :target: https://pypi.python.org/pypi/rpaframework-pdf
   :alt: rpaframework-pdf latest version



.. image:: https://img.shields.io/pypi/v/rpaframework-recognition.svg?label=rpaframework-recognition&style=for-the-badge&color=blue
   :target: https://pypi.python.org/pypi/rpaframework-recognition
   :alt: rpaframework-recognition latest version



.. image:: https://img.shields.io/pypi/v/rpaframework-windows.svg?label=rpaframework-windows&style=for-the-badge&color=blue
   :target: https://pypi.python.org/pypi/rpaframework-windows
   :alt: rpaframework-windows latest version

From the above packages **rpaframework-core** and **rpaframework-recognition** are support packages, which themselves do **not** contain any libraries.


Libraries
---------

The RPA Framework project currently includes the following libraries:

The ``x`` in the **PACKAGE** column means that library **is** included in the **rpaframework** package and for example. ``x,dialogs`` means that ``RPA.Dialogs`` library is provided in both the **rpaframework** and **rpaframework-dialogs** packages.

+----------------------------+-------------------------------------------------------+------------------------+
| **LIBRARY NAME**           | **DESCRIPTION**                                       | **PACKAGE**            |
+----------------------------+-------------------------------------------------------+------------------------+
| `Archive`_                 | Archiving TAR and ZIP files                           | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Browser.Selenium`_        | Control browsers and automate the web                 | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Browser.Playwright`_      | Newer way to control browsers                         | special (more below)   |
+----------------------------+-------------------------------------------------------+------------------------+
| `Cloud.AWS`_               | Use Amazon AWS services                               | x,aws                  |
+----------------------------+-------------------------------------------------------+------------------------+
| `Cloud.Azure`_             | Use Microsoft Azure services                          | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Cloud.Google`_            | Use Google Cloud services                             | google                 |
+----------------------------+-------------------------------------------------------+------------------------+
| `Crypto`_                  | Common hashing and encryption operations              | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Database`_                | Interact with databases                               | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Desktop`_                 | Cross-platform desktop automation                     | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Desktop.Clipboard`_       | Interact with the system clipboard                    | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Desktop.OperatingSystem`_ | Read OS information and manipulate processes          | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Dialogs`_                 | Request user input during executions                  | x,dialogs              |
+----------------------------+-------------------------------------------------------+------------------------+
| `DocumentAI`_              | Intelligent Document Processing wrapper               | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `DocumentAI.Base64AI`_     | Intelligent Document Processing service               | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `DocumentAI.Nanonets`_     | Intelligent Document Processing service               | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Email.Exchange`_          | E-Mail operations (Exchange protocol)                 | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Email.ImapSmtp`_          | E-Mail operations (IMAP & SMTP)                       | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Excel.Application`_       | Control the Excel desktop application                 | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Excel.Files`_             | Manipulate Excel files directly                       | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `FileSystem`_              | Read and manipulate files and paths                   | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `FTP`_                     | Interact with FTP servers                             | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `HTTP`_                    | Interact directly with web APIs                       | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Hubspot`_                 | Access HubSpot CRM data objects                       | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Images`_                  | Manipulate images                                     | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `JavaAccessBridge`_        | Control Java applications                             | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `JSON`_                    | Manipulate JSON objects                               | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `MFA`_                     | Authenticate using one-time passwords (OTP) & OAuth2  | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Notifier`_                | Notify messages using different services              | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Outlook.Application`_     | Control the Outlook desktop application               | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `PDF`_                     | Read and create PDF documents                         | x,pdf                  |
+----------------------------+-------------------------------------------------------+------------------------+
| `Robocorp.Process`_        | Use the Robocorp Process API                          | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Robocorp.WorkItems`_      | Use the Robocorp Work Items API                       | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Robocorp.Vault`_          | Use the Robocorp Secrets API                          | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Salesforce`_              | Salesforce operations                                 | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `SAP`_                     | Control SAP GUI desktop client                        | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Tables`_                  | Manipulate, sort, and filter tabular data             | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Tasks`_                   | Control task execution                                | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Twitter`_                 | Twitter API interface                                 | x                      |
+----------------------------+-------------------------------------------------------+------------------------+
| `Windows`_                 | Alternative library for Windows automation            | x,windows              |
+----------------------------+-------------------------------------------------------+------------------------+
| `Word.Application`_        | Control the Word desktop application                  | x                      |
+----------------------------+-------------------------------------------------------+------------------------+

.. _Archive: https://rpaframework.org/libraries/archive/
.. _Browser.Playwright: https://rpaframework.org/libraries/browser_playwright/
.. _Browser.Selenium: https://rpaframework.org/libraries/browser_selenium/
.. _Cloud.AWS: https://rpaframework.org/libraries/cloud_aws/
.. _Cloud.Azure: https://rpaframework.org/libraries/cloud_azure/
.. _Cloud.Google: https://rpaframework.org/libraries/cloud_google/
.. _Crypto: https://rpaframework.org/libraries/crypto/
.. _Database: https://rpaframework.org/libraries/database/
.. _Desktop: https://rpaframework.org/libraries/desktop/
.. _Desktop.Clipboard: https://rpaframework.org/libraries/desktop_clipboard/
.. _Desktop.Operatingsystem: https://rpaframework.org/libraries/desktop_operatingsystem/
.. _Dialogs: https://rpaframework.org/libraries/dialogs/
.. _DocumentAI: https://rpaframework.org/libraries/documentai
.. _DocumentAI.Base64AI: https://rpaframework.org/libraries/documentai_base64ai/
.. _DocumentAI.Nanonets: https://rpaframework.org/libraries/documentai_nanonets/
.. _Email.Exchange: https://rpaframework.org/libraries/email_exchange/
.. _Email.ImapSmtp: https://rpaframework.org/libraries/email_imapsmtp/
.. _Excel.Application: https://rpaframework.org/libraries/excel_application/
.. _Excel.Files: https://rpaframework.org/libraries/excel_files/
.. _FileSystem: https://rpaframework.org/libraries/filesystem/
.. _FTP: https://rpaframework.org/libraries/ftp/
.. _HTTP: https://rpaframework.org/libraries/http/
.. _Hubspot: https://rpaframework.org/libraries/hubspot/
.. _Images: https://rpaframework.org/libraries/images/
.. _JavaAccessBridge: https://rpaframework.org/libraries/javaaccessbridge/
.. _JSON: https://rpaframework.org/libraries/json/
.. _MFA: https://rpaframework.org/libraries/mfa/
.. _Notifier: https://rpaframework.org/libraries/notifier/
.. _Outlook.Application: https://rpaframework.org/libraries/outlook_application/
.. _PDF: https://rpaframework.org/libraries/pdf/
.. _Robocorp.Process: https://rpaframework.org/libraries/robocorp_process/
.. _Robocorp.WorkItems: https://rpaframework.org/libraries/robocorp_workitems/
.. _Robocorp.Vault: https://rpaframework.org/libraries/robocorp_vault/
.. _Salesforce: https://rpaframework.org/libraries/salesforce/
.. _SAP: https://rpaframework.org/libraries/sap/
.. _Tables: https://rpaframework.org/libraries/tables/
.. _Tasks: https://rpaframework.org/libraries/tasks/
.. _Twitter: https://rpaframework.org/libraries/twitter/
.. _Windows: https://rpaframework.org/libraries/windows/
.. _Word.Application: https://rpaframework.org/libraries/word_application/

Installation of RPA.Browser.Playwright
--------------------------------------

The **RPA.Browser.Playwright** at the moment requires special installation, because
of the package size and the post install step it needs to be fully installed.

Minimum required conda.yaml to install Playwright:

.. code-block:: yaml

   channels:
     - conda-forge
   dependencies:
     - python=3.9.13
     - pip=22.1.2
     - nodejs=16.4.2
     - pip:
       - robotframework-browser==13.3.0
       - rpaframework==20.1.2
   rccPostInstall:
     - rfbrowser init

Installation
------------

Learn about installing Python packages at `Installing Python Packages`_.

Default installation method with Robocorp `Developer Tools`_ using conda.yaml:

.. code-block:: yaml

   channels:
     - conda-forge
   dependencies:
     - python=3.9.13
     - pip=22.1.2
     - pip:
       - rpaframework==20.1.2

To install all extra packages (including Playwright dependencies), you can use:

.. code-block:: yaml

   channels:
     - conda-forge
   dependencies:
     - python=3.9.13
     - tesseract=4.1.1
     - pip=22.1.2
     - nodejs=16.14.2
     - pip:
       - robotframework-browser==13.3.0
       - rpaframework==20.1.2
       - rpaframework-aws==5.0.0
       - rpaframework-google==6.1.1
       - rpaframework-recognition==5.0.0
   rccPostInstall:
     - rfbrowser init

Separate installation of AWS, Dialogs, PDF and Windows libraries without main rpaframework:

.. code-block:: yaml

   channels:
     - conda-forge
   dependencies:
     - python=3.9.13
     - pip=22.1.2
     - pip:
       - rpaframework-aws==5.0.0 # included in the rpaframework as an extra
       - rpaframework-dialogs==4.0.0  # included in the rpaframework by default
       - rpaframework-pdf==5.0.0  # included in the rpaframework by default
       - rpaframework-windows==6.0.1 # included in the rpaframework by default


.. note:: Python 3.7 or higher is required

Example
-------

After installation the libraries can be directly imported inside
`Robot Framework`_:

.. code:: robotframework

    *** Settings ***
    Library    RPA.Browser.Selenium

    *** Tasks ***
    Login as user
        Open available browser    https://example.com
        Input text    id:user-name    ${USERNAME}
        Input text    id:password     ${PASSWORD}

The libraries are also available inside Python_:

.. code:: python

    from RPA.Browser.Selenium import Selenium

    lib = Selenium()

    lib.open_available_browser("https://example.com")
    lib.input_text("id:user-name", username)
    lib.input_text("id:password", password)

Support and contact
-------------------

- `rpaframework.org <https://rpaframework.org/>`_ for library documentation
- `Robocorp Documentation`_ for guides and tutorials
- **#rpaframework** channel in `Robot Framework Slack`_ if you
  have open questions or want to contribute
- `Robocorp Forum`_ for discussions about RPA
- Communicate with your fellow Software Robot Developers and Robocorp experts
  at `Robocorp Developers Slack`_

.. _Robot Framework Slack: https://robotframework-slack-invite.herokuapp.com/
.. _Robocorp Forum: https://forum.robocorp.com
.. _Robocorp Developers Slack: https://robocorp-developers.slack.com

Contributing
------------

Found a bug? Missing a critical feature? Interested in contributing?
Head over to the `Contribution guide <https://rpaframework.org/contributing/guide.html>`_
to see where to get started.

Development
-----------

Repository development is `Python`_ based and requires at minimum
Python version 3.7+ installed on the development machine. The default Python version used in the
Robocorp Robot template is 3.7.5 so it is a good choice for the version to install. Not recommended
versions are 3.7.6 and 3.8.1, because they have issues with some of the dependencies related to rpaframework.
At the time the newer Python versions starting from 3.9 are also not recommended, because some of
the dependencies might cause issues.

Repository development tooling is based on basically on `poetry`_ and `invoke`_. Poetry is the
underlying tool used for compiling, building and running the package. Invoke is used for scripting
purposes for example for linting, testing and publishing tasks.

First steps to start developing:

1. initial poetry configuration

.. code:: shell

   poetry config virtualenvs.path null
   poetry config virtualenvs.in-project true
   poetry config repositories.devpi "https://devpi.robocorp.cloud/ci/test"

2. git clone the repository
#. create a new Git branch or switch to correct branch or stay in master branch

   - some branch naming conventions **feature/name-of-feature**, **hotfix/name-of-the-issue**, **release/number-of-release**

#. ``poetry install`` which install package with its dependencies into the **.venv** directory of the package, for example **packages/main/.venv**
#. if testing against Robocorp Robot which is using **devdata/env.json**

   - set environment variables
   - or ``poetry build`` and use resulting .whl file (in the **dist/** directory) in the Robot **conda.yaml**
   - or ``poetry build`` and push resulting .whl file  (in the **dist/** directory) into a repository and use raw url
     to include it in the Robot **conda.yaml**
   - another possibility for Robocorp internal development is to use Robocorp **devpi** instance, by ``poetry publish --ci``
     and point **conda.yaml** to use rpaframework version in devpi

#. ``poetry run python -m robot <ROBOT_ARGS> <TARGET_ROBOT_FILE>``

   - common *ROBOT_ARGS* from Robocorp Robot template: ``--report NONE --outputdir output --logtitle "Task log"``

#. ``poetry run python <TARGET_PYTHON_FILE>``
#. ``invoke lint`` to make sure that code formatting is according to **rpaframework** repository guidelines.
   It is possible and likely that Github action will fail the if developer has not linted the code changes. Code
   formatting is based on `black`_ and `flake8`_ and those are run with the ``invoke lint``.
#. the library documentation can be created in the repository root (so called "meta" package level). The documentation is
   built by the docgen tools using the locally installed version of the project, local changes for the main package
   will be reflected each time you generate the docs, but if you want to see local changes for optional packages, you must
   utilize ``invoke install-local --package <package_name>`` using the appropriate package name (e.g., ``rpaframework-aws``). This
   will reinstall that package as a local editable version instead of from PyPI. Multiple such packages can be added by
   repeating the use of the ``--package`` option. In order to reset this, use ``invoke install --reset``.

   - ``poetry update`` and/or ``invoke install-local --package <package name>``
   - ``make docs``
   - open ``docs/build/html/index.html`` with the browser to view the changes or execute ``make local`` and navigate to
     ``localhost:8000`` to view docs as a live local webpage.

   .. code-block:: toml

      # Before
      [tool.poetry.dependencies]
      python = "^3.7"
      rpaframework = { path = "packages/main", extras = ["cv", "playwright", "aws"] }
      rpaframework-google = "^4.0.0"
      rpaframework-windows = "^4.0.0"

      # After
      [tool.poetry.dependencies]
      python = "^3.7"
      rpaframework = { path = "packages/main", extras = ["cv", "playwright"] }
      rpaframework-aws = { path = "packages/aws" }
      rpaframework-google = "^4.0.0"
      rpaframework-windows = "^4.0.0"

#. ``invoke test`` (this will run both Python unittests and robotframework tests defined in the packages **tests/ directory**)

   - to run specific Python test: ``poetry run pytest path/to/test.py::test_function``
   - to run specific Robotframework test: ``inv testrobot -r <robot_name> -t <task_name>``

#. git commit changes
#. git push changes to remote
#. create pull request from the branch describing changes included in the description
#. update **docs/source/releasenotes.rst** with changes (commit and push)

Packaging and publishing are done after changes have been merged into master branch.
All the following steps should be done within master branch.

#. git pull latest changes into master branch
#. in the package directory containing changes execute ``invoke lint`` and ``invoke test``
#. update **pyproject.toml** with new version according to semantic versioning
#. update **docs/source/releasenotes.rst** with changes
#. in the repository root (so called "meta" package level) run command ``poetry update``
#. git commit changed **poetry.lock** files (on meta and target package level), **releasenotes.rst**
   and **pyproject.toml** with message "PACKAGE. version x.y.z"
#. git push
#. ``invoke publish`` after Github action on master branch is all green

Some recommended tools for development

- `Visual Studio Code`_ as a code editor with following extensions:

   - `Robocorp Code`_
   - `Robot Framework Language Server`_
   - `GitLens`_
   - `Python extension`_

- `GitHub Desktop`_ will make version management less prone to errors

.. _poetry: https://python-poetry.org
.. _invoke: https://www.pyinvoke.org
.. _Visual Studio Code: https://code.visualstudio.com
.. _GitHub Desktop: https://desktop.github.com
.. _Robocorp Code: https://marketplace.visualstudio.com/items?itemName=robocorp.robocorp-code
.. _Robot Framework Language Server: https://marketplace.visualstudio.com/items?itemName=robocorp.robotframework-lsp
.. _GitLens: https://marketplace.visualstudio.com/items?itemName=eamodio.gitlens
.. _Python extension: https://marketplace.visualstudio.com/items?itemName=ms-python.python
.. _black: https://pypi.org/project/black/
.. _flake8: https://pypi.org/project/flake8/

License
-------

This project is open-source and licensed under the terms of the
`Apache License 2.0 <http://apache.org/licenses/LICENSE-2.0>`_.
