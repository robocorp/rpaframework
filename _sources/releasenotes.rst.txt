Release notes
=============

Upcoming release
----------------

- **Browser**: Upgrade ``SeleniumTestability`` plugin to 1.1.0 version
- **Browser**: Remove "..controlled by automated.." infobar by default when using Chrome
- **Email.ImapSmtp**: Add keywords for folder management and marking messages
  as read/unread and flag/unflag
- **Email.Exchange**: Add keywords for folder management
- Core functionality separated into ``rpaframework-core`` package

1.4.0
-----

- **Robocloud.Items**: Add keywords for listing and deleting variables
- **Windows**: Add keyword ``Get Window List``
- **Windows**: Fix keywords ``Connect By PID`` and ``Connect By Handle``

1.3.0
-----

- New features for **Browser** library

  - Set headless mode with environment variable ``RPA_HEADLESS_MODE=1``
  - New boolean returning keywords like ``Is Element Visible`` and ``Does Page Contain``
  - New keyword ``Get Element Status`` to get 4 different element states in a dictionary
  - Added plugin ``SeleniumTestability`` which can be enabled
    with ``Library  RPA.Browser  use_testability``
  - In total 40 new keywords

- **OperatingSystem**: Improve error messages on keywords restricted to specific
  operating systems

1.2.1
-----

- Cloud libraries: Fix ``use_robocloud_vault`` to support also ``FileSecrets``

1.2.0
-----

- Add support for Robocloud Vault for the following libraries:

  - **Cloud.AWS**
  - **Cloud.Azure**
  - **Cloud.Google**

- **Images**: Automatically convert points/regions from strings
- **Outlook.Application**: Add keyword ``Wait For Message``

1.1.0
-----

- New **Tasks** library, which allows using flow control between tasks
- New **Cloud.Azure** library, which supports following Azure APIs:

  - ``Text Analytics``
  - ``Face``
  - ``Computer Vision``
  - ``Speech``

- **Cloud.AWS**: Fix parameters and return options for keywords
  ``Detect Document Text`` and ``Analyze Document``

1.0.4
-----

- **Excel.Files**: Add keyword for setting cell values
- **Excel.Files**: Mitigate compatibility issues with file extensions

1.0.3
-----

- **Excel.Files**: Fixed double close issue with workbooks
- **Excel.Files**: Ignoring columns with empty header
- **Tables**: Improved handling of non-string columns

1.0.2
-----

- **msoffice**: Fix. Call `close document` only on Word documents
- **Browser**: Fix Geckodriver downloading version based on Chrome version

Thank you https://github.com/mdp for providing fix for the **msoffice**

1.0.1
-----

- **Tables**: Added keywords ``Get table slice`` and ``Rename table columns``
- **Excel.Files**: Fixed various issues with appending data to empty worksheet
- **Outlook**: Fix attachment handling

1.0.0
-----

- **MAJOR** change. Package has been renamed to ``rpaframework``. The old PyPI package
  will continue to work for a while (not receiving updates anymore), but it will be removed
  before official GA launch in the beginning of July.

0.11.0
------

- **Cloud.Google**: Added as optional package, needs to be installed
  with ``pip install rpa-framework[google]``

  Support for services:

    - ``Google Cloud Natural Language``
    - ``Google Cloud Speech to Text``
    - ``Google Cloud Storage``
    - ``Google Cloud Text to Speech``
    - ``Google Cloud Translation``
    - ``Google Cloud Video Intelligence``
    - ``Google Cloud Vision``

- **Excel.Files**: Minor documentation update

0.10.1
------

- **Email.Exchange**: Fix parameter handling for kw ``send_message``

0.10.0
------

- **Email.Exchange**: Add support for ``HTML`` content, ``attachments``, and inline ``images``
- **Email.ImapSmtp**: Allow sending inline images - parameter ``images`` for kw ``Send Message``
- **HTTP**: Return response of ``Download`` keyword (including content)
- **Cloud.AWS**: Due to ``boto3`` dependency size, library requires ``pip install rpa-framework[aws]`` to use

0.9.3
-----

- New library: **Cloud.AWS**, supporting following services:

  - ``Comprehend``
  - ``S3``
  - ``SQS``
  - ``Textract``

- **Tables**: Add keyword ``Get table dimensions``, allow setting arbitrary cell value
- New library: **Twitter**

0.9.2
-----

- Updated Robot Framework to 3.2.1

0.9.1
-----

- **Email.ImapStmp**: Fix attachment handling for kw ``Send Message``
- **Excel.Application**: Add keyword ``Run Macro``
- **PDF**: Add keywords:

  - ``Parse PDF``
  - ``Get input fields``
  - ``Update field values``
  - ``Set field value``
  - ``Set anchor to element``
  - ``Get value from anchor``
  - ``Add image to PDF``
  - ``Save PDF``
  - ``Dump PDF as XML``

0.9.0
-----

- **Tables**:

  - **Note**: This change is backwards incompatible
  - Removed limitation of column names being valid Python identifiers
  - Default iteration method changed to dictionaries instead of namedtuples
  - Keywords that return rows or columns now harmonized to return them in
    dictionary format by default, with option to use lists
  - Table head/tail keywords changed to return new Table instance
  - Added keyword for trimming extra whitespace from column names

- **Excel.Files**: Trim column names in addition to rows

0.8.7
-----

- **OperatingSystem**: psutils dependency marked as Windows only because
  it has wheel files only for Windows

0.8.6
-----

- **HTTP**:

  - Add keyword ``Download``
  - Add ``overwrite`` option to ``HTTP Get``

- **FileSystem**:

  - Fix string interpolation in error messages
  - Add ``force`` option for file removal keywords
  - Add ``overwrite`` option for file create keywords

- **Tables**: Add keyword ``Trim empty rows``
- **Excel.Files**:

  - Add keyword ``Read worksheet as table``
  - Auto-convert integer values in .xls worksheets

0.8.5
-----

- **PDF**: Add ``Encrypt PDF`` and ``Add Pages To Source PDF`` keywords.
- **Windows**: Add aliases for element locators,
  for better Robocode Lab compatibility
- **HTTP**: Add keyword ``HTTP Get``
- **Tables**: Fix missing cell values for sanitized columns

0.8.4
-----

- Fix: **PDF** ``Template HTML to PDF`` keyword

0.8.3
-----

- Fix: **Windows** ``drag_and_drop`` keyword
- New library: **Netsuite**
- **PDF**: add new keywords

0.8.2
-----

- **Windows**: Add keyword for clicking image templates
- **Windows**: Add keyword for drag and drop

0.8.1
-----

- **Browser**: Fix ``Open Available Browser`` kw parameter bug

0.8.0
-----

- New library: **Salesforce**
- New library: **Database**

0.7.5
-----

- **Email.ImapSmtp**: Separate how IMAP and SMTP are handled in the library
- **Windows**: Improve documentation for keys
- **Browser**: Manage webdrivermanager download error

0.7.4
-----

- **Browser**: Restructure how driver downloads and logging are handled

0.7.3
-----

- **Browser**: Detect Chrome and chromedriver versions. Download driver if they differ
- **Images**: Don't template match same region multiple times
- **Tables**:

  - Added new keywords: ``Set table row``, ``Set table column``, ``Set table cell``
  - Renamed keyword ``Get cell value`` to ``Get table cell``

0.7.2
-----

- **Browser**: Store webdrivers in temporary directory

0.7.1
-----
First public release of RPA Framework
