Release notes
=============

`Upcoming release <https://github.com/robocorp/rpaframework/projects/3#column-16713994>`_
+++++++++++++++++

- API retrying improvements affecting Work Items
- Library **RPA.Email.ImapSmtp**: Keyword ``Email To Document`` for converting HTML or
  Text e-mails into Word documents (:issue:`295`)

- Library **RPA.Robocorp.WorkItems**:

  - Removed Keyword ``Parse Work Item From Email``
  - Automatically loads e-mail body formats like JSON/YAML/Text/HTML into "parsedEmail"
    work item variable

`Released <https://pypi.org/project/rpaframework/#history>`_
+++++++++

11.6.3 - 15 Nov 2021
--------------------

- Library **RPA.Email.ImapSmtp**: Fix email fetch when uid is empty

11.6.2 - 13 Nov 2021
--------------------

- Library **RPA.Email.ImapSmtp**: Fix handling of application/octet-stream attachments

11.6.1 - 12 Nov 2021
--------------------

- Library **RPA.PDF**:

  - Fix non empty or junk XML dumping on PDF parsing (:issue:`287`)
  - Fixed by ``rpaframework-pdf`` **0.10.0** (included in this release)

- Library **RPA.Email.ImapSmtp**:

  - Fix sender name encoding when using ``Send Message`` keyword (:issue:`279`)
  - Fix filename encoding when using ``Save Attachment``/``Save Attachments`` keywords (:issue:`290`)

11.6.0 - 4 Nov 2021
-------------------

- Library **RPA.Robocorp.WorkItems**: Keyword ``Parse Work Item From Email`` for
  retrieving the input item dictionary payload from the sent e-mail JSON body which
  triggered the process (:issue:`275`)
- Library **RPA.Desktop.Windows**: Fix how keyword ``Screenshot`` handles filename when
  saving

11.5.2
------

- Library **RPA.JavaAccessBridge**: Raise the causing error (instead of just logging it)
  if initialization fails

11.5.1
------

- Library **RPA.Robocorp.WorkItems**: Keyword `For Each Input Work Item` supports now
  human-friendly parameter names as `items_limit` and `return_results`

11.5.0
------

- Library **RPA.Robocorp.WorkItems**:

  - Keyword `For Each Input Work Item` bugfixes and results collection switch
    (:issue:`250`)
  - Keyword `Release Input Work Item` allows exception passing with type, code and
    name (:pr:`256`)
  - Automatic API call retrying under Control Room for failed requests (:issue:`252`)
  - Default input item during local dev, docs and cloud requests hotfixes (:pr:`253`)

- Library **RPA.Outlook.Application**:

  - Changes related to (:issue:`248`)
  - Add new keyword `Get Emails`
  - Add new keyword `Mark Emails As Read`
  - Add new keyword `Move Emails`
  - Add new keyword `Save Email Attachments`
  - Renamed keyword `Send Email` (old keyword `Send Message` gives Deprecation warning)
  - Renamed keyword `Wait For Email`  (old keyword `Wait For Message` gives Deprecation warning)

- Add warning message if importing Windows platform dependtant library on non-Windows platform

  - **RPA.Desktop.Windows**
  - **RPA.Excel.Application**
  - **RPA.Outlook.Application**
  - **RPA.Word.Application**

- Library **RPA.Desktop.Windows**: Add possibility to bypass initial element lookup when
  using `Open Dialog` or `Connect By Handle` keywords

- Library **RPA.Email.ImapSmtp**: Keyword `List Messages` bugfix

11.4.0
------

- Library **RPA.Robocorp.WorkItems** support on iterating work items for both local
  development and in the cloud:

  - Add keyword `For Each Input Work Item` for applying a keyword over all input work
    items (:pr:`241`)

  - Add keywords `Get Current Work Item` and `Release Input Work Item` for releasing
    and setting the state of the currently processed input work item (:pr:`245`)

11.3.0
------

