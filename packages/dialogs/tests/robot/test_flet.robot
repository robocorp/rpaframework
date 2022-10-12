*** Settings ***
Library           DateTime
Library           RPA.Dialogs
Force Tags        skip

*** Variables ***
@{EMPTY_LIST}

*** Test Cases ***
Failure dialog
    Add checkbox    checkbox-field-2    Checkbox label    default=True
    Add submit buttons    one,two
    Run Dialog
