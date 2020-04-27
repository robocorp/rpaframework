*** Settings ***
Library           RPA.PDF
Library           OperatingSystem
Force Tags        pdf

*** Variables ***
${TEMPLATE}       ${CURDIR}${/}..${/}resources${/}order.template
${NORMAL_PDF}     ${CURDIR}${/}..${/}resources${/}generated.pdf
${ENCRYPTED_PDF}    ${CURDIR}${/}..${/}resources${/}encrypted.pdf
${PDF}            ${OUTPUT_DIR}${/}result.pdf
&{VARS}           name=Robot Generated
...               email=robot@domain.com
...               zip=00100
...               items=Item 1, Item 2

*** Tasks ***
Create PDF from HTML template
    Template HTML to PDF    ${TEMPLATE}    ${PDF}    ${VARS}
    File Should Exist    ${PDF}

Get text from PDF
    &{text}=    Get Text From PDF    0    ${NORMAL_PDF}
    Should Contain    ${text}[${0}]    Robot Generated
    Should Contain    ${text}[${0}]    robot@domain.com
    Should Contain    ${text}[${0}]    00100
    Should Contain    ${text}[${0}]    Item 1, Item 2

Get number of pages
    ${pages}=    Get number of pages    ${NORMAL_PDF}
    Should Be Equal As Integers    ${pages}    1
    Set Source Document    ${NORMAL_PDF}
    Add Pages To Source Document    5    ${NORMAL_PDF}    ${OUTPUT_DIR}${/}/modified.pdf
    ${pages}=    Get number of pages    ${OUTPUT_DIR}${/}modified.pdf
    Should Be Equal As Integers    ${pages}    6

Get named destinations
    @{destinations}=    Get named destinations    ${NORMAL_PDF}

Get XMP metadata
    ${metadata}=    Get XMP metadata    ${NORMAL_PDF}

Get page mode
    ${pagemode}=    Get page mode    ${NORMAL_PDF}

Get page layout
    ${layout}=    Get page layout    ${NORMAL_PDF}
    Should Be Equal    /OneColumn    ${layout}

Get page outlines
    ${outlines}=    Get outlines    ${NORMAL_PDF}

Get form text fields
    ${fields}=    Get form text fields    ${NORMAL_PDF}

Get fields
    ${fields}=    Get fields    ${NORMAL_PDF}    ${OUTPUT_DIR}${/}fields.txt

PDF decryption
    ${isdecrypted}=    Is PDF encrypted    ${NORMAL_PDF}
    Should Not Be True    ${isdecrypted}
    ${result}=    PDF Decrypt    ${NORMAL_PDF}    mysecretpassword
    Should Not Be True    ${result}
    ${result}=    PDF Decrypt    ${ENCRYPTED_PDF}    mysecretpassword
    Should Be True    ${result}

PDF encrypt
    PDF encrypt    ${NORMAL_PDF}    ${OUTPUT_DIR}${/}encrypted.pdf    mysecretpassword
    ${isdecrypted}=    Is PDF encrypted    ${OUTPUT_DIR}${/}encrypted.pdf
    Should Be True    ${isdecrypted}