- Library **RPA.Robocorp.Vault**: Supports both .yaml/.json local vault secrets file formats (:issue:`225`)
- Library **RPA.PDF**: Add possibility to preserve whitespacing in PDF textboxes - :issue:`235`
- Library **RPA.Robocorp.WorkItems**: New environment variables for work items I/O
  during local dev ("RPA_INPUT_WORKITEM_PATH", "RPA_OUTPUT_WORKITEM_PATH" - :pr:`234`)
- Library **RPA.Email.ImapSmtp**:

  - Fix `Move Messages` issue (:issue:`237`)
  - Add keyword `Move Messages By IDs`
  - Fix boolean return values for keywords doing definite actions (like Mark As Read, Delete Messages..)

- Library **RPA.Email.Exchange**: Update `exchangelib` dependency to 4.5.1 and pin `tzlocal` dependency to 2.1

11.2.1
------

- Library **RPA.Robocorp.WorkItems**: Handle payloads with non-ascii characters
- Library **RPA.Dialogs**: Date ISO format for ``Add Date Input`` keyword
- Library **RPA.Desktop**: Always write unicode with ``Type text``

11.2.0
------

- Library **RPA.Dialogs**: ``Add Date Input`` keyword
- New library **RPA.Robocorp.Process**: Library support for Control Room Process API

11.1.3
------

- Library **RPA.Salesforce**:

  - Fix ``Salesforce Query`` result being limited to 250 objects
  - Add parameter to ``Salesforce Query`` to return result as ``Table``

11.1.2
------

- Library **RPA.Email.ImapSmtp**:

  - Remove newline and carriage return chars from attachment filenames
  - Fix problem with saving attachments which do not have payload

11.1.1
------

- Library **RPA.Robocorp.WorkItems**: Ensure file-based database has at least one item
- Library **RPA.Tables**: Fix reversed sort ordering
- Library **RPA.Windows**: Fix internal argument for ``Screenshot`` keyword
- Library **RPA.JSON**: Fix docstring examples

11.1.0
------

- Library **RPA.Email.ImapSmtp**:

  - Add support for IMAP literal search
  - Add support for Gmail advanced search

11.0.0
------

- Terminology fixes for Robocorp Control Room
- Renamed library **RPA.Robocloud.Items** to **RPA.Robocorp.WorkItems**:

  - Previous import works as before, with deprecation warning
  - Removed keywords ``Load work item`` and ``Load work item from environment``
  - Added keywords ``Get input work item`` and ``Create output work item``
  - Added support for variables and home directory in local database path
  - Changed local work items format

- Renamed library **RPA.Robocloud.Secrets** to **RPA.Robocorp.Vault**:

  - Previous import works as before, with deprecation warning
  - Added support for variables and home directory in local vault path

- Library **RPA.Email.ImapSmtp**:

  - Add `uid` into email dictionary
  - Fix email body decoding
  - Fix folder list problem when requesting non-existing folder

- Library **RPA.PDF**:

  - Handle missing document information
  - Always create output directory when writing to disk

- Library **RPA.Windows**: Fix exception from empty parent attribute
- Library **RPA.Images**:

  - Deprecate screenshot keywords, use ``rpaframework-recognition`` for template matching
  - Use the library **RPA.Desktop** for image-based automation going forward

10.9.3
------

- Library **RPA.Excel.Files**:

  - Return empty list when reading empty worksheet (:issue:`203`)
  - Correctly handle header names with non-string values

10.9.2
------

- Library **RPA.Email.ImapSmtp**:

  - Fix ``List Messages`` error not returning matching emails
  - Fix marking emails as SEEN when using ``List Messages`` or ``Wait For Message``
  - Add ``encoding`` library initialization parameter (default is ``utf-8`` as it used to be)
  - Add ``readonly`` parameter to keywords ``List Messages`` (True), ``Wait For Message`` (True) and ``Select Folder`` (False).
    Default values are in the parenthesis.

10.9.0
------

- Library **RPA.Desktop.Windows**: Add COMError protection to keyword ``Open From Search``
- Library **RPA.Email.ImapSmtp**: Fix possible `None` error when reading email body
- Library **RPA.Database**: Fix typo in ibm_db connection
- Library **RPA.JavaAccessBridge**:

  - Add new library init parameters: ``ignore_callbacks`` and ``access_bridge_path``
  - Bump java-access-bridge-wrapper version to 0.7.4

