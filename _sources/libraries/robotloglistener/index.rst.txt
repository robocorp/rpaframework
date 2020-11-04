################
RobotLogListener
################

.. contents:: Table of Contents
   :local:
   :depth: 1

***********
Description
***********

`RobotLogListener` is a library that implements Robot Framework Listener v2 interface.

************************
About keyword parameters
************************

Parameters `names` and `keywords` for keywords `Mute Run On Failure` and `Register Protected Keywords`
do not need to be full names of keywords, ie. all keywords matching even partially will be affected.
`Run Keyword` would match all `BuiltIn` library keywords (17 keywords in RF 3.2.1) and of course all
`Run Keyword` named keywords in any resource and/or library file which are imported would be matched also.

*******************
Mute Run On Failure
*******************

This keyword is to be used specifically with `RPA.Browser` library, which extends
`SeleniumLibrary`.  Normally most of the `SeleniumLibrary` keywords execute `run_on_failure`
behaviour, which can be set at library initialization. By default this behaviour is running
`Capture Page Screenshot` keyword on failure.

In the example task `Check the official website` below the keyword `Run Keyword` is muted and when
it runs the keyword `Element Should Be Visible` then those failures do not create page screenshots
into log file.

It is also possible to change default failure behaviour by giving parameter
`optional_keyword_to_run` for `Mute Run On Failure`, see task `Check the official website with error log`.
This optional keyword would be then executed on failure. Due to the underlying `SeleniumLibrary`
implementation this keyword can't have arguments.

Example of using `Mute Run On Failure` without and with optional keyword to run.

.. code-block:: robotframework
   :linenos:

   *** Settings ***
   Library         RPA.Browser
   Library         RPA.RobotLogListener
   Task Setup      Set Task Variable   ${TRIES}   1
   Task Teardown   Close All Browsers

   *** Tasks ***
   Check the official website
      Mute Run On Failure   Run Keyword
      Open Available Browser   https://www.robocorp.com
      Check for visible element
      Capture Page Screenshot

   Check the official website with error log
      Mute Run On Failure   Run Keyword  optional_keyword_to_run=Log tries
      Open Available Browser   https://www.robocorp.com
      Check for visible element
      Capture Page Screenshot

   *** Keywords ***
   Check for visible element
      FOR  ${idx}  IN RANGE  1   20
         Set Task Variable   ${TRIES}   ${idx}
         ${status}   Run Keyword And Return Status   Element Should Be Visible  id:xyz
         Exit For Loop If   '${status}' == 'PASS'
         Sleep  2s
      END

   Log tries
      Log  Checked element visibility ${TRIES} times


***************************
Register Protected Keywords
***************************

This keyword is used to totally disable logging for named keywords. In the example below
the keyword `This will not output` is protected and it will not be logging into Robot Framework
log files.

Robot Framework
===============

.. code-block:: robotframework
    :linenos:

    *** Settings ***
    Library         RPA.RobotLogListener

    *** Tasks ***
    Protecting keywords
       This will not output        # will output because called before register
       Register Protected Keywords    This will not output
       This will not output        # is now registered
       This will output

    *** Keywords ***
    This will not output
       Log   1

    This will output
       Log   2


Python
======

.. code-block:: python
    :linenos:

    from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
    from RPA.RobotLogListener import RobotLogListener

    try:
       BuiltIn().import_library("RPA.RobotLogListener")
    except RobotNotRunningError:
       pass

    class CustomLibrary:

       def __init__(self):
          listener = RobotLogListener()
          listener.register_protected_keywords(
                ["CustomLibrary.special_keyword"]
          )

       def special_keyword(self):
          print('will not be written to log')
          return 'not shown in the log'


*****************
API Documentation
*****************

See :download:`libdoc documentation <../../libdoc/RPA_RobotLogListener.html>`.

.. toctree::
   :maxdepth: 1

   ../../robot/RobotLogListener.rst
   python
