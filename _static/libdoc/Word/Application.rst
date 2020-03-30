###################
Robot Framework API
###################

***********
Description
***********

:Library scope: Task

Library for manipulating Word application.

********
Keywords
********

:Close Document:
  :Arguments: save_changes=False



:Create New Document:
  Create new document for Word application

:Export To Pdf:
  :Arguments: filename

  Export active document into PDF file.


:Get All Texts:
  Get all texts from active document


:Open Application:
  :Arguments: visible=False, display_alerts=False

  Open Microsoft application.


:Open File:
  :Arguments: filename=None

  Open Word document with filename.


:Quit Application:
  :Arguments: save_changes=False



:Replace Text:
  :Arguments: find, replace

  Replace text in active document


:Save Document:
  Save active document

:Save Document As:
  :Arguments: filename, fileformat=None

  Save document with filename and optionally with given fileformat


:Set Footer:
  :Arguments: text

  Set footer for the active document


:Set Header:
  :Arguments: text

  Set header for the active document


:Write Text:
  :Arguments: text, newline=True

  Writes given text at the end of the document