10.8.0
------

- Library **RPA.HTTP**:

  - Fix downloading of big files
  - Bump robotframework-requests version to 0.9.1

10.7.1
------

- Bump robotframework-pythonlibcore version to 3.0.0

10.6.0
------

- Library **RPA.Email.Exchange**: Add keyword ``Save Message`` to save message in EML format

10.5.0
------

- Library **RPA.JavaAccessBridge**: Bump ``java-access-bridge-wrapper`` to latest version
- Library **RPA.Database**: Add parameter ``autocommit`` to ``connect_to_database`` keyword (now only used with pymssql module)
- Library **RPA.Email.Exchange**: Fix ``List Messages`` when ``received_by`` is missing from the email

10.4.0
------

- New experimental library **RPA.JavaAccessBridge**

Library requirements:

- Windows only
- Java Access Bridge is enabled
- Environment variable pointing to the Access Bridge DLL file is set

See more details in library documentation.

Feedback is highly appreciated via Slack or Github issues!

- Library **RPA.Email.ImapSmtp**: Allow sending message with empty account and password

10.3.0
------

- Library **RPA.Database**: Return rows for ``SHOW`` and ``EXPLAIN`` statements
- Library **RPA.Desktop.Windows**: Add ``parent`` as possible locator

10.2.0
------

- Library **RPA.Excel.Application**:

  - Add keyword ``Export As PDF``
  - Add automatic document and application closing to prevent file being locked

- Library **RPA.FTP**: Add keyword parameters to support FTP over TLS/SSL (FTPS)
- Library **RPA.Desktop.Windows**: Add point of ``origin`` parameter to ``Drag and Drop``

rpaframework-google: 0.2.3
--------------------------

  - Fix authentication issue when using Robocorp Vault
  - Fix keyword ``Synthesize Speech``

10.1.0
------

- Library **RPA.Excel.Files**:

  - Add keyword ``Set cell format`` for adjusting cell number formatting
  - Add new keyword aliases ``Get cell value`` and ``Set cell value``
  - Improve keyword documentation

- Library **RPA.Excel.Application**: Add option to save in legacy formats
- Library **RPA.Desktop**: Fix issues with ``Press keys`` on Windows

10.0.7
------

- Library **RPA.Dialogs**: Print full traceback from errors when opening dialog
- Update optional ``numpy`` and ``opencv`` dependencies

10.0.6
------

- Library **RPA.Dialogs**:

  - Add unique name and icon for dialog window
  - Fix MacOS keyboard focus and dock icon issues

10.0.5
------

- Bump PyObjC versions from 6.x to 7.x,
  to fix possible API version errors with MacOS

10.0.4
------

- Library **RPA.Dialogs**:

  - Fix automatic height calculation on Windows
  - Fix element clearing if dialog throws exception
  - Fix errors in keyword examples

10.0.3
------

- Updated ``rpaframework-pdf`` dependency

10.0.2
------

- Fix ``use-robocorp-vault`` script error when creating ``devdata/env.json`` file

10.0.1
------

- Fix ``TypeError`` errors when creating Tables inside Robocorp Lab

10.0.0
------

- Library **RPA.Cloud.Google**:

  - Available now as ``rpaframework-google`` package instead of rpaframework extra
  - Added basic support for ``Gmail API``
  - Added keyword tags to identify keywords by service in the documentation
  - Fix regression bug with Sheets keyword ``Insert Values``

- Library **RPA.Dialogs**:

  - Open dialogs as native OS windows instead of new browser instances
  - Renamed multiple keywords and arguments, added type hints for all arguments
  - Visual upgrade to all components
  - Available separately as ``rpaframework-dialogs`` package, but still part of main release

- Library **RPA.Tables**:

  - Removed support for named rows, which caused confusion and had several shortcomings
  - Added automatic argument conversion for all keywords
  - Added examples for all keywords

9.6.0
-----

- Library **RPA.Email.ImapSmtp**:

  - Return file paths of saved attachments
  - Fix problem with non-ASCII attachment filenames

