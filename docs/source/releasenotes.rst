Release notes
=============


Latest versions
+++++++++++++++

.. include:: packages.rst
   :start-after: include-packages


`Upcoming release <https://github.com/robocorp/rpaframework/projects/3#column-16713994>`_
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

- Enables system certificate store usage with ``truststore`` automatic injection.
  Minimum versions for this to happen are Python **3.10.12** and ``pip`` **23.2.1**.
  (:issue:`1083`)
- Library **RPA.Browser.Selenium** (:pr:`1084`; ``rpaframework-core`` **11.1.0**):

  - Fixes webdriver caching when attempting previously downloaded executable reuse and
    latest release version retrieval optimization.
  - Use Robocorp controlled secure sources for querying and downloading webdrivers.
    Base URL to whitelist (:issue:`1080`) -- set `RPA_EXTERNAL_WEBDRIVERS` to any value
    if you want to default to the previously used external sources:
    https://downloads.robocorp.com/ext/webdrivers/
  - Ability to take into use a 64bit webdriver version for IE on a 64bit Windows system
    by setting `RPA_ALLOW_64BIT_IE` to any value. (by default the 32bit version is used
    as that's the recommendation provided by Selenium)


`Released <https://pypi.org/project/rpaframework/#history>`_
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

26.1.1 - 07 Sep 2023
--------------------

- Library **RPA.JavaAccessBridge** (:pr:`1087`): Fix problem with
  ``Select Window By Title`` keyword, which caused all but full title match to fail
  to select window successfully.

04 Sep 2023
-----------

- Library **RPA.Cloud.Google** (:pr:`1082`; ``rpaframework-google`` **8.0.0**):

  - Add new keywords for Google Sheets

    - ``Copy spreadsheet``
    - ``Create spreadsheet``
    - ``Delete sheet``
    - ``Generic spreadsheet batch update``
    - ``Get all sheet values``
    - ``Get spreadsheet basic information``
    - ``Get spreadsheet details``
    - ``Rename sheet``
    - ``To column letter``

  - Repurposed keywords

    - ``Copy sheet`` (now will copy a sheet within a spreadsheet)
    - ``Create sheet`` (now will create a sheet within a spreadsheet)

  .. warning::
    **Breaking** changes in the ``Sheets`` keywords. All actions/properties
    related to a whole spreadsheet will use `spreadsheet` name and `sheet` will
    be used to indicate a single sheet in a spreadsheet. This is to be consistent
    with Google API naming.

24 Aug 2023
-----------

- Library **RPA.Cloud.Google** (``rpaframework-google`` **7.1.2**):

  - Fix how OAuth token is updated into Control Room Vault.

- Library **RPA.Cloud.Google** (:pr:`1057`; ``rpaframework-google`` **7.1.1**):

  - Fix mimetype handling in overall and for Excel documents in ``Send Message``
    keyword. (:issue:`994`)
  - Improve token handling in authentication flow.

26.1.0 - 24 Aug 2023
--------------------

- General update on *all* packages (:pr:`950`):

  - All packages will be taking into use the latest `robotframework`
    version (**6.1.1**).
  - The minimum Python version is set to **3.8**.

  - All new package versions are listed below.

    - ``rpaframework-assistant`` **3.0.0** (additional release note included below)
    - ``rpaframework-aws`` **5.3.0**
    - ``rpaframework-google`` **7.1.0**
    - ``rpaframework-openai`` **1.3.0**
    - ``rpaframework-pdf`` **7.2.0**
    - ``rpaframework-recognition`` **5.2.0**
    - ``rpaframework-windows`` **7.4.0**

  - Library **RPA.Assistant** (:pr:`1068`; ``rpaframework-assistant`` **3.0.0**):

    - Fix ``Add Date Input`` validation and return value as `Date` object instead of
      a string.
    - Add Python examples for every keyword.

26.0.3 - 24 Aug 2023
--------------------

- Library **RPA.Browser.Selenium**: Properly show webdriver errors in case the initial
  default is not found in PATH.

26.0.2 - 24 Aug 2023
--------------------

- Library **RPA.Browser.Selenium** (:pr:`1069`): Use an already existing webdriver
  found in PATH if present. Only if such a default expected executable isn't found, a
  newly cached one will be downloaded and used. (affects all supported browsers)

26.0.1 - 22 Aug 2023
--------------------

- Library **RPA.Browser.Selenium** (:issue:`1059`): Fix webdriver management and
  automation issues related to Edge in IE mode. Updated Portal example:
  https://robocorp.com/portal/robot/robocorp/example-ie-mode-edge

26.0.0 - 18 Aug 2023
--------------------

- Library **RPA.Browser.Selenium** (:pr:`1058`):

  - Fixed `options` passing with Firefox. (when a binary location is specified)

- General improvements to **RPA.*.Application** libraries (:issue:`1055`):

  - *All*: Better error handling (COM -> runtime), improved generic docs and
    troubleshooting guiding, fixed document closing (if was closed already) and app
    open/quit management, improved warnings and logging, file paths are tested for
    existence when operating on documents and raise errors in their absence.

  - **Excel**:

    - Removed deprecated parameter `tabname` from ``Add New Sheet``. (use `sheetname`)
    - ``Save Excel As`` raises when there's no workbook open. (use ``Open Workbook``
      first)

  - **Outlook**:

    - Removed deprecated keywords: ``Send Message`` (use ``Send Email``) and
      ``Wait For Message`` (use ``Wait For Email``).

  .. warning::
    **Breaking** changes in the **Application** libraries listed above.

25.0.1 - 11 Aug 2023
--------------------

- Library **RPA.DocumentAI.Base64AI** (:issue:`719`):

  - Fix signature matching API.
  - Better documentation and errors.

- Library **RPA.PDF** (:pr:`1051`; ``rpaframework-pdf`` **7.1.6**):

  - Make the `reader` parameter optional in the ``Save PDF`` keyword.
  - Fix PDF fields retrieval, value decoding and setting. (:issue:`872`)

25.0.0 - 10 Aug 2023
--------------------

- Library **RPA.Salesforce** (:pr:`1003`): Add keywords
  ``Auth with connected app`` and ``Execute APEX``.
- Library **RPA.Email.ImapSmtp** (:pr:`1054`): Fix handling of `To`, `Cc` and `Bcc`
  fields in `Send Message` keyword.

24.1.2 - 27 Jul 2023
--------------------

- Library **RPA.Robocorp.Storage** (``robocorp-storage`` **0.3.2**): Fix bug when
  retrieving assets containing spaces in their names.

24.1.1 - 26 Jul 2023
--------------------

- Library **RPA.Browser.Selenium** (:pr:`1035`; ``rpaframework-core`` **11.0.5**):
  Fix `chromedriver` download issues with Chrome **115** and over.

24.1.0 - 25 Jul 2023
--------------------

