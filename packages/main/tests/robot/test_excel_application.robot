*** Settings ***
Library         RPA.Excel.Application   autoexit=${False}

Suite Setup         Open Application    visible=${True}     display_alerts=${True}
Suite Teardown      Quit Application

Default Tags      windows   skip  # no Excel app in CI


*** Variables ***
${RESOURCES}    ${CURDIR}${/}..${/}resources
${EXCELS}       ${RESOURCES}${/}excels


*** Tasks ***
Run a macro on a strange name
    # The `-` in the name created issues.
    [Setup]     Open Workbook    ${EXCELS}${/}boldmacro-x.xlsm

    Run Macro    bold_column  # this was failing before (just because of the file name)

    [Teardown]  Close Document
