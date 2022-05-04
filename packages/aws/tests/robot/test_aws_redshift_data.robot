*** Settings ***
Library         RPA.Cloud.AWS
Library         String
Library         Collections
Variables       aws_redshift_data_testvars.py


*** Variables ***
${SQL_LIST_TABLES}=         select ejslkerj, table_schema, table_name
...                         from information_schema.tables
...                         where table_schema not in ('information_schema', 'pg_catalog','pg_internal')
...                         and table_type = 'BASE TABLE'
${SQL_INSERT_SAMPLE_DB}=    insert into dev.public.venue (venueid, venuename) values (:id, :name)


*** Test Cases ***
Login to AWS Redshift Cluster
    [Setup]    Init
    ${tables}=    Execute redshift statement    ${SQL_LIST_TABLES}
    Dictionary should contain key    ${tables}[0]    table_name

Insert data into AWS with parameters
    [Setup]    Init
    ${random_id}=    Generate random string    3    [NUMBERS]
    ${random_name}=    Generate random string    25    [LETTERS]
    ${id_param}=    Create dictionary    name=id    value=${random_id}
    ${name_param}=    Create dictionary    name=name    value=${random_name}
    ${param_list}=    Create list    ${id_param}    ${name_param}
    Execute redshift statement    ${SQL_INSERT_SAMPLE_DB}    ${param_list}


*** Keywords ***
Init
    Check If Variable File Exists
    Init redshift data client
    ...    aws_key_id=${AWS_KEY_ID}
    ...    aws_key=${AWS_KEY}
    ...    region=${AWS_REGION}
    ...    cluster_identifier=${TEST_CLUSTER_ID}
    ...    database=${DATABASE_NAME}
    ...    database_user=${DATABASE_USERNAME}

Check If Variable File Exists
    ${result}    ${_}=    Run keyword and ignore error    Variable Should Exist    ${AWS_KEY_ID}
    IF    "${result}" == "FAIL"
        ${message}=    Set variable    No variable file for tests to use, skipping this test.
        Log    ${message}    level=WARN
        Skip    ${message}
    END