- Library **RPA.FileSystem**: Fix default argument handling (:issue:`170`)
- Library **RPA.Word.Application**: Add option to control opening documents in ReadOnly mode (:issue:`171`)

9.5.0
-----

- Library **RPA.Tables**:

  - Add ``encoding`` option for CSV reading and writing
  - Add ``not contains`` and ``not in`` operators for filtering

- Library **RPA.JSON**: Add indent option to ``Save JSON To File``
- Library **RPA.Excel.Files**: Add keyword ``Get worksheet value``
- Library **RPA.HTTP**: Allow string as ``verify`` parameter to give path to CA_BUNDLE

9.4.0
-----

- Library **RPA.PDF**: Add ``Set Convert Settings`` keyword to adjust document analysis settings from default values

9.3.4
-----

- Library **RPA.PDF**: Add orientation, rotate and format image properties for ``Add Files To PDF``
- Library **RPA.Cloud.Google**: Fix bug in create file properties and set initial mimetype correctly

9.3.3
-----

- Library **RPA.Cloud.Google**: Fix mimetype error with ``Drive Upload File``

9.3.2
-----

- Library **RPA.Email.Exchange**: Fix ``Empty Folder`` keyword

9.3.1
-----

- Library **RPA.Cloud.Google**: Add missing service account support for ``Drive`` and ``Apps Script``

9.3.0
-----

- Library **RPA.PDF**:

  - Add keywords ``Save Figure As Image`` and ``Save Figures As Images`` to save PDF Figure objects
  - Add keyword ``Add Files To PDF`` to combine images and/or a PDFs (or pages from PDF) to new PDF
  - Improved performance by setting pdfminer log level to INFO

- Library **RPA.Dialogs**:

  - Add new keyword ``Add Password Input``, see (:pr:`161`)
  - Logging from keyword ``Request Response`` is now suppressed in Robot Framework logs

Thank you https://github.com/antusystem for submitting the pull request!

9.2.1
-----

  - Library **Email.ImapSmtp**: Fix issue with saving attachments

9.2.0
-----

  - Add new script **use-robocorp-vault**, which helps to setup local development run to use Robocorp Vault

9.1.0
-----

- Library **RPA.PDF**:

  - Restore path create feature for keyword ``HTML To PDF``
  - Fix keyword annotation of ``Save PDF``, which caused unavailability of the keyword
  - Update changes to this library in release notes of  ``8.0.0``
  - Known issue about viewing PDF with form checkbox fields, see (:issue:`156`)

- Library **RPA.Cloud.Google**:

  - Add Sheets keyword ``Update Values``
  - Add Sheets keyword ``Copy Sheet``
  - Return responses from all Sheets keywords

9.0.0
-----

Update to **Robot Framework 4.0**.

Feature highlights:

- Native IF/ELSE syntax
- Ability to skip tasks dynamically
- Argument auto-conversion improvements
- Documentation generation improvements
- Removal of task criticality

To see the full list of changes see
`the official release notes <https://github.com/robotframework/robotframework/blob/master/doc/releasenotes/rf-4.0.rst>`_.


8.2.0
-----

- Library **RPA.Robocloud.Secrets**:

  - Add keyword ``Set Secret`` for updating stored secrets

8.1.0
-----

- Library **RPA.Email.Exchange**:

  - Add keyword ``List Unread Messages``
  - Add keyword ``Move Message``

8.0.1
-----

- Library **RPA.Browser.Selenium**: Fix webdriver creation on Windows

8.0.0
-----

- Library **RPA.Browser.Selenium**:

  - Keyword ``Open Available Browser`` has the default option 'AUTO' for
    arguments ``headless`` and ``download``. See keyword documentation
    for details.
  - Webdrivers for Chrome/Chromium and Firefox are automatically matched
    to the currently installed browser version.
  - Webdrivers which are still running on Python process exit are closed
    automatically to prevent hanging subprocesses. (:issue:`94`)
  - Webdrivers are stored in the user's home folder, to speed
    up browser start-up times between reboots.

