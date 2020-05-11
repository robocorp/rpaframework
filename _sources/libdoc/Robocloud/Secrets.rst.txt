###################
Robot Framework API
###################

***********
Description
***********

:Library scope: Task

Handler for SecretManager. Decides which SecretManager to use based on
environment variable `RPA_SECRET_MANAGER`. If environment variable is not
defined then `RobocloudSecrets` is used as default SecretManager.

:raises Exception: if configured SecretManager does not implement
                   `BaseSecretManager` class
:raises Exception: if configured SecretManager does not exist in the namespace

********
Keywords
********

:Get Secret:
  :Arguments: secret_name

  Get secret defined with key `secret_name` and return
  value of the key.

  If key does not exist raises `KeyError`.

