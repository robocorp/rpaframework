RPA Framework
=============

.. contents:: Table of Contents
   :local:
   :depth: 1

.. include-marker

Introduction
------------

`RPA Framework` is a collection of open-source libraries and tools for
Robotic Process Automation (RPA), and it is designed to be used with both
`Robot Framework`_ and Python_. The goal is to offer well-documented and
actively maintained core libraries for Software Robot Developers.

Learn more about RPA at Robohub_.

**The project is:**

- 100% Open Source
- Sponsored by Robocorp_
- Optimized for Robocloud_ and Robocode_
- Accepting external contributions

.. _Robot Framework: https://robotframework.org
.. _Robot Framework Foundation: https://robotframework.org/foundation/
.. _Python: https://python.org
.. _Robohub: https://hub.robocorp.com
.. _Robocorp: https://robocorp.com
.. _Robocloud: https://hub.robocorp.com/introduction/robocorp-suite/robocloud/
.. _Robocode: https://hub.robocorp.com/introduction/robocorp-suite/robocode-lab/

Links
^^^^^

- Homepage: `<https://www.github.com/robocorp/rpa-framework/>`_
- Documentation: `<https://rpaframework.org/>`_
- PyPI: `<https://pypi.org/project/rpa-framework/>`_

------------

.. image:: https://github.com/robocorp/rpa-framework/workflows/main/badge.svg
   :target: https://github.com/robocorp/rpa-framework/actions?query=workflow%3Amain
   :alt: Status

.. image:: https://img.shields.io/pypi/v/rpa-framework.svg?label=version
   :target: https://pypi.python.org/pypi/rpa-framework
   :alt: Latest version

.. image:: https://img.shields.io/pypi/l/rpa-framework.svg
   :target: http://www.apache.org/licenses/LICENSE-2.0.html
   :alt: License

.. note::
   RPA Framework is in Early Access phase and expected 1.0
   release will happen during summer 2020.

Libraries
---------

The RPA Framework project currently includes the following libraries:

+------------------------+-------------------------------------------+
| `Tables`_              | Manipulate, sort, and filter tabular data |
+------------------------+-------------------------------------------+
| `FileSystem`_          | Read and manipulate files and paths       |
+------------------------+-------------------------------------------+
| `Browser`_             | Control browsers and automate the web     |
+------------------------+-------------------------------------------+
| `HTTP`_                | Interact directly with web APIs           |
+------------------------+-------------------------------------------+
| `PDF`_                 | Read and create PDF documents             |
+------------------------+-------------------------------------------+
| `Slack`_               | Send notifications to Slack channels      |
+------------------------+-------------------------------------------+
| `Excel.Files`_         | Manipulate Excel files directly           |
+------------------------+-------------------------------------------+
| `Excel.Application`_   | Control the Excel desktop application     |
+------------------------+-------------------------------------------+
| `Word.Application`_    | Control the Word desktop application      |
+------------------------+-------------------------------------------+
| `Outlook.Application`_ | Control the Outlook desktop application   |
+------------------------+-------------------------------------------+
| `Email.Exchange`_      | E-Mail operations (Exchange protocol)     |
+------------------------+-------------------------------------------+
| `Email.ImapSmtp`_      | E-Mail operations (IMAP & SMTP)           |
+------------------------+-------------------------------------------+
| `Desktop.Windows`_     | Automate Windows desktop applications     |
+------------------------+-------------------------------------------+
| `Desktop.Clipboard`_   | Interact with the system clipboard        |
+------------------------+-------------------------------------------+
| `Robocloud.Items`_     | Use the Robocloud Work Items API          |
+------------------------+-------------------------------------------+
| `Robocloud.Secrets`_   | Use the Robocloud Secrets API             |
+------------------------+-------------------------------------------+

.. _Tables: https://rpaframework.org/libraries/tables/
.. _FileSystem: https://rpaframework.org/libraries/filesystem/
.. _Browser: https://rpaframework.org/libraries/browser/
.. _HTTP: https://rpaframework.org/libraries/http/
.. _PDF: https://rpaframework.org/libraries/pdf/
.. _Slack: https://rpaframework.org/libraries/slack/
.. _Excel.Files: https://rpaframework.org/libraries/excel_files/
.. _Excel.Application: https://rpaframework.org/libraries/excel_application/
.. _Word.Application: https://rpaframework.org/libraries/word_application/
.. _Outlook.Application: https://rpaframework.org/libraries/outlook_application/
.. _Email.Exchange: https://rpaframework.org/libraries/email_exchange/
.. _Email.ImapSmtp: https://rpaframework.org/libraries/email_imapsmtp/
.. _Desktop.Windows: https://rpaframework.org/libraries/desktop_windows/
.. _Desktop.Clipboard: https://rpaframework.org/libraries/desktop_clipboard/
.. _Robocloud.Items: https://rpaframework.org/libraries/robocloud_items/
.. _Robocloud.Secrets: https://rpaframework.org/libraries/robocloud_secrets/

Installation
------------

If you already have Python_ and `pip <http://pip-installer.org>`_ installed,
you can use:

``pip install rpa-framework``

.. note:: Python 3.6 or higher is required

Example
-------

After installation the libraries can be directly imported inside
`Robot Framework`_:

.. code:: robotframework

    *** Settings ***
    Library    RPA.Browser

    *** Tasks ***
    Login as user
        Open browser  https://example.com
        Input text    id:user-name    ${USERNAME}
        Input text    id:password     ${PASSWORD}

The libraries are also available inside Python_:

.. code:: python

    from RPA.Browser import Browser

    lib = Browser()

    lib.open_browser("https://example.com")
    lib.input_text("id:user-name", username)
    lib.input_text("id:password", password)

Support and contact
-------------------

- `rpaframework.org <https://rpaframework.org/>`_ for library documentation
- Robohub_ for guides and tutorials
- **#rpa-framework** channel in `Robot Framework Slack`_ if you
  have open questions or want to contribute

.. _Robot Framework Slack: https://robotframework-slack-invite.herokuapp.com/

Contributing
------------

Found a bug? Missing a critical feature? Interested in contributing?
Head over to the `Contribution guide <https://rpaframework.org/contributing/guide/>`_
to see where to get started.

License
-------

This project is open-source and licensed under the terms of the
`Apache License 2.0 <http://apache.org/licenses/LICENSE-2.0>`_.