- Library **RPA.Browser.Selenium** (:pr:`1021`; ``rpaframework-core`` **11.0.4**):

  - Correctly handles and downloads a valid existing webdriver version when there's a
    need for one.
  - Ability to provide a default browser binary location with the
    `RPA_SELENIUM_BINARY_LOCATION` environment variable. (useful when the webdriver
    isn't able to automatically detect and start your system browser)
  - Portal example taking these into use:
    https://robocorp.com/portal/robot/robocorp/example-google-image-search

- Library **RPA.Browser.Playwright**: Renders documentation for
  ``robotframework-browser==17.1.0``.

24.0.0 - 18 Jul 2023
--------------------

- Library **RPA.Robocorp.Storage**: Takes into use ``robocorp-storage`` **0.3.1** and
  replaces the limited generic keywords with the ones below. (:pr:`1016`)

  - ``Set Bytes Asset`` & ``Get Bytes Asset``
  - ``Set Text Asset`` & ``Get Text Asset``
  - ``Set JSON Asset`` & ``Get JSON Asset``
  - ``Set File Asset`` & ``Get File Asset``

  .. warning::
    **Breaking** changes: Old ``Set Asset`` & ``Get Asset`` keywords are gone, please
    replace them with one of the pairs above.

23.5.2 - 29 Jun 2023
--------------------

- Library **RPA.Robocorp.Storage**: Add support for using Assets in VSCode

23.5.1 - 28 Jun 2023
--------------------

- Library **RPA.JavaAccessBridge**:

  - Update and pin ``java-access-bridge-wrapper`` to version ``0.14.1``

23.5.0 - 27 Jun 2023
--------------------

- Library **RPA.JavaAccessBridge**:

  - Update ``java-access-bridge-wrapper`` to version ``0.13.0``
  - Add keyword ``Print Locator Tree``

23.4.0 - 22 Jun 2023
--------------------

- Add new library **RPA.Robocorp.Storage** for managing assets within *Asset Storage*
  in Control Room. (:issue:`957`)

09 Jun 2023
-----------

- Library **RPA.Assistant** 2.3.0:

  - Add new elements with ``Add Loading Spinner`` and ``Add Loading Bar``.

23.3.0 - 09 Jun 2023
--------------------

- Library **RPA.MSGraph** (:pr:`980`):

  - Lock ``O365`` dependency to a version less than ``2.0.27`` for compatibility
    with Python 3.7.

- Security update: Bumps ``cryptography`` to version ``41.0.1``. (:issue:`979`)

- Library **RPA.JavaAccessBridge**:

  - Update ``java-access-bridge-wrapper`` to version ``0.12.0``

23.2.1 - 02 Jun 2023
--------------------

- Library **RPA.JavaAccessBridge** (:pr:`978`):

  - Fix element search issue with ``Click Element`` keyword
  - Add new keyword ``Wait Until Element Exists``

23.2.0 - 02 Jun 2023
--------------------

- Library **RPA.Browser.*** (:pr:`974`):

  - **Selenium**:

    - Fix bug with detecting the right web-driver version for download on systems
      having Chromium installed instead of Chrome. (:issue:`949`)
    - Add support for operating on shadow DOMs within the ``Get WebElement`` keyword.
      (:issue:`941`)

  - **Playwright**:

    - Upgrade version and documentation to the latest `robotframework-browser`
      **16.2.0**. (:issue:`942`)
    - Automatic `headless` detection when running on systems without UI, including our
      Cloud Worker (Linux container). (:issue:`166`)

01 Jun 2023
-----------

- Library **RPA.OpenAI** 1.2.0 (:pr:`973`):

  - Add support for AzureAI and update ``openai`` to ``0.27.7``.

23.1.0 - 19 May 2023
--------------------

- Library **RPA.Browser.Selenium** (:pr:`943`):

  - New keyword ``Click Element When Clickable`` which tries to overcome errors like
    "Other element would receive the click". (:issue:`884`)
  - New keyword ``Set Element Attribute`` which sets an attribute value to an element
    retrievable with ``Get Element Attribute``. (:issue:`762`)
  - Setting a custom download directory is now supported by all Chromium-based browsers
    and Firefox. Use ``Set Download Directory`` before opening any browser instance in
    order to set such a custom path. (this should be working now in both headful and
    headless modes; :issue:`882`)
  - Custom user profiles (and common configuration) can be used with all Chromium-based
    browsers, like Chrome, Edge. (:issue:`865`)
  - Improved main library documentation, accepting both `WebElement` and `str` as
    locator types under our keywords as well. (:issue:`940`, :issue:`939`)

12 May 2023
-----------

- Library **RPA.Assistant** 2.2.2:

  - Documentation example fix, correct name of argument to ``maximum_rows``.

23.0.0 - 05 May 2023
--------------------

- Library **RPA.Database** (:pr:`944`):

  - Improvements for keyword ``Call Stored Procedure``

    - Fix keyword not returning results of the procedure
    - Add possibility of returning result as a ``RPA.Tables.Table`` by parameter ``as_table=True``
      (default is `True`, ie. `Table` is returned)
    - Add possibility of returning multiple resultsets from a ``Call Stored Procedure``
      by parameter ``multiple=True`` (default is `False`, ie. only one resultset is returned)
      Multiple results are then either list of lists or list of Tables.
    - Remove specific support for Python 2.* in this keyword

- Library **RPA.Email.Exchange** (:pr:`948`):

  - Add new keyword ``Send Reply Message``
  - Add parameter `items_only` for keyword ``List Messages`` which returns internal Email
    objects (mainly for advanced usage)

- Library **RPA.Email.ImapSmtp**:

  - Add keyword ``Convert EML file into message`` which reads EML message and returns
    headers, attachments and body (in text and HTML) format. (:pr:`948`)
  - Add parameters `in_reply_to` and `return_path` to keyword ``Send Message``. (:pr:`948`)
  - Make the `recipients` optional. It is still mandatory to give one of the following
    parameters `recipients`, `cc` or `bcc`. (:pr:`930`)

- Library **RPA.FTP** (:pr:`938`): Add socket support for TLS connections.

- Library **RPA.JavaAccessBridge** (:pr:`947`):

  - Add new keyword ``List Java Windows``
  - Add new keyword ``Select Window By PID``
  - Add new keyword ``Select Window By Title``
  - Keyword ``Select Window`` is deprecated in favor of the 2 ``Select..`` keywords mentioned
    above. Direct replacement for this keyword is ``Select Window By Title``. This keyword
    will be removed during next major release involving ``RPA.JavaAccessBridge`` library.

- Update library documentation to contain information about `autoexit` init parameter

  - **RPA.Excel.Application**
  - **RPA.Outlook.Application**

- Library **RPA.Word.Application** (:pr:`945`): Add `autoexit` init parameter (on default `True` as it is for
  similar libraries). This is a breaking change.

04 May 2023
-----------

- Library **RPA.Cloud.Google** (``rpaframework-google`` **7.0.3**; :pr:`935`): Fix move drive file

22.5.3 - 02 May 2023
--------------------

- Security update: Bumps ``cryptography`` to version **40**. (fixes the limitation of
  not being able to use the latest ``rpaframework-pdf`` in some scenarios;
  :issue:`926`)

22.5.2 - 13 Apr 2023
--------------------

- Library **RPA.Browser.Selenium** (:pr:`916`):

  - Takes into use the latest Selenium (**4.8.3** at the time of the release) and its
    logging fixes. (:issue:`883`)
  - Fixes scheme ensuring bug during not provided URLs. (:issue:`586`)
  - Fixes `headless` mode setting with newer browsers and enables more browser features
    when running in this mode. (:issue:`919`)
  - Ensures keyword ``Screenshot`` works and logs messages as expected. (logs aren't
    polluted with raw image data on levels equal or greater than `INFO` and it returns
    the final output image path; :issue:`920`)
  - Takes into use the latest webdriver-manager fixes given ``rpaframework-core``
    **11.0.1**.

22.5.1 - 07 Apr 2023
--------------------

- Library **RPA.Windows** (``rpaframework-windows`` **7.3.2**; :issue:`913`):

  - Keywords ``[Double|Right|Middle ]Click`` will raise `ActionNotPossible` if the
    element is not visible during clicking. (thus clicking wouldn't happen at all)
  - Main library and various keywords documentation fixes.

- Library **RPA.PDF** (``rpaframework-pdf`` **7.1.5**) (:pr:`914`): Fix "TypeError:
  cannot pickle 'dict_keys' object" bug with the ``HTML To PDF`` keyword.

  .. note::
    This ``rpaframework`` version requires at least the following library versions (if
    you have such dependencies already listed in your *conda.yaml*), although we
    recommend upgrading to the latest found in `PyPI <https://pypi.org/>`_:

      - ``rpaframework-assistant`` **2.2.1**
      - ``rpaframework-aws`` **5.2.8**
      - ``rpaframework-dialogs`` **4.0.4** (deprecated)
      - ``rpaframework-google`` **7.0.2**
      - ``rpaframework-pdf`` **7.1.4**
      - ``rpaframework-recognition`` **5.1.2**
      - ``rpaframework-windows`` **7.3.0**

22.5.0 - 05 Apr 2023
--------------------

- Library **RPA.Windows** (``rpaframework-windows`` **7.3.0**; :pr:`912`):

  - Our Windows elements recorder (`windows-recorder`) supports `path:` strategy
    display when run with verbosity on. (``-v`` flag)
  - Keyword ``Print Tree`` now displays the `path:` strategy locator alongside printed
    controls and flattened-by-level returned elements.
  - Keyword ``Set Value`` supports value validation customization through the
    `validator` parameter.

04 Apr 2023
-----------

- Library **RPA.Assistant** 2.2.0:

  - Add ``minimum_rows`` and ``maximum_rows`` arguments to ``Add Text Input``.
  - Add ability to specify validation functions as Robot Framework keywords.
  - Improve how validation errors are displayed. They display besides the input field
    now, instead of bottom of the dialog.
  - Fix checkbox values being returned as strings ``true`` and ``false`` instead of
    booleans.

22.4.0 - 29 Mar 2023
--------------------

- Library **RPA.Excel.Files**

  - Make method ``require_open_xlsx_workbook`` that was accidentally exposed
    a private method.

- Library **RPA.JavaAccessBridge** (:pr:`908`):

  - Fixes related to keyword ``Select Window``

    - Update to the latest ``java-access-bridge-wrapper`` 0.9.7
    - Add additional system window verification before using ``jab.switch_window_by_title``

- Library **RPA.Database** (:pr:`899`):

  - Add support for parameterized sql queries

- Library **RPA.PDF** (``rpaframework-pdf`` **7.1.3**) (:pr:`909`): Add documentation about PDF merge and split.

22.3.0 - 22 Mar 2023
--------------------

- New library **RPA.Smartsheet** (:pr:`880`):

  - Supports getting, creating and updating Smartsheet sheets, as well as downloading
    attachments.
  - Read library documentation for a full list of keywords.

22.2.3 - 15 Mar 2023
--------------------

- Library **RPA.PDF** (``rpaframework-pdf`` **7.1.2**): Light documentation fix and
  preserved default behaviour with the `boxes_flow` parameter in the
  ``Set Convert Settings`` keyword. (defaults to `0.5`)

14 Mar 2023
-----------

- Library **RPA.Assistant** 2.1.2:

  - Fix file picker sometimes causing ``AssertionError: Control must be added to the
    page first.`` error.
  - Fix ``Add Next Ui Button`` getting a normal `dict` and not a `dotdict` as its first
    argument.

22.2.2 - 13 Mar 2023
--------------------

- Library **RPA.Browser.Selenium** (:pr:`859`):

  - Fixes ``Set Download Directory`` keyword: functionality, docs, examples.
  - Improves Browser Locators functionality. (referenced by `alias:`)

22.2.1 - 09 Mar 2023
--------------------

- Library **RPA.Calendar**: Documentation fixes in various keywords.

22.2.0 - 09 Mar 2023
--------------------

- New library **RPA.Calendar** (:pr:`694`):

  - Supports holiday and business day related calculations.
  - Read library documentation for a full list of keywords.

- Library **RPA.Database**:

  - Changes how `psycopg2` module handles the ``Call Stored Procedure`` keyword.
  - Sets on the `autocommit` parameter use with ``Connect To Database`` keyword when
    using `psycopg2` module.
  - Removes **INFO** level logs from ``Connect To Database`` keyword. (privacy)

- Library **RPA.Outlook.Application** (:pr:`878`):

  - Adds possibility to set **CC** and **BCC** recipients with ``Send Email`` and
    ``Send Message`` keywords.

08 Mar 2023
-----------

- Library **RPA.Assistant** (``rpaframework-assistant`` **2.1.0**):

  - Features:

    - Add ``Set Title`` keyword. Can be used to set title of assistant when it is
      running.
    - Add ``Open Row`` and ``Close Row`` keywords. Used to layout elements into rows.
    - Add ``Open Column`` and ``Close Column`` keywords. Used to layout elements into
      columns.
    - Add ``Open Navbar`` and ``Close Navbar`` keywords. Can be used to create an
      always visible top bar for a dialog.
    - Add ``Open Stack`` and ``Close Stack`` keywords. Can be used to position elements
      manually.
    - Add ``Open Container`` and ``Close Container`` keywords. Useful for styling or
      placing single elements.
    - Add ``Add Flet Icon`` that enables adding any icons from flets large gallery of
      icons.

        - Compared to ``Add Icon``, it is more difficult to use but supports a much
          larger amount of icons.

    - Bugfixes:

        - Fix regression, Assistant flet app not closing properly when run from CLI and
          when the close button is pressed.
        - The library no longer silently misses adding to the result when an input
          ``name`` duplicate name is used, instead it raises a `ValueError`.

22.1.1 - 06 Mar 2023
--------------------

- Library **RPA.Windows** (``rpaframework-windows`` **7.2.1**; :pr:`869`):
  Documentation fixes in keywords: ``Set Value``, ``Print Tree``,
  ``Set Mouse Movement``.

22.1.0 - 06 Mar 2023
--------------------

- Library **RPA.Windows** (``rpaframework-windows`` **7.2.0**; :pr:`855`):

  - Enhances keyword ``Set Value`` with additional checks and a `send_keys_fallback`
    parameter as an alternate way of setting in the provided value. (if the main one
    fails; :issue:`483`)
  - Improves keyword ``Print Tree`` with clearer printed depths and children positions
    in the element tree. The returned element structure now encapsulates a usable path
    based locator in every element. (:issue:`796`)
  - Adds new keyword: ``Set Mouse Movement`` which enables/disables mouse movement
    simulation when interacting with elements. (e.g. clicking combo-boxes;
    :issue:`791`)
  - Miscellaneous: better recording instructions, documentation updates, bugfixes.
    (:issue:`591`, :issue:`797`)

22.0.1 - 03 Mar 2023
--------------------

- Added PyYAML 6.0 support, rpaframework can now install together with tools like
  `langchain`.

02 Mar 2023
-----------

**RPA.OpenAI** (``rpaframework-openai`` **1.1.1**):

  - Fix keyword ``Chat Completion Create`` not working as documented.

**RPA.OpenAI** (``rpaframework-openai`` **1.1.0**; :pr:`867`):

  - New keyword ``Chat Completion Create`` can be used to build up discussion with
    ChatGPT.

**RPA.Assistant** (``rpaframework-assistant`` **2.0.0**):

  - Added `location` argument to ``Add Button`` keyword.
  - Added `round` argument to ``Add Slider`` keyword.
  - Internal refactoring.
  - Update underlying UI library to ``flet`` **0.2.2** -> **0.4.2**, granting various
    bugfixes and improvements.
  - Depend on ``rpaframework-core`` **10.4.1** due to Flet dependency incompatibilities
    with earlier versions.

  .. warning::
    **Breaking** changes:

    - ``Run Dialog`` and ``Ask User`` parameter `clear` was removed, clearing is now
      mandatory.
    - (affects Python side users only): Location enum that ``run_dialog`` and
      ``ask_user`` accepts was changed from `Location` to `WindowLocation` to improve
      clarity.
    - By default `Slider` now rounds to 1 decimal.

28 Feb 2023
-----------

Library **RPA.PDF** (``rpaframework-pdf`` **7.1.0**):

  - Add possibility to change `boxes_flow` setting of PDF conversion with the
    ``Set Convert Settings`` keyword. The `boxes_flow` defines how text boxes within
    the PDF page are ordered. Read more about this in the keyword documentation.

22 Feb 2023
-----------

**RPA.Assistant** (``rpaframework-assistant`` **1.2.4**):

  - Reduce unnecessary debug logging from Flet that didn't obey the log level.

21 Feb 2023
-----------

**RPA.Assistant** (``rpaframework-assistant`` **1.2.3**):

  - Fix `results.key` access not working as documented.

22.0.0 - 20 Feb 2023
--------------------

.. warning::
  **Breaking** change release.

- The ``rpaframework-dialogs`` package is no longer part of the ``rpaframework``
  package. Reason for this change is the deprecation of the **RPA.Dialogs** library as
  we are recommending the **RPA.Assistant** library for building attended Robots.

  This means that **RPA.Dialogs** library can be still used, but it needs to be
  separately added into the **pip** section of the *conda.yaml* file
  (``rpaframework-dialogs==4.0.2``).

  The **RPA.Assistant** library also requires separate package installation of
  ``rpaframework-assistant==1.2.1``.

  We see that unattended robots are a majority of the process run cases and thus it
  makes sense to move libraries meant for the attended robots into separate packages.
  Added benefit is that will reduce the package size for the ``rpaframework`` package.

  Please read `the migration guide <https://github.com/robocorp/rpaframework/blob/master/packages/assistant/docs/Migration-Guide.md>`_
  on how to move from **RPA.Dialogs** to **RPA.Assistant**.

Other changes included in the release:

- Library **RPA.Windows** (``rpaframework-windows`` **7.1.0**; :pr:`840`):

  - Add support for the `path:` strategy in locators. (index-based element tree search)
  - Enhance ``Print Tree`` keyword with better element tree logging and the ability to
    return such structure.

- Library **RPA.Tables** (:issue:`821`): Allow custom dialects in csv files.

- Library **RPA.Robocorp.Process** (:issue:`845`): Host of the Process API should use
  the host from an environment variable (`RC_API_PROCESS_HOST`) if that is available.

- Script **use-robocorp-vault** maximum token validity time has been lowered to 20
  hours.

20 Feb 2023
-----------

- Library **RPA.Assistant**:

  - **1.2.2**

    - Fix package on Python 3.7.

  - **1.2.1**

    - Fix ``Add Slider`` `default` parameter misbehave if no user input was done on
      it.

17 Feb 2023
-----------

- Library **RPA.Assistant** (``rpaframework-assistant`` **1.2.0**):

    - Add `default` argument to ``Add Slider`` keyword to set a default for the slider.

- Library **RPA.Assistant** (:issue:`838`, :issue:`828`; ``rpaframework-assistant``
  **1.1.0**):

    - Bugfixes for dialog clearing.
    - New ``Add Slider`` keyword to create sliders for numeric inputs.
    - New `default` and `required` arguments for ``Add Text Input``.
    - Removing `None` values from the results so it makes value checking easier.

21.1.1 - 15 Feb 2023
--------------------

- Security upgrade of ``cryptography`` dependency to **39.0.1**. (:pr:`833`)

21.1.0 - 09 Feb 2023
--------------------

- Library **RPA.DocumentAI.Base64AI** (:issue:`803`): Support for signature matching on
  image documents with the following newly added keywords:

  - ``Get Matching Signatures``: Detects and returns signatures and their similarity.
  - ``Filter Matching Signatures``: Keeps relevant and alike signatures only.
  - ``Get Signature Image``: Saves signature's image for manual inspection.

  Portal example: https://github.com/robocorp/example-signature-match-assistant

- Global fix with retrieving the output directory path.

08 Feb 2023
-----------

- **OpenAI** (:pr:`792`) comes to **RPA Framework**! New library **RPA.OpenAI** adds
  four keywords covering GPT-3 text completions and DALL.E image creation.

  - ``Authorize To Openai:`` Authorize with OpenAI using your API key.
  - ``Completion Create``: Keyword for creating text completions in GPT-3 API using
    your prompt and various arguments.
  - ``Image Create``: Create one or more images based on a text prompt.
  - ``Image Create Variation``: Creating one or more variations of an existing image.

  .. note::
    **RPA.OpenAI** is not included in the core ``rpaframework`` package, so please add
    ``rpaframework-openai==1.0.1`` as a **pip** dependency in your **conda.yaml**.

- ``rpaframework-assistant`` **1.0.0**

    - New **RPA.Assistant** library! Provides better development experience for various
      use cases where previously **RPA.Dialogs** would have been used.
        - **RPA.Dialogs** users: `the new Migration Guide <https://github.com/robocorp/rpaframework/blob/master/packages/assistant/docs/Migration-Guide.md>`_
        - Does not use webview. Should improve compatibility and reduce broken installs.
        - Added mechanism to make buttons execute Python functions or Robot keywords.
        Enables building of code executing interactive assistants.
        - New ``Ask User`` keyword for building simple dialogs with less boilerplate.

- ``rpaframework-assistant`` **1.0.1**

    - macOS force stop bugfix

- ``rpaframework-assistant`` **1.0.2**, **1.0.3**, **1.0.4**

    - documentation building fixes and documentation updates

21.0.1 - 03 Feb 2023
--------------------

- Library **RPA.Windows** (``rpaframework-windows`` **7.0.3**): Fix Windows element(s)
  retrieval. (and dependent keywords)

21.0.0 - 01 Feb 2023
--------------------

.. warning::
  Multiple **breaking** changes below!

- Library **RPA.Cloud.Azure** (:issue:`635`):

  - `robocloud_vault_name` -> `robocorp_vault_name`
  - `use_robocloud_vault` -> `use_robocorp_vault`
  - ``Set Robocloud Vault`` -> ``Set Robocorp Vault``

- Library **RPA.Cloud.Google** (:pr:`794`; ``rpaframework-google`` **7.0.0**):

  - ``RPA.Robocloud.Secrets`` -> ``RPA.Robocorp.Vault``

- Library **RPA.PDF** (:issue:`785`; ``rpaframework-pdf`` **7.0.1**):

  - Keyword ``Find Text``:

    - Supports additional parameter `ignore_case`, which if set to `True`, will make
      the search case insensitive. (switch it **on** if you experience a different
      behaviour)
    - Adds `subtext:` strategy in the passed `locator` which checks for a substring
      instead of the whole text to match.

  - New related Portal example for parsing PDF invoices:
    https://github.com/robocorp/example-parse-pdf-invoice

20.1.2 - 26 Jan 2023
--------------------

- Library **RPA.Browser.Selenium** (:pr:`787`): Improved browser order resolution given
  the set env var and running OS.

20.1.1 - 26 Jan 2023
--------------------

- Library **RPA.Browser.Selenium** (:issue:`781`): Ability to change the default
  search order of browsers, when using the ``Open Available Browser`` keyword, through
  the `RPA_SELENIUM_BROWSER_ORDER` env var.

20.1.0 - 19 Jan 2023
--------------------

- Library **RPA.Browser.Selenium** (:issue:`745`): Ability to run Edge in IE
  compatibility mode. (robot example: https://github.com/robocorp/example-ie-mode-edge)
- Library **RPA.SAP**: Fix error in dependency import order in the underlying
  `SapGuiLibrary`.

20.0.2 - 10 Jan 2023
--------------------

- Security dependency fix given the bump of ``cryptography`` package to version **38**.
  (:pr:`773`)

20.0.1 - 10 Jan 2023
--------------------

- Fix docs given the dropped support for extras under library dependencies. (:pr:`772`)

20.0.0 - 09 Jan 2023
--------------------

- Global package & sub-library updates adding security and documentation fixes.
  (:pr:`767`)
- Other affected sub-libraries:

  - ``rpaframework-aws`` **5.2.5** (no API change, just dev & docs 3rd-party package
    upgrades)
  - ``rpaframework-google`` **6.1.5** (no API change, just dev & docs 3rd-party package
    upgrades)
  - ``rpaframework-pdf`` **6.0.1** (no API change, but behaviour may be different)
  - ``rpaframework-windows`` **7.0.2** (no API change, but locators recording may act
    differently)

.. warning::
  This is a **breaking** change!

  - We don't support *optional* packages anymore. Migrate your *conda.yaml* if needed:

    - ``rpaframework[aws]`` -> ``rpaframework-aws==5.2.4``
    - ``rpaframework[cv]`` -> ``rpaframework-recognition==5.0.1``
    - ``rpaframework[playwright]`` -> ``robotframework-browser==14.4.1``
    - And of course, don't forget about ``rpaframework==20.0.0``.

  - **RPA.Desktop** keywords related to mouse and keyboard may behave differently due
    to their ``pynput`` dependency recent upgrade.
  - Extra dependencies are pinned to the following minimum versions:

    - ``requests = "^2.28.1"``
    - ``oauthlib = "^3.2.2"``
    - ``requests-oauthlib = "^1.3.1"``

  - Misleading keyword ``On Token Refresh`` was removed from the **RPA.Email.Exchange**
    library. (wasn't meant to be a keyword at all)

19.4.2 - 21 Dec 2022
--------------------

- Library **RPA.Hubspot** (:issue:`740`): Deprecate keyword ``Auth With API Key`` in
  favor to ``Auth With Token``. (read how to generate one with
  `Private Apps <https://developers.hubspot.com/docs/api/private-apps>`_)

19.4.1 - 09 Dec 2022
--------------------

- Library **RPA.Email.Exchange** (:issue:`736`): Fix token auto-refresh for
  single-tenant Client apps.

19.4.0 - 08 Dec 2022
--------------------

- Added native OAuth2 support (:pr:`706`) with the following keywords:

  - ``Generate OAuth URL``
  - ``Get OAuth Token``
  - ``Refresh OAuth Token``

  Available in libraries:

    - **RPA.Email.Exchange** (:issue:`604`)
    - **RPA.Email.ImapSmtp** (additional keyword ``Generate OAuth String``)
    - **RPA.MFA** (:issue:`658`)

  Check the updated OAuth2 E-mail sending Portal example on: https://robocorp.com/portal/robot/robocorp/example-oauth-email

19.3.1 - 29 Nov 2022
--------------------

- Library **RPA.Browser.Selenium** (:issue:`710`): Fix bug with `auto_close=${False}`
  param when importing the library, which still had the browser closed at the end of
  the session. (now it's left open if such parameter is set to `False`)

19.3.0 - 28 Nov 2022
--------------------

- Library **RPA.Slack** (:issue:`711`): New keyword ``Slack Raw Message`` adds support for
  ``blocks`` message property by allowing user to set message dictionary.
- Library **RPA.Excel.Files** (:pr:`712`): Add new keywords for the library.

  List of new `RPA.Excel.Files` keywords:

  - Set Cell Formula
  - Copy Cell Values
  - Delete Columns
  - Delete Rows
  - Insert Rows Before
  - Insert Rows After
  - Insert Columns After
  - Insert Columns Before
  - Move Range
  - Clear Cell Range
  - Set Styles
  - Auto Size Columns
  - Hide Columns
  - Show Columns
  - Set Cell Values

19.2.0 - 17 Nov 2022
--------------------

- Library **RPA.Windows** (:pr:`693`):

  - Keyword ``Get Elements`` supports now parameter `siblings_only` which filters for
    elements found on the same level with the first match. This is ON by default; set
    it to `False` for a global search, which retrieves all the found elements matching
    the criteria instead.
  - Keyword ``Get Value`` returns `None` when there's no value to retrieve at all.
  - Fix sibling element searching in keyword ``Get Elements`` when there's no
    comparison strategy identified.

19.1.2 - 17 Nov 2022
--------------------

- Library **RPA.Robocorp.WorkItems** (:pr:`692`): Allow `email` input Work Item
  variable in the absence of the Control Room controlled one during e-mail triggering.

19.1.1 - 04 Nov 2022
--------------------

- Library **RPA.Outlook.RPA** (:pr:`687`): Fix ``pywintypesXX.dll`` errors.

19.1.0 - 03 Nov 2022
--------------------

- Library **RPA.Cloud.AWS** (:issue:`683`): Fix S3 ``List Files`` empty list response.
  Released in ``rpaframework-aws`` version ``5.2.1``.
- Library **RPA.HTTP** (:pr:`685`): Add keyword ``Check Vulnerabilities`` which will now just
  check for ``OpenSSL`` vulnerable versions.

  Related article: https://robocorp.com/docs/faq/openssl-cve-2022-11-01

19.0.0 - 27 Oct 2022
--------------------

- New Intelligent Document Processing library **RPA.DocumentAI**, which is a convenient
  wrapper over the existing libraries (:issue:`557`):

  - **RPA.Cloud.Google** (needs ``rpaframework-google`` installed)
  - **RPA.DocumentAI.Base64AI** (moved from ``RPA.Base64AI``)
  - **RPA.DocumentAI.Nanonets** (moved from ``RPA.Nanonets``)

  Provides the following generic keywords capable of working with all the engines
  above:

  - ``Init Engine``
  - ``Switch Engine``
  - ``Predict``
  - ``Get Result``

  Portal example: https://robocorp.com/portal/robot/robocorp/example-document-ai

.. warning::
  This is a **breaking** change! Two `DocumentAI` related libraries have moved, thus
  the importing location is changed now:

  - ``RPA.Base64AI`` -> ``RPA.DocumentAI.Base64AI``
  - ``RPA.Nanonets`` -> ``RPA.DocumentAI.Nanonets``

18.0.0 - 17 Oct 2022
--------------------

- Library **RPA.MSGraph** (:issue:`669`): Fix bugs in listing SharePoint files and in
  keywords not supporting Drive objects. Replace parameter ``drive_id`` with ``drive``
  throughout library, this is a **breaking** change for this library.

17.7.0 - 14 Oct 2022
--------------------

- Library **RPA.Outlook.Application** (:pr:`666`): Add parameter ``save_as_draft`` parameter
  to ``Send Message`` / ``Send Email`` keywords. Will save the email instead of sending.
- Library **RPA.Database** (:pr:`667`): Add SSL support for MySQL modules (``pymysql`` and
  ``mysql.connector``).
- Library **RPA.SAP** (:pr:`656`): Add new keywords.

17.6.0 - 12 Oct 2022
--------------------

- Library **RPA.Browser.Selenium** (:issue:`661`): Downloads correctly Mac arm64 web
  drivers. (due to ``rpaframework-core`` **10.0.1**)
- Library **RPA.Cloud.AWS** (:pr:`663`): Add more options for ``List Files`` keyword.

17.5.1 - 11 Oct 2022
--------------------

- Library **RPA.Browser.Selenium** (:pr:`660`): Ensure `use_profile` parameter is
  working as expected when set true. Affecting the ``Open Available Browser`` and
  ``Open Chrome Browser`` keywords.

17.5.0 - 07 Oct 2022
--------------------

- New library **RPA.MSGraph** (:issue:`176`, :pr:`653`): This library wraps the
  `O365 package`_, giving robots the ability to access the Microsoft Graph API programmatically.

.. _O365 package: https://pypi.org/project/O365

17.4.0 - 06 Oct 2022
--------------------

- Library **RPA.Robocorp.WorkItems** (:pr:`655`): Fix behaviour when releasing FAILED
  items with empty string `code` or `message`.
- Library **RPA.Salesforce** (:issue:`570`): Added two new keywords: ``Set Domain`` and
  ``Get Domain``. Enhanced documentation around the different ways to set a domain.

17.3.0 - 03 Oct 2022
--------------------

- Library **RPA.Database** (:pr:`649`): Add support for new `Psycopg 3 <https://anaconda.org/conda-forge/psycopg/>`_ PostgreSQL database adapter

17.2.0 - 30 Sep 2022
--------------------

- Library **RPA.Cloud.AWS** (:pr:`648`):

  - Add new keyword ``Generate Presigned URL`` for S3
  - Released in ``rpaframework-aws`` **5.1.0**

- Library **RPA.Windows** (:pr:`647`):

  - Add new keywords ``Drag and Drop`` and ``Set Focus``
  - Released in ``rpaframework-windows`` **6.1.0**

17.1.1 - 29 Sep 2022
--------------------

- Library **RPA.Email.Exchange** (:pr:`643`): Fix `access_type` parameter usage in
  keyword ``Authorize`` with "delegate" & "impersonation" accepted values.

17.1.0 - 28 Sep 2022
--------------------

- Library **RPA.Email.Exchange** (:issue:`641`): Add support for OAuth2 auto token
  refresh in Vault with `vault_name` and `vault_token_key` parameters during library
  import.

17.0.1 - 21 Sep 2022
--------------------

- Library **RPA.Cloud.AWS** (:pr:`637`):

  - All references to `Robocloud.Vault` changed to `Robocorp.Vault` (parameters and documentation).
    This is **breaking** for this library, which leads to **major** version bump also for ``rpaframework``,
    because this library can be also installed with ``rpaframework[aws]`` instead of ``rpaframework-aws``.
  - Add possibility to pass extra parameters for some S3 keywords, for example. metadata and content type.
  - Released in ``rpaframework-aws`` **5.0.0**

- Library **RPA.Excel.Files** (:pr:`638`): Add support for opening .xlsx files in ``read_only`` mode
- New library **RPA.Base64AI** (:pr:`639`): Supports `Base64 AI <https://base64.ai/>`_  IDP service
- New library **RPA.Nanonets** (:pr:`639`): Supports `Nanonets <https://nanonets.com/>`_  IDP service
- Library **RPA.Cloud.Google** (:pr:`619`):

  - Add support for `Document AI <https://cloud.google.com/document-ai/>`_  IDP service
  - Released in ``rpaframework-google`` **6.1.1**

16.3.0 - 07 Sep 2022
--------------------

- Library **RPA.Browser.Selenium** (:issue:`618`): Simplified dict-like `options`
  passing to keywords ``Open Available Browser`` and ``Open Browser``.

16.2.0 - 07 Sep 2022
--------------------

- Library **RPA.Email.ImapSmtp** (:pr:`622`): Add parameter `attachment_position` for keyword ``Send Message``

16.1.0 - 01 Sep 2022
--------------------

- Library **RPA.Browser.Selenium** (:issue:`615`): Keyword ``Open Available Browser``
  supports passing a custom `port` to open the browser on.
- Library **RPA.Windows** (``rpaframework-windows`` **6.0.1**, :issue:`609`): Fix
  clicking sibling elements retrieved with keyword ``Get Elements``. (previous bug with
  `robocorp_click_offset`)

16.0.0 - 31 Aug 2022
--------------------

- New library **RPA.MFA** (:pr:`610`) adds support for one time passwords (OTP).
  Currently supports `time` and `counter` based use cases.
- Library **RPA.Robocorp.Process** (:pr:`611`): New keywords
  ``List Process Run Artifacts`` and ``Get Robot Run Artifact``.
- Library **RPA.Browser.Selenium** (:issue:`494`):

  - Upgraded to Selenium 4. (:pr:`602`)
  - Using the new `webdriver-manager <https://pypi.org/project/webdriver-manager/>`_
    for an improved download and cache of the driver. (:issue:`607`)
  - Keyword ``Open Available Browser`` supports ``options`` parameter allowing to
    customize the browser run. (desired capabilities got deprecated; :issue:`385`)

.. warning::
  This is a **breaking** change! The library works with the following major version
  upgrades given any dependent package:

  - ``rpaframework-aws`` **4.0.0**
  - ``rpaframework-dialogs`` **4.0.0**
  - ``rpaframework-google`` **6.0.0**
  - ``rpaframework-pdf`` **5.0.0**
  - ``rpaframework-recognition`` **5.0.0**
  - ``rpaframework-windows`` **6.0.0**

15.9.0 - 22 Aug 2022
--------------------

- Library **RPA.Database**: Add support for new Oracle connector `oracledb <https://python-oracledb.readthedocs.io/en/latest/index.html>`_

15.8.1 - 19 Aug 2022
--------------------

- Library **RPA.JavaAccessBridge**: Include ``java-access-bridge-wrapper`` dependency
  **0.9.5** fixing memory leak issue
- ``rpaframework-recognition`` **4.0.2**: Fix issue with dependency ``opencv-python-headless``

15.8.0 - 12 Aug 2022
--------------------

- Library **RPA.Excel.Files** (:pr:`599`): Add parameter `formatting_as_empty` for keyword
  ``Append Rows To Worksheet``, which allows appending rows to sheet with formatted cells.
- Library **RPA.Notifier** (:pr:`603`): Fix how keyword parameters are forwarded

15.7.0 - 10 Aug 2022
--------------------

- Security dependency update (``lxml`` **4.9.1**) within the following packages:

  - ``rpaframework-aws`` **3.1.2**
  - ``rpaframework-dialogs`` **3.0.1**
  - ``rpaframework-google`` **5.0.2**
  - ``rpaframework-recognition`` **4.0.1** (``rpaframework[cv]``)

- Library **RPA.Tables** (:pr:`495`):

  - New keywords: ``Filter Table With Keyword``, ``Map Column Values``. (:issue:`226`)
  - Improved documentation. (:issue:`220`)
  - Improved `str`/`int` row index resolving.

- Library **RPA.FileSystem** (:pr:`597`): New ``Get File Stem`` keyword retrieving only
  the name of a file (without its extension) from the given `path`.

15.6.1 - 09 Aug 2022
--------------------

- Library **RPA.Salesforce** (:issue:`583`): Keyword
  ``Salesforce Query Result As Table`` bugfix on empty results.
- Library **RPA.Browser.Selenium** (:issue:`593`): Keyword ``Print To PDF`` provides
  better error message when trying to print in non-headless mode (which doesn't work
  by design; same with full page screenshots).

15.6.0 - 02 Aug 2022
--------------------

- Library **RPA.Desktop** (:pr:`592`): Ability to customize the locators path using the
  ``locators_path`` parameter during library import.
- Ability to customize the locators file path through the ``RPA_LOCATORS_DATABASE``
  environment variable. (:issue:`370`)
- Library **RPA.PDF** (:issue:`558`, ``rpaframework-pdf`` **4.1.0**): Fix ``pages``
  selection rationale when operating with PDFs. (bugs & documentation)

15.5.0 - 22 Jul 2022
--------------------

- Library **RPA.Windows** (:issue:`587`): Fix offset-based clicking. (coordinates
  relative to the center of the element with ``offset:x,y`` locator property)
- Library **RPA.Robocorp.WorkItems** (:issue:`538`): Automatically release the current
  input Work Item as ``FAILED`` `Application` when the robot fails unexpectedly.

15.4.0 - 13 Jul 2022
--------------------

- Adds ``overwrite`` parameter (default `False`) for controlling how attachment
  download happens with the following keywords (:issue:`584`):

  - **RPA.Email.ImapSmtp**:

    - ``Save Attachment``
    - ``Save Attachments``

  - **RPA.Email.Exchange**: ``Save Attachments``
  - **RPA.Outlook.Application**: ``Save Email Attachments``

15.3.0 - 08 Jul 2022
--------------------

- Library **RPA.Excel.Application**: Fixes bug with keyword ``Run Macro`` on Excel file
  names containing spaces or other problematic symbols. (:issue:`479`)
- Library **RPA.Excel.Files**:

  - Keyword ``Create Workbook`` supports now ``sheet_name`` parameter which sets a
    custom name for the newly created active sheet. (:issue:`224`)
  - Fixes a problem with Microsoft validation by stripping leading/trailing whitespace
    from the workbook properties. (:issue:`572`)

15.2.0 - 05 Jul 2022
--------------------

- Library **RPA.Email.Exchange** (:issue:`567`): Keyword ``Authorize`` supports OAuth2
  Authorization Code flow. (enable it with ``is_oauth=${True}``; Portal
  `example <https://robocorp.com/portal/robot/robocorp/example-oauth-email>`_)
- Library **RPA.FileSystem** (:pr:`568`): Add keyword examples and type hints.

15.1.4 - 23 Jun 2022
--------------------

- Fix *VSCode* keyword definitions in all packages (:issue:`560`). (*libspec* Python
  modules paths)

  - ``rpaframework-aws`` **3.1.1**
  - ``rpaframework-google`` **5.0.1**
  - ``rpaframework-pdf`` **4.0.2**
  - ``rpaframework-windows`` **5.0.1**

- Library **RPA.Desktop**: Fix docs examples returning ``Region`` elements.

15.1.3 - 22 Jun 2022
--------------------

- Fix *VSCode* keyword definitions. (*libspec* Python modules paths)

15.1.2 - 21 Jun 2022
--------------------

- Library **RPA.PDF** (:pr:`549`, ``rpaframework-pdf`` **4.0.1**): Extended PDF
  examples.
- Library **RPA.Tables** (:pr:`492`): Keyword examples updated to be more complete.
- Library **RPA.Excel.Files** (:pr:`493`): Doc strings and typehints updated.

15.1.1 - 17 Jun 2022
--------------------

- Library **RPA.JSON** (:issue:`548`): Fix *libspec* infinite recursion on ``JSONType``
  type.
- Deprecate *Lab* references under documentation.

15.1.0 - 15 Jun 2022
--------------------

- Library **RPA.Cloud.AWS** (:pr:`508`, ``rpaframework-aws`` **3.1.0**):

  - New service client support for Amazon Redshift's Data API (:issue:`496`). Keyword
    support for submitting SQL queries and obtaining results from them (can be
    performed asynchronously, if desired).
  - New service client support for Amazon STS and the `Assume Role` operation
    (:issue:`498`). The `Assume role` keyword returns temporary credentials which
    include a session token. All services updated to support using the session
    token as part of their `Init ... client` keyword.

- Library **RPA.Robocorp.WorkItems** (:pr:`536`): Expand examples for ``Release Input Work Item``
  and fix other documentation issues.
- Library **RPA.Outlook.Application** (:pr:`545`): Reduce logging

security release (all packages) - 27 May 2022
---------------------------------------------

**Critical** Python package security update concerning ``pillow`` package which is
a common image processing library for Python.

All new release versions:

    - ``rpaframework`` **15.0.0**
    - ``rpaframework-aws`` **3.0.0**
    - ``rpaframework-dialogs`` **3.0.0**
    - ``rpaframework-google`` **5.0.0**
    - ``rpaframework-pdf`` **4.0.0**
    - ``rpaframework-recognition`` **4.0.0**
    - ``rpaframework-windows`` **5.0.0**

14.2.0 - 25 May 2022
--------------------

- Library **RPA.PDF** (:issue:`515`, ``rpaframework-pdf`` **3.0.1**): Ensures
  checkboxes are ticked correctly with latest dependency upgrades.
- Library **RPA.JSON** (:issue:`481`): Keyword ``Delete From JSON`` supports *filter*
  expressions for keys removal.
- Library **RPA.Browser.Selenium** (:pr:`502`): Automatically add URL scheme when
  navigating, such as `https` (default) or `http`. This functionality is controlled
  with the keyword ``Set Default URL Scheme``.
  with the keyword `Set default URL scheme`.
- Library **RPA.Hubspot**: Fix several bugs and improve logging (:issue:`504`,
  :issue:`505`, :issue:`506`, and :issue:`507`).

14.1.1 - 12 May 2022
--------------------

- Library **RPA.Email.ImapSmtp** (:issue:`500`): Keywords ``Authorize[ Imap/Smtp]``
  support `is_oauth` parameter which instructs the client to authenticate through the
  basic (`False`) or XOAUTH2 (`True`) protocol.
- Library **RPA.Excel.Files** (:pr:`490`): Keyword examples updated to be more complete
  and Python examples have been added to all keywords.

14.1.0 - 05 May 2022
--------------------

- Library **RPA.Robocorp.WorkItems** (:issue:`485`): Automatically parse into
  ``email[body]`` payload variable the e-mail body on e-mail Process triggering with
  "Parse email" configuration option enabled in Control Room.
- Library **RPA.Hubspot** (:pr:`484`): Add keywords for creating and updating objects in
  Hubspot, as well as a new batch system when creating batched inputs via keyword.
- Library **RPA.Excel.Files** (:pr:`491`):

  - Fix ``IndexError`` when removing *.xls* worksheets.
  - Fix removing currently active worksheet.

14.0.0 - 02 May 2022
--------------------

- Robot Framework 5 support, but not restricted to (:pr:`470`):

  - Read **migration instructions** on `Taking Robot Framework 5 into use <https://robocorp.com/docs/languages-and-frameworks/robot-framework/robot-framework-5>`_
  - TRY-EXCEPT-ELSE-FINALLY
  - WHILE
  - Inline IF-ELSE IF-ELSE
  - BREAK and CONTINUE
  - RETURN

- Library **RPA.Email.Exchange** (:issue:`477`): Keyword ``Send Message`` supports
  sending messages with any combination of `recipients`, `cc` and/or `bcc`.

- The support for Python version 3.6 has been **REMOVED** from the ``rpaframework[-*]``
  packages starting with the following versions (:pr:`469`):

    - ``rpaframework`` **14.0.0**
    - ``rpaframework-aws`` **2.0.0**
    - ``rpaframework-dialogs`` **2.0.0**
    - ``rpaframework-google`` **4.0.0**
    - ``rpaframework-pdf`` **3.0.0**
    - ``rpaframework-recognition`` **3.0.0**
    - ``rpaframework-windows`` **4.0.0**

13.3.1 - 15 Apr 2022
--------------------

- Library **RPA.Windows** (``rpaframework-windows`` **3.1.1**, :pr:`473`): Fix
  documentation.

13.3.0 - 14 Apr 2022
--------------------

- Library **RPA.Dialogs**: Include fix for dependency ``robocorp-dialog`` package.
- Library **RPA.Windows** (``rpaframework-windows`` **3.1.0**, :issue:`439`):

  - Keyword ``Get Elements`` returns all similar elements matching locator. (:pr:`471`)
  - Keyword ``List Windows`` returns now extra attributes similar to the old
    deprecated ``RPA.Desktop.Windows`` library (:issue:`408`):

    - ``automation_id``
    - ``control_type``
    - ``class_name``
    - ``rectangle``
    - ``keyboard_focus``
    - ``is_active``
    - ``object``

  - Improved locators parsing and ability to enclose values containing spaces with
    ``"`` double-quote. (:issue:`363`)

  .. warning::
    This is a **breaking** change! If you use single-quote locator value enclosing,
    please switch it to double-quote instead. (e.g. ``Control Window  subname:'-
    Notepad'`` -> ``Control Window  subname:"- Notepad"``)

    If you're having issues with your current robots, pin in your *conda.yaml*
    ``rpaframework-core==7.0.1`` and stay on ``rpaframework<=13.2.0``. Once you do the
    double-quote fix, remove the pin and upgrade to the latest ``rpaframework``.

13.2.0 - 08 Apr 2022
--------------------

- New library **RPA.Hubspot**: Library support for Hubspot CRM API. Current keywords
  primarily focus on retrieving data from Hubspot, there is currently no support for
  updating information.

13.1.0 - 07 Apr 2022
--------------------

- Library **RPA.Database**: Fix configuration value retrieval. (:pr:`456`)
- Library **RPA.Dialogs**: Add next button to support wizard style dialogs. (:issue:`452`)

13.0.3 - 05 Apr 2022
--------------------

- Library **RPA.Database**: Fix queries with ``pyodbc`` module. (affects Microsoft SQL
  Server, :issue:`443`)

13.0.2 - 04 Apr 2022
--------------------

- Library **RPA.Email.ImapSmtp**: Fix handling of ``cc`` and ``bcc`` fields
  with ``Send Message`` keyword
- Library **RPA.Cloud.AWS**:

  - Fix initializing services with Vault (broken by **13.0.1** release)
  - The service region can also be given as a environment variable or as Vault
    key: ``AWS_REGION``
  - Included and available as separate package ``rpaframework-aws`` **1.0.3**

13.0.1 - 01 Apr 2022
--------------------

- Library **RPA.Cloud.AWS**: Fix getting analysis result from larger PDF files
- Library **RPA.Tables**: Fix reading table from CSV file with longer rows
- Various updates to keyword type hinting
- New package ``rpaframework-aws`` **1.0.2** (can be used without ``rpaframework`` package)

13.0.0 - 28 Mar 2022
--------------------

- Major version upgrades for the following packages (incompatible with
  ``rpaframework<13``):

  - ``rpaframework-google`` **3.0.0**
  - ``rpaframework-recognition`` **2.0.0**
  - ``rpaframework-windows`` **3.0.0**
  - ``rpaframework-dialogs`` **1.0.0**
  - ``rpaframework-pdf`` **2.0.0**

  .. warning::
    Any optional package (`google`, `recognition`) should be upgraded at least to the
    version above in your *conda.yaml* in order to use ``rpaframework`` **13.0.0**.
    (if such dependencies are explicitly pinned)

  .. note::
    Package ``rpaframework-windows`` can be omitted entirely from the *conda.yaml*
    since it's included automatically with this version.

12.10.1 - 25 Mar 2022
---------------------

- Library **RPA.Email.ImapSmtp**: Fix multiple recipients error with ``Send Message``

12.10.0 - 23 Mar 2022
---------------------

- Library **RPA.Cloud.AWS**: Fix ``Download Files`` on saving objects with paths.
- Library **RPA.HTTP**: Overriding ``RequestsLibrary`` logging to DEBUG level for
  request and response.
- Automatically installing ``rpaframework-windows`` **2.3.2**. (no need to specify this
  dependency in your *conda.yaml* anymore)
- Deprecated ``RPA.Desktop.Windows`` in favor of ``RPA.Windows``.

12.9.0 - 11 Mar 2022
--------------------

- Library **RPA.Robocorp.Process**:

  - Add keyword ``List Process Run Work Items``
  - Add parameter `step_run_id` into ``Get Process Run Status``

- Library **RPA.Desktop.Windows**: Fix issue with ``Get Window Elements``
- Library **RPA.Browser.Selenium**: Fix issue of `auto_close=False` "hanging" on
  Windows OS task teardown
- Library **RPA.Email.ImapSmtp**:

  - Add parameters `cc` and `bcc` to the ``Send Message`` keyword
  - Fix issue with ``List Messages``

- Library **RPA.Email.Exchange**:

  - Add more filtering keys to the `criterion` parameter (detailed description in the
    `library documentation <https://rpaframework.org/libraries/email_exchange/index.html>`_)
  - The `contains` parameter has been deprecated as filtering keys now has `_contains` option, for
    example `sender_contains:name@domain.com`
  - Fix issue with keyword ``Wait For Message``

- Resolved **Github** issues

  - `RPA.Email.Exchange. Error with Wait For Message keyword filtering <https://github.com/robocorp/rpaframework/issues/418>`_
  - `RPA.Email.Exchange Wait for Message keyword throws an error <https://github.com/robocorp/rpaframework/issues/377>`_
  - `Email.Exchange: Add more support for email filtering <https://github.com/robocorp/rpaframework/issues/410>`_
  - `Get Window Elements triggers NotImplementedError <https://github.com/robocorp/rpaframework/issues/344>`_
  - `Email.ImapSmtp: Issues with filtering emails <https://github.com/robocorp/rpaframework/issues/409>`_

12.8.2 - 25 Feb 2022
--------------------

- Library **RPA.Robocorp.WorkItems**: Keyword ``Create Output Work Item`` supports
  adding `variables`, `files` and saving in one go through parameters. (:issue:`392`)
- Library **RPA.Windows** (``rpaframework-windows`` **2.2.2**): Keyword
  ``Get Os Version`` returns proper Windows version. (:pr:`394`)
- Library **RPA.Excel.Files**:

  - Fix I/O for tables with one or no rows. (:issue:`391`)
  - Add parameter ``data_only`` to keyword ``Open Workbook`` to read value instead of
    formula on XLSX file.

12.8.1 - 18 Feb 2022
--------------------

- Library **RPA.Excel.Application**: Fix on Windows 11 given pywin32 dependency update.
- Package **comtypes** upgrade which fixes `Syntax Error` issues.
- Library **RPA.core**: Add internal ``interact()`` helper for interrupting code
  execution and spawning an interactive shell which aids REPL debugging.
- Library **RPA.Windows** (``rpaframework-windows`` **2.2.1**):

  - Add keyword ``Get Os Version`` which returns the current Windows version.
  - Add keyword ``Close Window`` which closes any matched open window.
  - Keyword ``Get Elements`` returns now only sibling elements similar to provided
    `locator`.
  - General library and tests fixes. (`COMError`, comtypes)

12.8.0 - 10 Feb 2022
--------------------

- Library **RPA.Tables**: Add delimiter support to ``Write Table To CSV``

12.7.0 - 10 Feb 2022
--------------------

- Library **RPA.Email.ImapSmtp**

  - Add email dictionary support for all keywords with parameter ``criterion``
  - Add `prefix` parameter to keywords ``Save Message`` and ``Save Attachment``

12.6.1 - 08 Feb 2022
--------------------

- Library **RPA.Email.Exchange**: Fix saving .eml attachments from emails (:issue:`381`)
- Library **RPA.Email.ImapSmtp**: Fix handling of folder names with spaces (:issue:`380`)

12.6.0 - 27 Jan 2022
--------------------

- Library **RPA.JavaAccessBridge**: Add ``Close Java Window`` keyword

12.5.1 - 18 Jan 2022
--------------------

- Fix importing issues of **RPA.Desktop** on Windows due to ``comtypes`` dependency
  Python 3 compatibility.

12.5.0 - 17 Jan 2022
--------------------

- Library **RPA.Email.Exchange**: Add .eml file support to ``Save Attachments`` keyword
- Library **RPA.JavaAccessBridge**:

  - Add `strict` locator match support to locator string and to keyword ``Get Elements``
  - Fix some issues related to ``JavaElement`` objects

12.4.1 - 12 Jan 2022
--------------------

- Library **RPA.JavaAccessBridge**:

  - Fix scaling issue when clicking element coordinates (:issue:`355`)
  - Add ``click`` and ``type_text`` methods into ``Java Element`` object
  - Fix ``Type Text

- Library **RPA.Notifier**:

  - Fix handling of keyword **kwargs parameter
  - Add kwargs documentation and examples

12.3.0 - 10 Jan 2022
--------------------

- Library **RPA.JavaAccessBridge**:

    - Add keyword ``Read Table`` which returns table cells as ``Java Element``s
     (more info in the documentation).
    - Keyword ``Get Elements`` can also return elements as ``Java Element`` when
     new parameter `java_element=True`.
    - Fix locator value parsing for keys like `indexInParent` which can have
     only integer value.
    - Open known issue: clicking table cell elements seems to be problematic
     atleast on Java Swing application (:issue:`355`)

12.2.0 - 17 Dec 2021
--------------------

- Library **RPA.Database**:

    - Keyword ``Query`` supports now a ``returning`` parameter which explicitly
      instructs the statement execution to return or not the fetched values.
      (:issue:`286`)
    - Auto commits and rollbacks fixes given the ``sanstran`` flag. (:issue:`282`)

- Library **RPA.PDF**: Fixed ``Add Watermark Image To PDF`` with the same file for both
  input and output (:issue:`337`, ``rpaframework-pdf`` **1.30.4**)

12.1.2 - 14 Dec 2021
--------------------

- Library **RPA.PDF**: HTML -> PDF rendering serialized fonts cleanup bug fix
  (:pr:`322`, ``rpaframework-pdf`` **1.30.3**)

12.1.1 - 7 Dec 2021
-------------------

- Library **RPA.PDF**: Serialize PDF related fonts under Robocorp's home directory
  (:pr:`315`, ``rpaframework-pdf`` **1.30.2**)

12.1.0 - 7 Dec 2021
-------------------

- Library **RPA.PDF** (:issue:`304`, ``rpaframework-pdf`` **1.30.1**):

    - Fixed unicode when rendering HTML as PDF
    - Fixed PDF form fields setting given various codecs
    - Faster PDF parsing
    - Updated docs on ``Find Text`` keyword and library

Releases on 01 Dec 2021
-----------------------

- All rpaframework packages include now `.libspec` file for each library in the package.
  This will make coding experience in the VSCode editor better via ``Robot Framework Language Server``
  extension.

  - `rpaframework` **12.0.3**
  - `rpaframework-windows` **1.4.2**
  - `rpaframework-google` **1.0.2**

12.0.0 - 29 Nov 2021
--------------------

- Add .libspec files for all the libraries (used by VScode extension)
- Library **RPA.PDF** (:issue:`243`):

    - Keyword ``Find Text`` improvements and **breaking** changes:

        - Sets and works with multiple anchors if more than one are found
        - Anchor search supports "regex:" criteria too through the locator
        - `only_closest` parameter got replaced by `closest_neighbours` which can
          specify the max number of adjacent texts to return in the match object
        - The return value is a list of `Match` objects where every match has an
          `anchor` (the pinpoint in the PDF through locator) and a list of `neighbours`
          (the adjacent texts to the anchor given the provided direction)

    - Fixed by ``rpaframework-pdf`` **1.26.11** (included in this release)

11.6.4 - 24 Nov 2021
--------------------

- API retrying improvements affecting Work Items (:issue:`298`)
- Library **RPA.Email.ImapSmtp**: Keyword ``Email To Document`` for converting HTML or
  Text e-mails into Word documents (:issue:`295`)

- Library **RPA.Robocorp.WorkItems** (:pr:`285`):

  - Removed Keyword ``Parse Work Item From Email``
  - Automatically loads e-mail body formats like JSON/YAML/Text/HTML into "parsedEmail"
    work item variable

- Updated ``rpaframework-recognition`` dependency (to version 1.0.0) (:pr:`303`)

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

- Migration guide: Given this major upgrade, the ``Load Work Item ...`` keywords got
  removed with functionality replaced by ``Get Input Work Item``. Use this keyword for
  loading your next input work item no matter if you're running the robot in Control
  Room or locally. Keep in mind that under *Robot Framework* code, the first input work
  item gets loaded automatically and you don't need to call this keyword if you only
  process one item in your run. For disabling this behavior, use ``autoload=${False}``
  when importing the ``RPA.Robocorp.WorkItems`` library.

    If multiple steps are configured in Control Room, make sure that "Done items
    forwarding" is checked in Process' configuration. Uncheck this if you have a modern
    robot that explicitly retrieves multiple input work items and creates output ones.

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
