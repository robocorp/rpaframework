*** Settings ***
Library       RPA.Excel.Files
Force tags    skip

*** Variables ***
${EXCELFILE}        ./resources/orders.xlsx
${EMPTYEXCEL}       ./resouces/empty_orders.xlsx

*** Tasks ***
Reading rows
    ${rows}=        Read rows    ${EXCELFILE}
    Log Many        ${rows}
    ${rows}=        Read rows    ${EXCELFILE}   header=True
    Log Many        ${rows}
    ${rows}=        Read rows    ${EXCELFILE}   header=True   aslist=True
    Log Many        ${rows}
    ${length}=      Get Length   ${rows}
    Log             ${length}
    ${rows}=        Read rows    ${EMPTYEXCEL}   header=True   aslist=True
    ${length}=      Get Length   ${rows}
    Log             ${length}
    ${rows}=        Read rows    ${EMPTYEXCEL}   aslist=True
    ${length}=      Get Length   ${rows}
    Log             ${length}
    ${rows}=        Read rows    ${EMPTYEXCEL}
    ${length}=      Get Length   ${rows}
    Log             ${length}