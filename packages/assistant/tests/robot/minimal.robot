*** Settings ***

Library  RPA.Assistant

*** Keywords ***
Handler Keyword
    Log to Console  test
    Sleep  1

*** Test Cases ***
Main task
    [Tags]  skip
    Add Heading  some buttons
    Add Button  label="button"  function=Handler Keyword
    Run Dialog

