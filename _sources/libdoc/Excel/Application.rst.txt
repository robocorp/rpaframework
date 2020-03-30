###################
Robot Framework API
###################

***********
Description
***********

:Library scope: Task

Library for manipulating Excel application.

********
Keywords
********

:Add New Sheet:
  :Arguments: sheetname, tabname=None, create_workbook=True

  Add new worksheet to workbook. Workbook is created by default if
  it does not exist.

  :raises ValueError: error is raised if workbook does not exist and
      `create_workbook` is False

:Add New Workbook:
  Adds new workbook for Excel application

:Close Document:
  :Arguments: save_changes=False



:Find First Available Row:
  :Arguments: worksheet=None, row=1, column=1

  Find first available free row and cell


:Open Application:
  :Arguments: visible=False, display_alerts=False

  Open Microsoft application.


:Open Workbook:
  :Arguments: filename

  Open Excel by filename


:Quit Application:
  :Arguments: save_changes=False



:Save Excel:
  Saves Excel file

:Save Excel As:
  :Arguments: filename, autofit=False

  Save Excel with name if workbook is open


:Set Active Worksheet:
  :Arguments: sheetname=None, sheetnumber=None

  Set active worksheet by either its sheet number or name


:Write To Cells:
  :Arguments: worksheet=None, row=None, column=None, value=None, number_format=None, formula=None

  Write value, number_format and/or formula into cell.

  :raises ValueError: if cell is not given
