*** Settings ***
Documentation       API keys and variables must be provided in ./setup.py. These should use a live or
...                 sandbox Hubspot environment to test the API, there is no mocking function.

Library             RPA.Hubspot
Library             Collections
Variables           ./setup.py

Force Tags          hubspot

*** Variables ***
${NOT_AUTHENTICATED_ERROR}      STARTS:HubSpotAuthenticationError:
${AUTHENTICATION_FAILED}        HubSpotAuthenticationError: Authentication was not successful.
${HUBSPOT_TYPE_ERROR}           STARTS:HubSpotObjectTypeError:

*** Test Cases ***
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
    Run Keyword And Expect Error    ${AUTHENTICATION_FAILED}
    ...    Auth with API key    api_key=123

Search for Contact by First Name Returns Contacts
    Auth with API key    ${API_KEY}
    ${search_object}=    Evaluate
    ...    [{'filters':[{'propertyName':'firstname','operator':'EQ','value':'${FIRST_NAME}'}]}]
    ${contacts}=    Search for objects    CONTACTS    search=${search_object}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}

Search for All Contacts Returns 1000 Contacts
    Auth with API key    ${API_KEY}
    ${search_object}=    Evaluate    [{'filters':[{'propertyName':'firstname','operator':'HAS_PROPERTY'}]}]
    ${contacts}=    Search for objects    CONTACTS    search=${search_object}
    ${length}=    Get Length    ${contacts}
    Should Be Equal As Integers    1000    ${length}

Search for object with natural language returns object
    Auth with API key    ${API_KEY}
    ${contacts}=    Search for objects    CONTACTS    firstname    EQ    ${FIRST_NAME}    AND    lastname    EQ
    ...    ${LAST_NAME}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}
    Should Contain Match    ${{[c.properties["lastname"] for c in $contacts]}}    ${LAST_NAME}
    ...    case_insensitive=${True}

Seach for object using IN operator returns object
    Auth with API key    ${API_KEY}
    ${contacts}=    Search for objects    CONTACTS    email    IN    ${CONTACT_EMAILS}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME_2}
    ...    case_insensitive=${True}

Search for object using BETWEEN operator returns object
    Auth with API key    ${API_KEY}
    ${contacts}=    Search for objects    CONTACTS    hs_object_id    BETWEEN    ${{[$CONTACT_ID,$CONTACT_ID]}}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}
    Should Contain Match    ${{[c.properties["lastname"] for c in $contacts]}}    ${LAST_NAME}
    ...    case_insensitive=${True}

Retrieve One Object Using ID Returns Object
    Auth with API key    ${API_KEY}
    ${contact}=    Get object    CONTACT    ${OBJECT_ID}
    Should Be Equal As Strings    ${OBJECT_ID}    ${contact.id}

Retrieve Objects Using IDs Returns Objects
    Auth with API key    ${API_KEY}
    ${contacts}=    Get object    CONTACT    ${OBJECT_IDS}
    FOR    ${obj}    IN    @{contacts}
        List should contain value    ${EXPECTED_EMAILS}    ${obj.properties}[email]
    END

List company associations for contact returns one company
    Auth with API key    ${API_KEY}
    ${associations}=    List associations    CONTACT    ${OBJECT_ID}    COMPANY
    Should Be Equal As Strings    ${COMPANY_ID}    ${{$associations[0].id}}

List company associations for list of contacts returns companies
    Auth with API key    ${API_KEY}
    ${associations}=    List associations    CONTACT    ${OBJECT_IDS}    COMPANY
    FOR    ${id}    ${associated_objs}    IN    &{associations}
        ${associated_ids}=    Evaluate    [o.id for o in $associated_objs]
        List should contain value    ${associated_ids}    ${EXPECTED_ASSOCIATION_MAP}[${id}]
    END

Retrieve Custom Object Using Custom ID Returns Object
    Auth with API key    ${API_KEY}
    ${custom_object}=    Get object    ${CUSTOM_OBJECT_TYPE}    ${CUSTOM_OBJ_ID}
    ...    id_property=${ID_PROPERTY}    properties=${ID_PROPERTY}
    Should Be Equal as Strings    ${CUSTOM_OBJ_ID}    ${custom_object.properties["${ID_PROPERTY}"]}

