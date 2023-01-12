*** Settings ***
Documentation       Run real tests in a live HubSpot sandbox as there's no mocking
...     functionality available. Tests configuration is placed under the
...     HubspotTestvars.py variables file, which relies on a 'HUBSPOT_TOKEN' env var to
...     be set in order to get authorized into the API.

Library             Collections
Library             RPA.Hubspot
Library             String

Variables           ../resources/config/HubspotTestvars.py
Task Setup          Token Auth
Force Tags          hubspot


*** Variables ***
${NOT_AUTHENTICATED_ERROR}      STARTS:HubSpotAuthenticationError:


*** Keywords ***
Token Auth
    IF   "${ACCESS_TOKEN}" == "not-set"
        Skip    No token set, please provide it with 'HUBSPOT_TOKEN' env var.
    END
    ${status}   ${ret} =    Run Keyword And Ignore Error
    ...     Auth With Token    ${ACCESS_TOKEN}
    IF    "${status}" == "FAIL"
        Skip    Can't authorize with the provided token.
    END

Generate random name and description
    ${random_name}=    Generate random string    8    [LETTERS]
    ${random_description}=    Generate random string    20    chars=\ [LETTERS]
    [Return]    ${random_name}    ${random_description}


*** Tasks ***
Search for objects should fail without authentication
    [Setup]     Log To Console    No auth required

    Run Keyword And Expect Error    ${NOT_AUTHENTICATED_ERROR}
    ...    Search for objects    object_type=CONTACTS

List associations should fail without authentication
    [Setup]     Log To Console    No auth required

    Run Keyword And Expect Error    ${NOT_AUTHENTICATED_ERROR}
    ...    List associations    object_type=contact    object_id=123    to_object_type=company

Get object should fail without authentication
    [Setup]     Log To Console    No auth required

    Run Keyword And Expect Error    ${NOT_AUTHENTICATED_ERROR}
    ...    Get object    object_type=contact    object_id=123

Authentication fails with API key
    [Setup]     Log To Console    No auth required

    Run Keyword And Expect Error    ${NOT_AUTHENTICATED_ERROR}
    ...     Auth With API Key    api_key=123

Search for Contact by First Name Returns Contacts
    ${search_object}=    Evaluate
    ...    [{'filters':[{'propertyName':'firstname','operator':'EQ','value':'${FIRST_NAME}'}]}]
    ${contacts}=    Search for objects    CONTACTS    search=${search_object}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}

Search for All Contacts Returns 1000 Contacts
    ${search_object}=    Evaluate    [{'filters':[{'propertyName':'firstname','operator':'HAS_PROPERTY'}]}]
    ${contacts}=    Search for objects    CONTACTS    search=${search_object}
    ${length}=    Get Length    ${contacts}
    Should Be Equal As Integers    1000    ${length}

Search for object with natural language returns object
    ${contacts}=    Search for objects    CONTACTS    firstname    EQ    ${FIRST_NAME}    AND    lastname    EQ
    ...    ${LAST_NAME}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}
    Should Contain Match    ${{[c.properties["lastname"] for c in $contacts]}}    ${LAST_NAME}
    ...    case_insensitive=${True}

Seach for object using IN operator returns object
    ${contacts}=    Search for objects    CONTACTS    email    IN    ${CONTACT_EMAILS}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME_2}
    ...    case_insensitive=${True}

Search for object using BETWEEN operator returns object
    ${contacts}=    Search for objects    CONTACTS    hs_object_id    BETWEEN    ${{[$CONTACT_ID,$CONTACT_ID]}}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}
    Should Contain Match    ${{[c.properties["lastname"] for c in $contacts]}}    ${LAST_NAME}
    ...    case_insensitive=${True}

Retrieve One Object Using ID Returns Object
    ${contact}=    Get object    CONTACT    ${OBJECT_ID}
    Should Be Equal As Strings    ${OBJECT_ID}    ${contact.id}

Retrieve Objects Using IDs Returns Objects
    ${contacts}=    Get object    CONTACT    ${OBJECT_IDS}
    FOR    ${obj}    IN    @{contacts}
        List should contain value    ${EXPECTED_EMAILS}    ${obj.properties}[email]
    END

List company associations for contact returns one company
    ${associations}=    List associations    CONTACT    ${OBJECT_ID}    COMPANY
    Should Be Equal As Strings    ${COMPANY_ID}    ${{$associations[0].id}}

List company associations for list of contacts returns companies
    ${associations}=    List associations    CONTACT    ${OBJECT_IDS}    COMPANY
    FOR    ${id}    ${associated_objs}    IN    &{associations}
        ${associated_ids}=    Evaluate    [o.id for o in $associated_objs]
        List should contain value    ${associated_ids}    ${EXPECTED_ASSOCIATION_MAP}[${id}]
    END

Retrieve Custom Object Using Custom ID Returns Object
    ${custom_object}=    Get object    ${CUSTOM_OBJECT_TYPE}    ${CUSTOM_OBJ_ID}
    ...    id_property=${ID_PROPERTY}    properties=${ID_PROPERTY}
    Should Be Equal as Strings    ${CUSTOM_OBJ_ID}    ${custom_object.properties["${ID_PROPERTY}"]}

