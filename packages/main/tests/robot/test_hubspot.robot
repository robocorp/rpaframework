*** Settings ***
Library           RPA.Hubspot
Force Tags        hubspot

*** Variables ***
${NOT_AUTHENTICATED_ERROR}    STARTS:HubSpotAuthenticationError:
${AUTHENTICATION_FAILED}    STARTS:ApiException: (401)
${HUBSPOT_TYPE_ERROR}    STARTS:HubSpotObjectTypeError:

*** Tasks ***
List contacts should fail without authentication
    Run Keyword And Expect Error    ${NOT_AUTHENTICATED_ERROR}
    ...    List contacts

Search for objects should fail without authentication
    Run Keyword And Expect Error    ${NOT_AUTHENTICATED_ERROR}
    ...    Search for objects    object_type=CONTACTS

List associations should fail without authentication
    Run Keyword And Expect Error    ${NOT_AUTHENTICATED_ERROR}
    ...    List associations    object_type=contact    object_id=123    to_object_type=company

Get object should fail without authentication
    Run Keyword And Expect Error    ${NOT_AUTHENTICATED_ERROR}
    ...    Get object    object_type=contact    object_id=123

Authentication fails with bad API key
    Auth with API key    api_key=123
    Run Keyword And Expect Error    ${AUTHENTICATION_FAILED}    List contacts