- Library **RPA.PDF**:

  - Refactor library into a separate package. (:issue:`97`)
  - Rename keyword ``Add Image to PDF`` to ``Add Watermark Image to PDF``.
  - Rename ``Get Value From Anchor`` to ``Find Text``.
  - Rename ``Page Rotate`` to ``Rotate Page``.
  - Rename ``PDF Decrypt`` to ``Decrypt PDF``.
  - Rename ``PDF Encrypt`` to ``Encrypt PDF``.
  - Rename ``Update Field Values`` to ``Save Field Values``.
  - Rename ``Open PDF Document`` to ``Open PDF``.
  - Rename ``Close PDF Document`` to ``Close PDF``.
  - Unify keyword signatures, now keywords can be given an input and output paths.
    If no input path given, the library assumes a PDF is already opened by some
    other keyword. If no output path given, the library will output the file
    to ``output/output.pdf``.

- Library **RPA.Desktop.Windows**:

  - Keyword ``Open File`` return type changed from boolean to integer,
    to indicate the opened application ID
  - Add ``object`` key into ``Get Window List`` return data (allows advanced usage)
  - Change how field is emptied with ``Type Into`` parameter ``empty_field=True``

- Library **RPA.Tables**:

  - Add option to define column name for unknown CSV fields,
    and warn about header and data mismatch
  - Correctly handle source data with ``NoneType`` columns

- Library **RPA.Word.Application**: Fix saving with Office 2007 and older (:issue:`146`)

- Library **RPA.Cloud.AWS**:

  - Add keyword ``Convert Textract Response To Model``
  - Add ``model`` parameter to Keyword ``Analyze Document`` for getting modeled response object

- Library **RPA.Email.ImapSmtp**: Set attachment header correctly (:issue:`148`)

7.6.0
-----

- Library **RPA.Outlook.Application**: Fix ``ActiveDocument`` bug when closing Outlook
- Library **RPA.Email.ImapSmtp**: Convert non-literal values in ``List Messages`` response to strings
- Library **RPA.Desktop.Windows**: Add keyword ``Set Automation Speed``

7.5.0
-----

- Library **RPA.Email.Exchange**:

  - Fix sub folder bug with ``Move Messages``
  - Add keyword ``Save Attachments``
  - Add ``criterion`` parameter to ``List Messages`` for filtering
  - Add ``save_dir`` parameter to ``List Messages`` for saving attachments
  - Add more details into returned messages

- Library **RPA.Database**:

  - Fix bug with ``Call Stored Procedure``
  - Hide details of ``Connect To Database`` from Robot Framework logs

7.4.2
-----

- Library **RPA.Email.ImapSmtp**: Fix errors in server folder handling
- Library **RPA.Desktop**: Use correct default application when opening files on Windows
- Fix integer handling in ``Notebook Print`` core keyword

7.4.1
-----

- Library **RPA.Outlook.Application**: Fix HTML email body issue

7.4.0
-----

- Library **RPA.Browser.Selenium**:

  - Add parameter ``user_agent`` for keywords ``Open Available Browser`` and ``Open Chrome Browser``
  - Add keyword ``Execute CDP`` to execute Chrome DevTools Protocol commands

- Fix issues with Windows library imports on Python 3.9

7.3.0
-----

- Library **RPA.Desktop.Windows**:

  - ``Open File`` performs the ``Open Dialog`` call only if windowtitle is given
  - Expose ``timeout`` parameter for ``Open File`` keyword

- Library **RPA.Browser.Selenium**:

  - Keyword ``Open Available Browser`` now prints table of attempts to Notebooks on error

- Library **RPA.JSON**: Add optional default for fetching values

7.2.0
-----

- Library **RPA.Desktop.Windows**:

  - Add keyword ``Refresh Window`` to support element re-evaluation when UI changes
  - Improve ``Restore Dialog`` keyword
  - Add experimental support for combined locators like ``name:element1 and type:Button``
  - Add window title wildcard support for keywords starting applications and ``Open Dialog``
  - Fix ``Quit Application`` error when using process id to quit
  - Add ``focus`` parameter to ``Mouse Click`` keyword
  - Add ``legacy`` and ``object`` attributes to element dictionary
  - Fix ``Wait For Element`` error when asserting number of elements to wait
  - Fix ``Open File`` by adding parameters to control window it opens
  - Fix ``Connect By Handle`` parameter type to int

