*** Settings ***
Library           RPA.Salesforce    domain=CustomDomainHere
Force Tags        salesforce

*** Variables ***
${NOT_AUTHENTICATED_ERROR}    SalesforceAuthenticationError: *
${AUTHENTICATION_FAILED}    SalesforceAuthenticationFailed: *

*** Tasks ***
Not authenticated salesforce query
    Run Keyword And Expect Error
    ...    ${NOT_AUTHENTICATED_ERROR}
    ...    Salesforce Query    Select Id, Name from Account

Not authenticated set account
    Run Keyword And Expect Error
    ...    ${NOT_AUTHENTICATED_ERROR}
    ...    Set Account    account_name=Nokia

Not authenticated get salesforce object by id
    Run Keyword And Expect Error
    ...    ${NOT_AUTHENTICATED_ERROR}
    ...    Get Salesforce Object By Id    Account    23e3334

Not authenticated create salesforce object
    Run Keyword And Expect Error
    ...    ${NOT_AUTHENTICATED_ERROR}
    ...    Create Salesforce Object    Account    ""

Not authenticated update salesforce object
    Run Keyword And Expect Error
    ...    ${NOT_AUTHENTICATED_ERROR}
    ...    Update Salesforce Object    Account    6237452354    ""

Not authenticated upsert salesforce object
    Run Keyword And Expect Error
    ...    ${NOT_AUTHENTICATED_ERROR}
    ...    Upsert Salesforce Object    Account    6237452354    ""

Not authenticated delete salesforce object
    Run Keyword And Expect Error
    ...    ${NOT_AUTHENTICATED_ERROR}
    ...    Delete Salesforce Object    Account    6237452354

Not authenticated get salesforce object metadata
    Run Keyword And Expect Error
    ...    ${NOT_AUTHENTICATED_ERROR}
    ...    Get Salesforce Object Metadata    Account

Not authenticated describe salesforce object
    Run Keyword And Expect Error
    ...    ${NOT_AUTHENTICATED_ERROR}
    ...    Describe Salesforce Object    Account

Incorrect credentials
    [Tags]    skip
    Run Keyword And Expect Error
    ...    ${AUTHENTICATION_FAILED}
    ...    Auth With Token
    ...    username=notexisting@notexisting.com
    ...    password=secretpassword
    ...    api_token=324daqewjjsakjshh333

Confirm current domain
    ${domain}=    Get Domain
    Should Be Equal As Strings    ${domain}    CustomDomainHere

Set domain
    Set Domain    Sandbox
    ${domain}=    Get Domain
    Should Be Equal As Strings    ${domain}    test
