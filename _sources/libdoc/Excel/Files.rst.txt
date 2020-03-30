###################
Robot Framework API
###################

***********
Description
***********

:Library scope: Task

Robot Framework library for manipulating Excel files.

To run macros or load password protected worksheets,
please use the Excel application library.

********
Keywords
********

:Append Rows To Worksheet:
  :Arguments: content, name=None



:Close Workbook:


:Create Workbook:
  :Arguments: path=None, fmt=xlsx



:Create Worksheet:
  :Arguments: name, content=None, exist_ok=False



:Get Active Worksheet:


:List Worksheets:
  List all names of worksheets in the given workbook.

:Open Workbook:
  :Arguments: path



:Read Worksheet:
  :Arguments: name=None, header=False

  Read the content of a worksheet into a list.

:Remove Worksheet:
  :Arguments: name=None



:Rename Worksheet:
  :Arguments: src_name, dst_name



:Save Workbook:
  :Arguments: path=None



:Set Active Worksheet:
  :Arguments: value



:Worksheet Exists:
  :Arguments: name

  Return True if worksheet with given name is in workbook.
