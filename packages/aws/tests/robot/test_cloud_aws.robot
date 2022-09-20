*** Settings ***
Library         RPA.Cloud.AWS
Force Tags      skip

*** Variables ***
${S3_BUCKET_NAME}  %{AWS_BUCKET=testresources}
${RESOURCES}    ${CURDIR}${/}..${/}resources

*** Keywords ***
Init AWS Services
  Init Textract Client  %{AWS_KEY_ID}  %{AWS_KEY_SECRET}  %{AWS_REGION}
  Init S3 Client  %{AWS_KEY_ID}  %{AWS_KEY_SECRET}  %{AWS_REGION}

Upload Local File To S3
  [Arguments]  ${bucketname}  ${localfilepath}  ${objectname}
  ${resp}=  Upload File  ${bucketname}  ${localfilepath}  ${objectname}
  Log many  ${resp}

Download S3 object to Local File
  [Arguments]  ${bucketname}  ${files}=${NONE}  ${target_directory}=${CURDIR}
  ${count}=  Download Files  ${bucketname}  ${files}  ${target_directory}
  Log To Console  Downloaded ${count} files

Analyze File in S3 storage
  [Arguments]  ${bucketname}  ${objectname}
  ${jobid}  Start Document Analysis  ${bucketname}  ${objectname}
  ${response}  Get Document Analysis  ${jobid}
  ${model}=  Convert Textract Response To Model  ${response}
  FOR  ${page_num}  ${page}  IN ENUMERATE  @{model.pages}
    Log To Console  page num: ${page_num}
    #Log To Console  ${page.tables}
    #  Log Many  ${page.form}
    #  Log Many  ${page}
    #  Log  ${page}
    #  Log  ${page.form}
    #END
  END

*** Test Cases ***
Start Textract Document Text Detection Job
  Init Textract Client  %{AWS_KEY_ID}  %{AWS_KEY_SECRET}  %{AWS_REGION}
  ${jobid}=  Start Document Text Detection  ${S3_BUCKET_NAME}  document.pdf
  FOR  ${i}  IN RANGE  50
    ${response}  Get Document Text Detection  ${jobid}
    Exit For Loop If  "${response}[JobStatus]" == "SUCCEEDED"
    Sleep  1s
  END

Start Textract Document Analysis Job
  Init Textract Client  %{AWS_KEY_ID}  %{AWS_KEY_SECRET}  %{AWS_REGION}
  ${jobid}=  Start Document Analysis  ${S3_BUCKET_NAME}  document.pdf
  FOR  ${i}  IN RANGE  50
    ${response}  Get Document Analysis  ${jobid}
    Exit For Loop If  "${response}[JobStatus]" == "SUCCEEDED"
    Sleep  1s
  END

Longer Textract Document Analysis Job
  Init AWS Services
  Upload Local File To S3  ${analysis_bucket}  ${RESOURCES}${/}NASDAQ_AAPL_2019.pdf  nasdaq_aapl
  Analyze File in S3 storage  ${analysis_bucket}  nasdaq_aapl