Search for custom object with natural language returns object
    Auth with API key    ${API_KEY}
    ${custom_objects}=    Search for objects    ${CUSTOM_OBJECT_TYPE}    ${ID_PROPERTY}    EQ    ${CUSTOM_OBJ_ID}
    ...    properties=${ID_PROPERTY}
    Should Be Equal as Strings    ${CUSTOM_OBJ_ID}    ${custom_objects[0].properties["${ID_PROPERTY}"]}

List Deal Pipelines Should Return Default Pipeline
    Auth with API key    ${API_KEY}
    ${pipelines}=    List pipelines    DEALS
    ${pipeline_ids}=    Evaluate    [p.id for p in $pipelines]
    List should contain value    ${pipeline_ids}    default

List Default Deal Pipeline Should Return Default Pipeline
    Auth with API key    ${API_KEY}
    ${default_pipeline}=    Get pipeline    DEALS    default

List Deal Pipeline With Label Should Return Pipeline
    Auth with API key    ${API_KEY}
    ${default_pipeline}=    Get pipeline    DEALS    ${PIPELINE_LABEL}

Get Pipeline Stages For Labeled Pipeline Returns Dictionary In Proper Order
    Auth with API key    ${API_KEY}
    &{stages}=    Get Pipeline Stages    DEALS    ${PIPELINE_LABEL}    use_cache=${False}
    @{stage_labels}=    Get dictionary keys    ${stages}    sort_keys=${False}
    Lists should be equal    ${EXPECTED_STAGE_ORDER}    ${stage_labels}

Check Test Deal Is Currently In Expected Stage
    Auth with API key    ${API_KEY}
    ${current_stage}=    Get current stage of object    DEAL    ${TEST_DEAL}
    Should be equal as strings    ${EXPECTED_STAGE}    ${current_stage}[0]

Get User Returns Expected User
    Auth with token    ${ACCESS_TOKEN}
    ${user}=    Get user    ${USER_ID}
    Should be equal as strings    ${USER_EMAIL}    ${user}[email]

Get Owner by ID Returns Expected Owner
    Auth with API key    ${API_KEY}
    ${owner}=    Get owner by id    ${OWNER_ID}
    Should be equal as strings    ${OWNER_EMAIL}    ${owner.email}

Get Owner of Company Returns Expected Owner
    Auth with API key    ${API_KEY}
    ${extra_properties}=    Create list    hubspot_owner_id
    ${company}=    Get object    COMPANY    ${COMPANY_WITH_OWNER_ID}    properties=${extra_properties}
    ${owner}=    Get owner of object    ${company}
    Should be equal as strings    ${EXPECTED_COMPANY_OWNER}    ${owner.id}

Get Custom Owner Property of Company Returns Expected Owner
    Auth with API key    ${API_KEY}
    ${extra_properties}=    Create list    hubspot_owner_id    ${CUSTOM_OWNER_PROPERTY}
    ${company}=    Get object    COMPANY    ${COMPANY_ID_WITH_CUSTOM_OWNER}    properties=${extra_properties}
    ${owner}=    Get owner of object    ${company}    owner_property=${CUSTOM_OWNER_PROPERTY}
    Should be equal as strings    ${EXPECTED_CUSTOM_OWNER}    ${owner.id}

Induce Rate Limit Error and Ensure Good results
    Auth with API key    ${API_KEY}
    ${contacts}=    Search for objects    CONTACTS    firstname    HAS_PROPERTY    max_results=20
    FOR    ${contact}    IN    @{contacts}
        ${individual_contact}=    Search for objects    CONTACTS    hs_object_id    EQ    ${contact.id}
    END
    ${contacts}=    Search for objects    CONTACTS    firstname    EQ    ${FIRST_NAME}    AND    lastname    EQ
    ...    ${LAST_NAME}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}
    Should Contain Match    ${{[c.properties["lastname"] for c in $contacts]}}    ${LAST_NAME}
    ...    case_insensitive=${True}