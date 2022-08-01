*** Settings ***
Documentation       API keys and variables must be provided in ``./testvars.py``. These should use a live or
...                 sandbox Hubspot environment to test the API, there is no mocking function.
...
...                 The ``testvars.py`` should be built like so (example values provided, these will
...                 need to be replaced with IDs and data from HubSpot):
...
...                 |    # API key for all tests.
...                 |    API_KEY = "not-a-real-hubspot-api-key"
...                 |    ACCESS_TOKEN = "pat-na1-not-a-real-hubspot-auth-token"
...                 |
...                 |    # Contact/object lookup tests.
...                 |    FIRST_NAME = "John"
...                 |    LAST_NAME = "Smith"
...                 |    FIRST_NAME_2 = "Alice"
...                 |    CONTACT_EMAILS = ["john@example.com", "alice@example.com"]
...                 |    CONTACT_ID = "1234"
...                 |
...                 |    # Get One Object test
...                 |    OBJECT_ID = 4567
...                 |    COMPANY_ID = 123456789
...                 |
...                 |    # Batch tests
...                 |    OBJECT_IDS = [4567, 987654]
...                 |    EXPECTED_ASSOCIATION_MAP = {"4567": "123456789", "65478": "987654321"}
...                 |    EXPECTED_EMAILS = ["john@example.com", "alice@example.com"]
...                 |
...                 |    # Get Custom Object with Custom ID property test
...                 |    CUSTOM_OBJ_ID = "123456-8ef6-4af3-9c10-8798a532f"
...                 |    ID_PROPERTY = "organization_id"
...                 |    CUSTOM_OBJECT_TYPE = "Organization"
...                 |
...                 |    # Pipeline tests.
...                 |    PIPELINE_LABEL = "Self-Service Pipeline"
...                 |    EXPECTED_STAGE_ORDER = (
...                 |    "Free",
...                 |    "Pro",
...                 |    "Closed lost",
...                 |    )
...                 |    TEST_DEAL = 123456789
...                 |    EXPECTED_STAGE = "Contract Signed"
...                 |
...                 |    # User provisioning tests.
...                 |    USER_ID = "2456789"
...                 |    USER_EMAIL = "john@example.com"
...                 |
...                 |    # Owner lookup tests.
...                 |    OWNER_ID = "123654987"
...                 |    OWNER_EMAIL = "john@example.com"
...                 |    COMPANY_WITH_OWNER_ID = "123456789"
...                 |    EXPECTED_COMPANY_OWNER = "987456123"
...                 |
...                 |    CUSTOM_OWNER_PROPERTY = "customer_success_contact"
...                 |    COMPANY_ID_WITH_CUSTOM_OWNER = "123456789"
...                 |    EXPECTED_CUSTOM_OWNER = "123654987"

Library             RPA.Hubspot
Library             Collections
Library             String
Variables           ./hubspot_testvars.py

Force Tags          hubspot


*** Variables ***
${NOT_AUTHENTICATED_ERROR}      STARTS:HubSpotAuthenticationError:
${AUTHENTICATION_FAILED}        HubSpotAuthenticationError: Authentication was not successful.
${HUBSPOT_TYPE_ERROR}           STARTS:HubSpotObjectTypeError:


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
    Run Keyword And Expect Error    ${AUTHENTICATION_FAILED}
    ...    Auth with API key    api_key=123

Search for Contact by First Name Returns Contacts
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${search_object}=    Evaluate
    ...    [{'filters':[{'propertyName':'firstname','operator':'EQ','value':'${FIRST_NAME}'}]}]
    ${contacts}=    Search for objects    CONTACTS    search=${search_object}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}

Search for All Contacts Returns 1000 Contacts
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${search_object}=    Evaluate    [{'filters':[{'propertyName':'firstname','operator':'HAS_PROPERTY'}]}]
    ${contacts}=    Search for objects    CONTACTS    search=${search_object}
    ${length}=    Get Length    ${contacts}
    Should Be Equal As Integers    1000    ${length}

Search for object with natural language returns object
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${contacts}=    Search for objects    CONTACTS    firstname    EQ    ${FIRST_NAME}    AND    lastname    EQ
    ...    ${LAST_NAME}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}
    Should Contain Match    ${{[c.properties["lastname"] for c in $contacts]}}    ${LAST_NAME}
    ...    case_insensitive=${True}

Seach for object using IN operator returns object
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${contacts}=    Search for objects    CONTACTS    email    IN    ${CONTACT_EMAILS}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME_2}
    ...    case_insensitive=${True}

Search for object using BETWEEN operator returns object
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${contacts}=    Search for objects    CONTACTS    hs_object_id    BETWEEN    ${{[$CONTACT_ID,$CONTACT_ID]}}
    Should Contain Match    ${{[c.properties["firstname"] for c in $contacts]}}    ${FIRST_NAME}
    ...    case_insensitive=${True}
    Should Contain Match    ${{[c.properties["lastname"] for c in $contacts]}}    ${LAST_NAME}
    ...    case_insensitive=${True}

Retrieve One Object Using ID Returns Object
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${contact}=    Get object    CONTACT    ${OBJECT_ID}
    Should Be Equal As Strings    ${OBJECT_ID}    ${contact.id}

Retrieve Objects Using IDs Returns Objects
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${contacts}=    Get object    CONTACT    ${OBJECT_IDS}
    FOR    ${obj}    IN    @{contacts}
        List should contain value    ${EXPECTED_EMAILS}    ${obj.properties}[email]
    END

