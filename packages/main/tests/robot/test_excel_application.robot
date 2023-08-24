*** Settings ***
Library         OperatingSystem
Library         RPA.Excel.Application   autoexit=${False}

Suite Setup         Open Application    visible=${True}     display_alerts=${True}
Suite Teardown      Quit Application

Default Tags      windows   skip  # no Excel app in CI


*** Variables ***
${RESOURCES}    ${CURDIR}${/}..${/}resources
${EXCELS}       ${RESOURCES}${/}excels
${RESULTS}      ${CURDIR}${/}..${/}results


*** Tasks ***
Run a macro on a strange name
    # The `-` in the name created issues.
    [Setup]     Open Workbook    ${EXCELS}${/}boldmacro-x.xlsm

    Run Macro    bold_column  # this was failing before (just because of the file name)
    ${out_pdf} =    Set Variable    ${RESULTS}${/}boldmacro-x.pdf
    Export As PDF   ${out_pdf}
    File Should Exist   ${out_pdf}

    [Teardown]  Close Document
