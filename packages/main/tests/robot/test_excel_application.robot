*** Settings ***
Library         RPA.Excel.Application

Task Setup      Open Application
Task Teardown   Quit Application

Force tags      windows  skip


*** Variables ***
${RESOURCES}    ${CURDIR}${/}..${/}resources
${EXCELS}       ${RESOURCES}${/}excels


*** Tasks ***
Run Macro On Strange Name
    # The `-` in the name created issues.
    Open Workbook    ${EXCELS}${/}boldmacro-x.xlsm
    Run Macro    bold_column  # this was failing before (just because of the file name)
