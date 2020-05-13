Release notes
=============

Upcoming release
----------------

- New library: Twitter

0.9.2
-----

- Updated Robot Framework to 3.2.1


0.9.1
-----

- Email.ImapStmp: Fix attachment handling for kw ``Send Message``
- Excel Application library: Add keyword ``Run Macro``
- PDF: Add keywords:

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

- Tables:

  - **Note**: This change is backwards incompatible
  - Removed limitation of column names being valid Python identifiers
  - Default iteration method changed to dictionaries instead of namedtuples
  - Keywords that return rows or columns now harmonized to return them in
    dictionary format by default, with option to use lists
  - Table head/tail keywords changed to return new Table instance
  - Added keyword for trimming extra whitespace from column names

- Excel files library: Trim column names in addition to rows

0.8.7
-----

- OperatingSystem: psutils dependency marked as Windows only because
  it has wheel files only for Windows

0.8.6
-----

- HTTP:

  - Add keyword ``Download``
  - Add ``overwrite`` option to ``HTTP Get``

- FileSystem:

  - Fix string interpolation in error messages
  - Add ``force`` option for file removal keywords
  - Add ``overwrite`` option for file create keywords

- Tables: Add keyword ``Trim empty rows``
- Excel files library:

  - Add keyword ``Read worksheet as table``
  - Auto-convert integer values in .xls worksheets

0.8.5
-----

- PDF: Add ``Encrypt PDF`` and ``Add Pages To Source PDF`` keywords.
- Windows: Add aliases for element locators,
  for better Robocode Lab compatibility
- HTTP: Add keyword ``HTTP Get``
- Tables: Fix missing cell values for sanitized columns

0.8.4
-----

- Fix: PDF ``Template HTML to PDF`` keyword

0.8.3
-----

- Fix: Windows ``drag_and_drop`` keyword
- New library: Netsuite
- PDF: add new keywords

0.8.2
-----

- Windows: Add keyword for clicking image templates
- Windows: Add keyword for drag and drop

0.8.1
-----

- Browser: Fix ``Open Available Browser`` kw parameter bug

0.8.0
-----

- New library: Salesforce
- New library: Database

0.7.5
-----

- ImapSmtp: Separate how IMAP and SMTP are handled in the library
- Windows: Improve documentation for keys
- Browser: Manage webdrivermanager download error

0.7.4
-----

- Browser: Restructure how driver downloads and logging are handled

0.7.3
-----

- Browser: Detect Chrome and chromedriver versions. Download driver if they differ
- Images: Don't template match same region multiple times
- Tables:

  - Added new keywords: ``Set table row``, ``Set table column``, ``Set table cell``
  - Renamed keyword ``Get cell value`` to ``Get table cell``

0.7.2
-----

- Browser: Store webdrivers in temporary directory

0.7.1
-----
First public release of RPA Framework
