*** Settings ***
Library           RPA.Hubspot
Library           Collections
Force Tags        hubspot

*** Variables ***
${NOT_AUTHENTICATED_ERROR}    STARTS:HubSpotAuthenticationError:
${AUTHENTICATION_FAILED}    STARTS:ApiException: (401)
${HUBSPOT_TYPE_ERROR}    STARTS:HubSpotObjectTypeError:

*** Tasks ***
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
    Run Keyword And Expect Error    ${AUTHENTICATION_FAILED}
    ...    Search for objects    object_type=CONTACTS

Search for Contact by First Name Returns Contacts
    Auth with API key    %{API_KEY}
    ${search_object}=    Evaluate    [{'filters':[{'propertyName':'firstname','operator':'EQ','value':'%{FIRST_NAME}'}]}]
    ${contacts}=    Search for objects    CONTACTS    search=${search_object}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    %{FIRST_NAME}    case_insensitive=${True}

Search for All Contacts Returns 1000 Contacts
    Auth with API key    %{API_KEY}
    ${search_object}=    Evaluate    [{'filters':[{'propertyName':'firstname','operator':'HAS_PROPERTY'}]}]
    ${contacts}=    Search for objects    CONTACTS    search=${search_object}
    ${length}=    Get Length    ${contacts}
    Should Be Equal As Integers    1000    ${length}

Retrieve One Object Using ID Returns Object
    Auth with API key    %{API_KEY}
    ${contact}=    Get object    CONTACT    %{OBJECT_ID}
    Should Be Equal    %{OBJECT_ID}    ${contact.id}

List company associations for contact returns one company
    Auth with API key    %{API_KEY}
    ${associations}=    List associations    CONTACT    %{OBJECT_ID}    COMPANY
    Should Be Equal    %{COMPANY_ID}    ${{$associations[0].id}}

Retrieve Custom Object Using Custom ID Returns Object
    Auth with API key    %{API_KEY}
    ${custom_object}=    Get object    %{CUSTOM_OBJECT_TYPE}    %{CUSTOM_OBJ_ID}
    ...    id_property=%{ID_PROPERTY}    properties=%{ID_PROPERTY}
    Should Be Equal    %{CUSTOM_OBJ_ID}    ${custom_object.properties["%{ID_PROPERTY}"]}
