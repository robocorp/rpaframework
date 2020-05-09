*** Settings ***
Library           RPA.PDF
Library           RPA.FileSystem
Force Tags        pdf
Task Teardown     Close all PDF Documents

*** Variables ***
${TEMPLATE}         ${CURDIR}${/}..${/}resources${/}order.template
${NORMAL_PDF}       ${CURDIR}${/}..${/}resources${/}generated.pdf
${INVOICE_PDF}      ${CURDIR}${/}..${/}resources${/}invoice.pdf
${VERO_PDF}         ${CURDIR}${/}..${/}resources${/}vero.pdf
${ENCRYPTED_PDF}    ${CURDIR}${/}..${/}resources${/}encrypted.pdf
${IMAGES_PDF}       ${CURDIR}${/}..${/}resources${/}imagesandtext.pdf
${PDF}              ${OUTPUT_DIR}${/}result.pdf
&{VARS}             name=Robot Generated
...                 email=robot@domain.com
...                 zip=00100
...                 items=Item 1, Item 2
${PASSWORD}         mysecretpassword

*** Tasks ***
Create PDF from HTML template
    Template HTML to PDF     ${TEMPLATE}    ${PDF}    ${VARS}
    ${exists}=               Does File Exist   ${PDF}
    Should Be True           ${exists}

Get text from one page
    &{text}=    Get Text From PDF    ${VERO_PDF}    1
    RPA Should Contain        ${text}[${1}].text    Omaisuus on saatu

Get text from multiple pages as string parameter
    &{text}=    Get Text From PDF    ${VERO_PDF}    1,2
    RPA Should Contain        ${text}[${1}].text    Omaisuus on saatu
    RPA Should Contain        ${text}[${2}].text    4.5 Omaisuuden hankkimisesta aiheutuneet menot
    RPA Should Not Contain    ${text}[${2}].text    Omaisuus on saatu

Get text from multiple pages as list parameter
    @{pages}=            Create List    0   1
    &{text}=             Get Text From PDF    ${VERO_PDF}   ${pages}
    RPA Should Contain   ${text}[${1}]    Omaisuus on saatu

Get text from all pages
    &{text}=             Get Text From PDF    ${VERO_PDF}
    RPA Should Contain   ${text}[${1}].text    Omaisuus on saatu
    RPA Should Contain   ${text}[${2}].text    4.5 Omaisuuden hankkimisesta aiheutuneet menot

Get number of pages
    ${pages}=                        Get number of pages    ${NORMAL_PDF}
    Should Be Equal As Integers      ${pages}    1
    ${pages}=                        Get number of pages    ${VERO_PDF}
    Should Be Equal As Integers      ${pages}    2

PDF decrypt
    ${isdecrypted}=    Is PDF encrypted    ${NORMAL_PDF}
    Should Not Be True    ${isdecrypted}
    ${result}=    PDF Decrypt    ${ENCRYPTED_PDF}   ${OUTPUT_DIR}${/}now_decrypted.pdf   password=${PASSWORD}
    Should Be True    ${result}

PDF encrypt
    PDF encrypt    ${NORMAL_PDF}    ${OUTPUT_DIR}${/}encrypted.pdf    ${PASSWORD}
    ${is_encrypted}=    Is PDF encrypted    ${OUTPUT_DIR}${/}encrypted.pdf
    Should Be True    ${is_encrypted}

Get information from PDF
    &{info}=    Get Info    ${IMAGES_PDF}
    Should Be Equal   ${info}[Author]   Mathieu Samyn
    Should Be Equal   ${info}[Title]    EnergyDailyPricesReport-EUROPA

Extract pages from PDF
    Extract pages from pdf    ${VERO_PDF}   ${OUTPUT_DIR}${/}extract.pdf  2
    ${pages}=                        Get number of pages    ${OUTPUT_DIR}${/}extract.pdf
    Should Be Equal As Integers      ${pages}    1
    &{item}=    Get Text From PDF    ${OUTPUT_DIR}${/}extract.pdf
    RPA Should Contain   ${item}[${1}]    4.5 Omaisuuden hankkimisesta aiheutuneet menot

Get text closest to element on the right (default)
    # invoice.pdf
    Open PDF Document    ${INVOICE_PDF}
    ${item}=   Get Value from Anchor  text:due date
    Should Be Equal    ${item.text}   January 31, 2016

Get text closest to element on the left
    # invoice.pdf
    Open PDF Document    ${INVOICE_PDF}
    ${item}=   Get Value from Anchor  text:January 31, 2016   pagenum=1   direction=left
    Should Be Equal    ${item.text}   Due Date

Get text closest to element using regexp match for value
    Open PDF Document    ${INVOICE_PDF}
    ${item}=   Get Value from Anchor  text:Hrs/Qty  pagenum=1  direction=bottom  regexp=\\d+[.]\\d+
    Should Be Equal   ${item.text}  1.00


Get figures from PDF
    [Tags]   skip
    # vero.pdf qrcode
    Open PDF Document    ${VERO_PDF}
    &{figures}=           Get All Figures
    FOR  ${key}   ${figure}   IN   &{FIGURES}
        Log    ${key}
        Log    ${figure}
    END

Get input fields from PDF
    # vero.pdf
    &{fields}=      Get Input Fields  ${VERO_PDF}   replace_no_value=${TRUE}
    Log Many   &{fields}
    Should Be Equal   ${fields}[Paivays][value]         Paivays
    Should Be Equal   ${fields}[Allekirjoitus][value]   Allekirjoitus
    Should Be Equal   ${fields}[Puhelinnumero][value]   Puhelinnumero
    Should Be Equal   ${fields}[Tulosta][value]         Tulosta
    Should Be Equal   ${fields}[Tyhjennä][value]        Tyhjennä

Set field value to PDF
    [Tags]   skip
    # vero.pdf
    Fail

Replace PDF content
    [Tags]   skip
    # invoice.pdf
    Fail

Save current PDF
    [Tags]   skip
    # invoice.pdf & vero.pdf
    Fail

Add image to PDF
    [Tags]   skip
    # invoice.pdf / add image at some coordinates
    Fail

*** Keywords ***
RPA Should Contain
    [Arguments]    ${text}    ${expected}
    Should Contain    ${text}    ${expected}     msg=Did not contain expected text: "${expected}"

RPA Should Not Contain
    [Arguments]    ${text}    ${expected}
    Should Not Contain    ${text}    ${expected}     msg=Did contain unexpected text: "${expected}"