List company associations for contact returns one company
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${associations}=    List associations    CONTACT    ${OBJECT_ID}    COMPANY
    Should Be Equal As Strings    ${COMPANY_ID}    ${{$associations[0].id}}

List company associations for list of contacts returns companies
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${associations}=    List associations    CONTACT    ${OBJECT_IDS}    COMPANY
    FOR    ${id}    ${associated_objs}    IN    &{associations}
        ${associated_ids}=    Evaluate    [o.id for o in $associated_objs]
        List should contain value    ${associated_ids}    ${EXPECTED_ASSOCIATION_MAP}[${id}]
    END

Retrieve Custom Object Using Custom ID Returns Object
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${custom_object}=    Get object    ${CUSTOM_OBJECT_TYPE}    ${CUSTOM_OBJ_ID}
    ...    id_property=${ID_PROPERTY}    properties=${ID_PROPERTY}
    Should Be Equal as Strings    ${CUSTOM_OBJ_ID}    ${custom_object.properties["${ID_PROPERTY}"]}

Search for custom object with natural language returns object
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${custom_objects}=    Search for objects    ${CUSTOM_OBJECT_TYPE}    ${ID_PROPERTY}    EQ    ${CUSTOM_OBJ_ID}
    ...    properties=${ID_PROPERTY}
    Should Be Equal as Strings    ${CUSTOM_OBJ_ID}    ${custom_objects[0].properties["${ID_PROPERTY}"]}

List Deal Pipelines Should Return Default Pipeline
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${pipelines}=    List pipelines    DEALS
    ${pipeline_ids}=    Evaluate    [p.id for p in $pipelines]
    List should contain value    ${pipeline_ids}    default

List Default Deal Pipeline Should Return Default Pipeline
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${default_pipeline}=    Get pipeline    DEALS    default

List Deal Pipeline With Label Should Return Pipeline
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${default_pipeline}=    Get pipeline    DEALS    ${PIPELINE_LABEL}

Get Pipeline Stages For Labeled Pipeline Returns Dictionary In Proper Order
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    &{stages}=    Get Pipeline Stages    DEALS    ${PIPELINE_LABEL}    use_cache=${False}
    @{stage_labels}=    Get dictionary keys    ${stages}    sort_keys=${False}
    Lists should be equal    ${EXPECTED_STAGE_ORDER}    ${stage_labels}

Check Test Deal Is Currently In Expected Stage
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${current_stage}=    Get current stage of object    DEAL    ${TEST_DEAL}
    Should be equal as strings    ${EXPECTED_STAGE}    ${current_stage}[0]

Get User Returns Expected User
    Check If Variable File Exists
    Auth with token    ${ACCESS_TOKEN}
    ${user}=    Get user    ${USER_ID}
    Should be equal as strings    ${USER_EMAIL}    ${user}[email]

Get Owner by ID Returns Expected Owner
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${owner}=    Get owner by id    ${OWNER_ID}
    Should be equal as strings    ${OWNER_EMAIL}    ${owner.email}

Get Owner of Company Returns Expected Owner
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${extra_properties}=    Create list    hubspot_owner_id
    ${company}=    Get object    COMPANY    ${COMPANY_WITH_OWNER_ID}    properties=${extra_properties}
    ${owner}=    Get owner of object    ${company}
    Should be equal as strings    ${EXPECTED_COMPANY_OWNER}    ${owner.id}

Get Custom Owner Property of Company Returns Expected Owner
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${extra_properties}=    Create list    hubspot_owner_id    ${CUSTOM_OWNER_PROPERTY}
    ${company}=    Get object    COMPANY    ${COMPANY_ID_WITH_CUSTOM_OWNER}    properties=${extra_properties}
    ${owner}=    Get owner of object    ${company}    owner_property=${CUSTOM_OWNER_PROPERTY}
    Should be equal as strings    ${EXPECTED_CUSTOM_OWNER}    ${owner.id}

Induce Rate Limit Error and Ensure Good results
    Check If Variable File Exists
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

Create random company
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${random_name}    ${random_description}=    Generate random name and description
    ${new_object}=    Create object    COMPANY    name=${random_name}    description=${random_description}
    Should be equal as strings    ${random_name}    ${new_object.properties}[name]
    Should be equal as strings    ${random_description}    ${new_object.properties}[description]

Set company number of employees to random number
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
    ${random_number}=    Generate random string    3    [NUMBERS]
    ${updated_object}=    Update object    COMPANY    ${COMPANY_ID}    numberofemployees=${random_number}
    Should be equal as integers    ${random_number}    ${updated_object.properties}[numberofemployees]

Create random companies by batch
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
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
    Check If Variable File Exists
    Auth with API key    ${API_KEY}
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


*** Keywords ***
Check If Variable File Exists
    ${result}    ${_}=    Run keyword and ignore error    Variable Should Exist    ${API_KEY}
    IF    "${result}" == "FAIL"
        ${message}=    Set variable    No variable file for tests to use, skipping this test.
        Log    ${message}    level=WARN
        Skip    ${message}
    END

Generate random name and description
    ${random_name}=    Generate random string    8    [LETTERS]
    ${random_description}=    Generate random string    20    chars=\ [LETTERS]
    [Return]    ${random_name}    ${random_description}