Search for custom object with natural language returns object
    ${custom_objects}=    Search for objects    ${CUSTOM_OBJECT_TYPE}    ${ID_PROPERTY}    EQ    ${CUSTOM_OBJ_ID}
    ...    properties=${ID_PROPERTY}
    Should Be Equal as Strings    ${CUSTOM_OBJ_ID}    ${custom_objects[0].properties["${ID_PROPERTY}"]}

List Deal Pipelines Should Return Default Pipeline
    ${pipelines}=    List pipelines    DEALS
    ${pipeline_ids}=    Evaluate    [p.id for p in $pipelines]
    List should contain value    ${pipeline_ids}    default

List Default Deal Pipeline Should Return Default Pipeline
    ${default_pipeline}=    Get pipeline    DEALS    default

List Deal Pipeline With Label Should Return Pipeline
    ${default_pipeline}=    Get pipeline    DEALS    ${PIPELINE_LABEL}

Get Pipeline Stages For Labeled Pipeline Returns Dictionary In Proper Order
    &{stages}=    Get Pipeline Stages    DEALS    ${PIPELINE_LABEL}    use_cache=${False}
    @{stage_labels}=    Get dictionary keys    ${stages}    sort_keys=${False}
    Lists should be equal    ${EXPECTED_STAGE_ORDER}    ${stage_labels}

Check Test Deal Is Currently In Expected Stage
    ${current_stage}=    Get current stage of object    DEAL    ${TEST_DEAL}
    Should be equal as strings    ${EXPECTED_STAGE}    ${current_stage}[0]

Get User Returns Expected User
    ${user}=    Get user    ${USER_ID}
    Should be equal as strings    ${USER_EMAIL}    ${user}[email]

Get Owner by ID Returns Expected Owner
    ${owner}=    Get owner by id    ${OWNER_ID}
    Should be equal as strings    ${OWNER_EMAIL}    ${owner.email}

Get Owner of Company Returns Expected Owner
    ${extra_properties}=    Create list    hubspot_owner_id
    ${company}=    Get object    COMPANY    ${COMPANY_ID_WITH_OWNER}    properties=${extra_properties}
    ${owner}=    Get owner of object    ${company}
    Should be equal as strings    ${EXPECTED_COMPANY_OWNER}    ${owner.id}

Get Custom Owner Property of Company Returns Expected Owner
    ${extra_properties}=    Create list    hubspot_owner_id    ${CUSTOM_OWNER_PROPERTY}
    ${company}=    Get object    COMPANY    ${COMPANY_ID_WITH_CUSTOM_OWNER}    properties=${extra_properties}
    ${owner}=    Get owner of object    ${company}    owner_property=${CUSTOM_OWNER_PROPERTY}
    Should be equal as strings    ${EXPECTED_CUSTOM_OWNER}    ${owner.id}

Induce Rate Limit Error and Ensure Good results
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

Create random company
    ${random_name}    ${random_description}=    Generate random name and description
    ${new_object}=    Create object    COMPANY    name=${random_name}    description=${random_description}
    Should be equal as strings    ${random_name}    ${new_object.properties}[name]
    Should be equal as strings    ${random_description}    ${new_object.properties}[description]

Set company number of employees to random number
    ${random_number}=    Generate random string    3    [NUMBERS]
    ${updated_object}=    Update object    COMPANY    ${COMPANY_ID}    numberofemployees=${random_number}
    Should be equal as integers    ${random_number}    ${updated_object.properties}[numberofemployees]

Create random companies by batch
    Create new batch    COMPANY    CREATE
    ${random_name1}    ${random_description1}=    Generate random name and description
    Add input to batch    name=${random_name1}    description=${random_description1}
    ${random_name2}    ${random_description2}=    Generate random name and description
    Add input to batch    name=${random_name2}    description=${random_description2}
    ${new_companies}=    Execute batch
    ${names}=    Create list    ${random_name1}    ${random_name2}
    ${descriptions}=    Create list    ${random_description1}    ${random_description2}
    FOR    ${company}    IN    @{new_companies}
        Should contain    ${names}    ${company.properties}[name]
        Should contain    ${descriptions}    ${company.properties}[description]
    END

Create two hundred random companies by batch
    Create new batch    COMPANY    CREATE
    ${properties_for_batch}=    Create list
    FOR    ${counter}    IN RANGE    200
        ${random_name}    ${random_description}=    Generate random name and description
        ${properties}=    Create dictionary    name=${random_name}    description=${random_description}
        Append to list    ${properties_for_batch}    ${properties}
    END
    Extend batch with inputs    ${properties_for_batch}
    ${new_companies}=    Execute batch
    ${all_names}=    Evaluate    [p["name"] for p in $properties_for_batch]
    ${all_descriptions}=    Evaluate    [p["description"] for p in $properties_for_batch]
    FOR    ${company}    IN    @{new_companies}
        Should contain    ${all_names}    ${company.properties}[name]
        Should contain    ${all_descriptions}    ${company.properties}[description]
    END