- Library **RPA.Desktop.OperatingSystem**: Add keyword ``Process ID Exists``
- Library **RPA.Browser.Selenium**:

  - Add keyword ``Print to PDF``
  - Increase headless Chrome window size

- Library **RPA.PDF**:

  - Add possibility to get textboxes (text and its coordinates) with keyword ``Get Text From PDF``
  - Add possibility to set anchor to point or area for keyword ``Get Value From Anchor``

7.1.1
-----

- Library **Desktop.Windows**:

  - Fix `Open Executable` error not taking control of the window
  - Address window resizing issue with `Open Dialog`

7.1.0
-----

- New library **Crypto** for common hashing and encryption operations
- Library **Cloud.Google**: Improve help and error messages for ``rpa-google-oauth`` tool
- Library **Desktop**: Handle locators with whitespace, allow using return values as arguments
- Library **Dialogs**: Throw error if user closes browser, add timeout to response
- Library **Excel.Application**:

  - Expose ``header`` argument in ``Create Worksheet``
  - Fix issues with worksheet access in keywords
  - Deprecate argument ``tabname`` in keyword ``Add new sheet``
  - Add more helpful error messages

- Library **FileSystem**: Add keyword for reading file owner
- Constrain version of ``comtypes`` dependency to fix issue with Windows DLLs

7.0.5
-----

- Fix issue with pip resolving incompatible chardet version

7.0.4
-----

- Library **Desktop.Windows**: Remove library destructor actions

7.0.3
-----

- Library **Desktop.Windows**: Fix possible COM exception when gathering elements from a window

7.0.2
-----

- Library **Cloud.Google**: Remove unnecessary log message

7.0.1
-----

- Library **Cloud.Google**: Fix how authentication scopes are initialized

7.0.0
-----

- Library **Desktop**:

  - Add initial version of OCR support
  - Add syntax for locator chaining
  - Add built-in buffer time between keyboard/mouse inputs
  - Add built-in wait period for all locators, instead of failing immediately
  - Add preview images for matched locators in Robot Framework log

- Library **Cloud.Google**:

  - Add support for Apps Script service
  - Add support for Drive service

- Library **Desktop.Windows**: Add more properties into dictionary returned by ``Get Window List``
- Library **Email.ImapSmtp**:

  - Add keyword ``Move Messages``
  - Add source folder parameter to ``List Messages``
  - Add limit to ``Delete Messages``
  - Add keywords to add/remove labels from GMail messages
  - Add keyword ``Do Message Actions`` for performing custom set of actions on selected messages

- **RPA.Browser** libraries

  - RPA.Browser.Playwright has been added, enabling use of playwright based robotframework-browser library
  - RPA.Browser was moved to RPA.Browser.Selenium, and the old import RPA.Browser is kept as deprecated alias for now

- Library **Tables**: Correctly handle empty fields when filtering

6.7.3
-----

- Fix issue with pip resolving incompatible chardet version

6.7.2
-----

- Add ``docutils`` as dependency to fix robotframework-lsp support

6.7.1
-----

- Library **Desktop**: Fix moving mouse to image template

6.7.0
-----

- Library **Excel.Files**:

  - Add keyword for inserting images to worksheets
  - Fix off-by-one issue with ``Find Empty Row`` return value

- Library **Desktop**:

  - Store screenshots in unique path by default, embed preview in logs
  - Resolve image templates correctly with different working directories

- Library **Excel.Application**:

  - Add keyword ``Find First Available Cell`` to return free cell
  - Keyword ``Open Workbook`` will set first worksheet active by default

- Library **PDF**: Fix error when parsing figures in the document
- Library **Database**: Add support for ``pymssql`` database module


6.6.0
-----

- Library **Tables**: Add various helper keywords:

  - ``Merge Tables`` for merging tables, with an optional shared key
  - ``Find Table Rows`` for finding rows with a specific column value
  - ``Set Row As Column Names`` for setting an existing row as header

