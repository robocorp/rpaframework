*** Settings ***
Library   RPA.Cloud.AWS
Force Tags  skip

*** Variables ***
${S3_BUCKET_NAME}   testresources

*** Tasks ***
Start Textract Document Text Detection Job
  Init Textract Client   %{AWS_KEY_ID}   %{AWS_KEY_SECRET}  %{AWS_REGION}
  ${jobid}=  Start Document Text Detection  ${S3_BUCKET_NAME}  document.pdf
  FOR  ${i}  IN RANGE  50
      ${response}  Get Document Text Detection  ${jobid}
      Exit For Loop If   "${response}[JobStatus]" == "SUCCEEDED"
      Sleep  1s
  END

Start Textract Document Analysis Job
  Init Textract Client   %{AWS_KEY_ID}   %{AWS_KEY_SECRET}  %{AWS_REGION}
  ${jobid}=  Start Document Analysis  ${S3_BUCKET_NAME}  document.pdf
  FOR  ${i}  IN RANGE  50
      ${response}  Get Document Analysis  ${jobid}
      Exit For Loop If   "${response}[JobStatus]" == "SUCCEEDED"
      Sleep  1s
  END