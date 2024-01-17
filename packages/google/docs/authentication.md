# Authentication examples with `RPA.Cloud.Google` library

## Authenticating with `service account`

- Method 1 as environment variables, `GOOGLE_APPLICATION_CREDENTIALS` with path to service account file.
- Method 2 as keyword parameter to `Init Storage` for example.
- Method 3 as Robocorp vault secret. The vault name and secret key name needs to be given in library init or with keyword `Set Robocorp Vault`. Secret value should contain JSON file contents.

### Method 1 examples

Python

```python
from RPA.Cloud.Google import Google
from robocorp.tasks import task

@task
def googling():
    library = Google()
    library.init_vision()
```

Robot Framework

```robotframework
*** Settings ***
Library   RPA.Cloud.Google

*** Tasks ***
Init Google services
    # NO parameters for Init Vision, expecting to get JSON
    # with GOOGLE_APPLICATION_CREDENTIALS environment variable
    Init Vision
```

### Method 2 examples

Python

```python
from RPA.Cloud.Google import Google
from robocorp.tasks import task

@task
def googling():
    library = Google()
    library.init_speech_to_text("/path/to/service_account.json")
```

Robot Framework

```robotframework
*** Settings ***
Library   RPA.Cloud.Google

*** Tasks ***
Init Google services
    Init Speech To Text   /path/to/service_account.json
```

### Method 3 examples

Python

```python
from RPA.Cloud.Google import Google
from robocorp.tasks import task

@task
def googling_with_library_init():
    library = Google(vault_name="googlecloud", vault_secret_key="servicecreds")
    library.init_storage()

@task
def googling_with_keyword():
    library = Google()
    library.set_robocorp_vault(vault_name="googlecloud", vault_secret_key="servicecreds")
    library.init_storage()
```

Robot Framework - library init

```robotframework
*** Settings ***
Library   RPA.Cloud.Google
...       vault_name=googlecloud
...       vault_secret_key=servicecreds

*** Tasks ***
Init Google services
    Init Storage
```

Robot Framework - using keyword

```robotframework
*** Settings ***
Library   RPA.Cloud.Google

*** Tasks ***
Init Google services
    Set Robocorp Vault   vault_name=googlecloud  vault_secret_key=servicecreds
    Init Storage
```

## Authenticating with `OAuth`

- Method 1 as keyword parameter `token_file` to `Init Storage` for example.
- Method 2 as Robocorp vault secret. The vault name and secret key name needs to be given in library init or with keyword `Set Robocorp Vault`. Secret value should contain JSON file contents.

### Method 1. The Google Apps Script and Google Drive services are authenticated using this method.

Python

```python
from RPA.Cloud.Google import Google
from robocorp.tasks import task

@task
def googling():
    oauth_token = "/path/to/oauth_token.json"
    scopes = ["forms", "spreadsheets"]
    library = Google()
    library.init_apps_script(token_file=oauth_token, scopes=scopes)
```

Robot Framework

```robotframework
*** Settings ***
Library   RPA.Cloud.Google

*** Variables ***
@{SCRIPT_SCOPES}     forms   spreadsheets
${OAUTH_TOKEN}  /path/to/oauth_token.json

*** Tasks ***
Init Google OAuth services
    Init Apps Script    token_file=${OAUTH_TOKEN}   ${SCRIPT_SCOPES}
```

### Method 2. setting Robocorp Vault in the library init

Python

```python
from RPA.Cloud.Google import Google
from robocorp.tasks import task

@task
def googling():
    library = Google(vault_name="googlecloud", vault_secret_key="oauth", cloud_auth_type="token")
    library.init_storage()
```

Robot Framework

```robotframework
*** Settings ***
Library   RPA.Cloud.Google
...       vault_name=googlecloud
...       vault_secret_key=oauth
...       cloud_auth_type=token

*** Tasks ***
Init Google services
    Init Storage
```

### Creating and using OAuth token file

The token file can be created using `credentials.json` by running command `rpa-google-oauth` which will start web based authentication process outputting the token at the end. Token could be stored into `Robocorp Vault`.

```shell
rpa-google-oauth --credentials <filepath> --service drive
```

or

```shell
rpa-google-oauth --credentials <filepath> --scopes drive.appdata,drive.file,drive.install
```

Example Vault content.

```json
"googlecloud": {
    "oauth-token": "gANfd123321aabeedYsc"
}
```

Using the Vault.

```robotframework
*** Keywords ***
Set up Google Drive authentication
    Set Robocorp Vault   vault_name=googlecloud
    ...  vault_secret_key=oauth-token
    ...  cloud_auth_type=token
    Init Drive
```
