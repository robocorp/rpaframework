Release notes
=============

Upcoming release
----------------

- Library **Browser**:

  - Add keywords ``Does Alert Contain`` and ``Does Alert Not Contain``
  - Fix ``Screenshot`` to explicitly  call ``Notebook Image`` to insert
    images into notebook when that is available

4.1.0
-----

- Library **Browser**: Add keyword ``Open User Browser`` which opens URL
  with user's default browser. Allows using browser's existing cache. To
  control this browser see keyword ``Attach Chrome Browser`` or use
  ``Desktop.Windows`` library to control the browser

4.0.0
-----

- Library **Browser**: Change keyword ``Screenshot`` to embed Base64 image
  string into log and save same Base 64 string to a file as png image
  (*NOTE. backwards compatibility breaking change*)
- Library **Desktop.Windows**:

  - Fix Windows backend handling to be consistent within a library
  - New keyword ``Set Windows Backend``

3.0.0
-----

- Upgrade ``Robot Framework`` to 3.2.2
- Upgrade ``pyscreenshot`` to 2.2
- Library **Email.ImapSmtp**:

  - Add keyword examples (documentation)
  - Change ``List Messages`` to return list of dictionaries containing
    message attributes. In addition there is attribute `Has-Attachments`
    for each message (*NOTE. backwards compatibility breaking change*)
  - Add keyword ``Save Attachment`` which can be used save attachments
    from a message. Can be used when looping through messages received
    by ``List Messages``

- Library **Desktop.Windows**:

  - Add keyword examples (documentation)
  - Add keyword ``Get Text``. Returns dictionary of possible values
    due to many implementation methods
  - Add parameter `empty_field` to keyword ``Type Into`` which will
    empty field before typing into a field
  - Add keyword ``Wait For Element`` which will search for element with timeout
  - Add more information about started app instances into application list

- Library **Desktop.OperatingSystem**:

  - Add keyword examples (documentation)
  - Add keyword ``Kill Process By PID`` to terminate process using its
    identifier

- Library **Browser**:

  - Add keyword examples (documentation)
  - Add `proxy` parameter for keywords ``Open Available Browser``
    and ``Open Chrome Browser``. Works only for Chrome at the moment

2.7.0
-----

- **Desktop.Windows**: Fix window dialog handling in ``Open Executable`` keyword
- New **Archive** library for ZIP and TAR operations
- **core.notebook**: Add parameter `count` to control row output from keyword ``Notebook Table``

2.6.0
-----

- **Browser**: Do not `EMBED` screenshots when in notebook run mode
- **Excel.Application**: Add keyword ``Read From Cells``
- **RobotLogListener**: Add keyword ``Mute Run On Failure`` to mute
  SeleniumLibrary's ``run_on_failure`` behaviour
- **Email.ImapSmtp**: Fix filetype issue when adding attachments to emails
- **Tables** and **Excel.Files**: Move table trimming actions from `Excel.Files`
  library to `Tables` library. Added parameter ``trim`` to `Tables` keyword
  ``Create Table`` which is by default `False`
- **PDF**: Fix input field setting and saving to PDF

2.5.1
-----

- **Browser**: Fix missing default argument

2.5.0
-----

- **Browser**:

  - Attempt fallback browser if webdriver unpacking fails
  - Attempt to use webdriver from PATH
  - Add option to define Chrome profile path and name
  - Add option to define Chrome profile preferences
  - Add keyword to attach to existing Chrome instance
  - Add keyword for waiting and clicking elements
  - Disable Chrome's password manager prompts

- **Robocloud.Items**: Allow empty list (or otherwise falsy value) as raw payload
- **Desktop.Windows**:

  - Add keyword ``Type Into``
  - Remove confusing placeholder keyword(s)

- **Excel/Word/Outlook.Application**: Use early binding to ensure constants exist
- **Tables**: Fix issues with invalid internal method calls
- **Email.ImapSmtp**:

  - Use given IMAP port
  - Fix confusing error message if TLS not supported

2.4.0
-----

- **Browser**: Add alias support for ``Open Available Browser``
- **Browser**: Fix indexing issues with multiple ``chromedriver`` instances
- **Browser**: Reduce superfluous logging from keywords
- **Robocloud.Items**: Add keywords for reading and writing full payloads

2.3.0
-----

- New **FTP** library, which interacts with FTP servers
- Use **RPA.core.notebook* library to output data into Jupyter Notebook
  (in Robocode Lab especially). Support added to keywords in the following
  libraries: **Browser**, **FTP**, **HTTP**, **Images**, **PDF**, **Twitter**,
  **Tables** and **Robocloud.Items**
- **Browser** sets default screenshot directory to EMBED which means that when
  using keywords ``Capture Page Screenshot`` or ``Capture Element Screenshot``
  without `filename` argument the image is embedded into `log.html` as Base64 image

2.2.0
-----

- **Robocloud.Secrets**: Add support for Robocloud end-to-end encryption
- **FileSystem**: Add ``exist_ok`` argument for ``Create directory`` keyword
- **Tasks**: Fix support for FAIL status in schema actions
- **Tasks**: Allow inlining execution graph in log (enabled by default)
- **Excel.Files**: Always fallback to legacy mode on error
- **Tables**: Fix manual override for CSV dialect, document arguments
- **Desktop.Windows**: Attach to windows more reliably, and show helpful message on error

2.1.0
-----

- **FileSystem**: Fix keyword ``Normalize Path`` to match built-in library,
  and add new keyword ``Absolute Path`` for previous functionality.
- **PDF**: Fix keyword ``Template HTML To PDF`` to handle HTML content from
  non-English Chrome browser.
- **PDF**: Add keyword ``HTML To PDF`` which takes HTML content as string parameter.
- **Email.Exchange**: Fix ``Authorize`` when autodiscover is set to False. Add missing parameters
  to keyword.
- New **Notifier** library, which allows using notification services like Slack, Gmail, Pushover etc.

2.0.1
-----

- **Browser**: Fix for regression in Chrome's Webdriver version handling
- **Email.ImapSmtp**: Fix how IMAP server is initialized
- Fix for issue with missing files when upgrading from version 1.x

2.0.0
-----

**NOTE:** Changes to **Email.ImapSmtp** and **Email.Exchange** are
backwards compatibility breaking changes.

- **Browser**: Added support for locator aliases
- **Browser**: Upgrade ``SeleniumTestability`` plugin to 1.1.0 version
- **Browser**: Remove "..controlled by automated.." infobar by default when using Chrome
- **Email.ImapSmtp** library initialization parameter `port` split to `smtp_port` and
  `imap_port` (*breaks backwards compatibility*)
- **Email.ImapSmtp**: Add keywords for folder management and marking messages
  as read/unread and flag/unflag
- **Email.Exchange** library keyword ``list_messages`` parameter order changed -
  new order `folder_name`, `count` (*breaks backwards compatibility*)
- **Email.Exchange**: Add keywords for folder management
- **Email.Exchange**: Add keywords ``Wait For Message`` and ``Move Messages``
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
