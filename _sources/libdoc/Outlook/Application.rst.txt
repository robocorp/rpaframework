###################
Robot Framework API
###################

***********
Description
***********

:Library scope: Task

Library for manipulating Outlook application.

********
Keywords
********

:Close Document:
  :Arguments: save_changes=False



:Open Application:
  :Arguments: visible=False, display_alerts=False

  Open Microsoft application.


:Quit Application:
  :Arguments: save_changes=False



:Send Message:
  :Arguments: recipients, subject, body, html_body=False, attachments=None

  Send message with Outlook