- Library **Browser**: Add keyword ``Highlight Elements`` for highlighting elements that match a selector
- Library **RPA.Desktop**: Fix macOS coordinate scaling when using image template locators
- Remove dependency to ``python-evdev`` on Linux

6.5.0
-----

- Library **Excel.Application**: Fix for `finding first available row <https://github.com/robocorp/rpaframework/issues/72>`_.
- Add missing variables for Robot Framework library scope and documentation format
- Add more verbose library docstrings in general

6.4.0
-----

- Library **Browser**: Add ``Set Download Directory`` keyword
- Library **Cloud.AWS**: Add keywords for Textract asynchronous operations regarding
  document analysis and text detection
- Library **Dialogs**: Default value support for input text element (pull request #70)
- Library **Desktop.Windows**: ``Mouse Click`` keyword supports now also element dictionary
  as target locator

6.3.1
-----

- Library **Desktop.Windows**: Add parameter to ``Get Element`` to prevent
  opening dialog

6.3.0
-----

- Library **Desktop**: Image template confidence changed to logarithmic scale
- Library **HTTP**: Directory support for download target
- Reduce logging in keyboard emulation keywords, e.g. ``Send Keys``, to prevent
  accidentally logging sensitive information

6.2.0
-----

- Library **Desktop.Windows**: Add timeout parameter for keywords ``Open From Search``
  and ``Open Using Run Dialog``

6.1.0
-----

- New library **JSON** for manipulating JSON objects

6.0.2
-----

- Library **Desktop**:

  - Library scope changed to global
  - Obey default image locator confidence

6.0.1
-----

- Library **Desktop**: Fix case handling with default locator

6.0.0
-----

- Library **FileSystem**: Replace ``force`` arguments with ``missing_ok`` to match python API
- Library **Desktop**: Initial release of new cross-platform desktop automation library
- Library **Dialogs**: Add library initialization arguments to change server port and form stylesheet
- Library **Robocloud.Items**: Remove invalid assert on file overwrite
- Library **Browser**:

  - Add new option to allow missing elements with status keywords such as ``Is Element Visible``
  - Set Chrome argument ``disable-dev-shm-usage`` by default in all environments


5.3.3
-----

- Library **Images**: Fix duplicate region matches, timeout option
- Library **Robocloud.Items**: Allow saving files with FileAdapter

5.3.2
-----

- Library **Robocloud.Items**: Fix relative path inputs,
  always return absolute paths.

5.3.1
-----

- Library **Robocloud.Items**: Fix accessing unsaved files from items
- Library **Tables**: Fix creating empty table with predefined columns
- Library **Database**: Fix ``Query`` keyword bug when SELECT result is empty

5.3.0
-----

- Library **Robocloud.Items**: Support for files in work items
- Library **Dialogs**: Type hinting and documentation updates
- Library **Images**: Raise error when timeout has been reached

5.2.0
-----

- New library **Dialogs** which allows getting input from the user
  via HTML forms


5.1.0
-----

- Library **Browser**: Add keyword ``Get Browser Capabilities``
- Library **Cloud.Google**: Add Google Sheets service support

5.0.0
-----

- Library **Database**:

  - Drop dependency robotframework-databaselibrary
  - Some of the old keywords do not exist anymore and some new keywords
    have been added (*NOTE. backwards compatibility breaking change*)

- Library **PDF**: Keywords ``Template HTML To PDF`` and ``HTML To PDF`` will now
  create directory structure and overwrite existing file by default.

- Library **Images**: Remove ``Save Format`` option from ``Take Screenshot``
  and ``Crop Image`` keywords. Change screenshotting library from ``pyscreenshot``
  to ``mss``.

4.2.0
-----

- Library **Browser**:

  - Add keywords ``Does Alert Contain`` and ``Does Alert Not Contain``
  - Fix ``Screenshot`` to explicitly call ``Notebook Image`` to insert
    images into notebook when that is available

- Library **Robocloud.Items**: Allow NoneType as default for variables

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
