###################
Robot Framework API
###################

***********
Description
***********

:Library scope: Task

Library for interfacing with Microsoft Exchange Web Services (EWS).


********
Keywords
********

:Authorize:
  :Arguments: username, password, autodiscover=True

  Connect to Exchange account


:List Messages:
  :Arguments: count=100

  List messages in the account inbox. Order by descending
  received time.

:Send Message:
  :Arguments: recipients=None, cc_recipients=None, bcc_recipients=None, subject=, body=, save=False

  Keyword for sending message through connected Exchange account.

  Email addresses can be prefixed with `ex:` to indicate Exchange
  account address.


