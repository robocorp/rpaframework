*** Settings ***
Library           RPA.PDF
Library           RPA.FileSystem
Force Tags        pdf
Task Teardown     Close all PDF Documents
Suite Setup
Suite Teardown    Empty Directory  ${WORK_DIR}

*** Variables ***
${WORK_DIR}         ${OUTPUT_DIR}${/}pdftests
${CONTENT}          <h1>Order confirmation</h1><p>Thank you for the order {{name}}</p>
${TEMPLATE}         ${CURDIR}${/}..${/}resources${/}order.template
${NORMAL_PDF}       ${CURDIR}${/}..${/}resources${/}generated.pdf
${INVOICE_PDF}      ${CURDIR}${/}..${/}resources${/}invoice.pdf
${VERO_PDF}         ${CURDIR}${/}..${/}resources${/}vero.pdf
${ENCRYPTED_PDF}    ${CURDIR}${/}..${/}resources${/}encrypted.pdf
${IMAGES_PDF}       ${CURDIR}${/}..${/}resources${/}imagesandtext.pdf
${PDF}              ${WORK_DIR}${/}result.pdf
${UNICODE_PDF}      ${WORK_DIR}${/}öåä.pdf
&{VARS}             name=Robot Generated
...                 email=robot@domain.com
...                 zip=00100
...                 items=Item 1, Item 2
${PASSWORD}         mysecretpassword

*** Tasks ***
Create PDF from HTML content
    [Tags]   html2pdf
    HTML to PDF     ${CONTENT}    ${PDF}    ${VARS}
    ${exists}=               Does File Exist   ${PDF}
    Should Be True           ${exists}

Create PDF from HTML template
    [Tags]   html2pdf
    Template HTML to PDF     ${TEMPLATE}    ${PDF}    ${VARS}
    ${exists}=               Does File Exist   ${PDF}
    Should Be True           ${exists}

Unicode HTML text to PDF
    [Tags]   html2pdf
    HTML To PDF   Hyvää yötä ja nÄkemiin   ${UNICODE_PDF}
    ${exists}=               Does File Exist   ${UNICODE_PDF}
    Should Be True           ${exists}

Missing parameters from HTML to PDF
    Run Keyword And Expect Error   KeyError: 'Required parameter(s) missing for kw: html_to_pdf'  HTML to PDF     content=${CONTENT}
    Run Keyword And Expect Error   KeyError: 'Required parameter(s) missing for kw: html_to_pdf'  HTML to PDF     filename=${PDF}
    Run Keyword And Expect Error   KeyError: 'Required parameter(s) missing for kw: html_to_pdf'  HTML to PDF

Missing parameters from Template HTML to PDF
    Run Keyword And Expect Error   KeyError: 'Required parameter(s) missing for kw: template_html_to_pdf'  Template HTML to PDF     template=${TEMPLATE}
    Run Keyword And Expect Error   KeyError: 'Required parameter(s) missing for kw: template_html_to_pdf'  Template HTML to PDF     filename=${PDF}
    Run Keyword And Expect Error   KeyError: 'Required parameter(s) missing for kw: template_html_to_pdf'  Template HTML to PDF

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
    ${result}=    PDF Decrypt    ${ENCRYPTED_PDF}   ${WORKDIR}${/}now_decrypted.pdf   password=${PASSWORD}
    Should Be True    ${result}

PDF encrypt
    PDF encrypt    ${NORMAL_PDF}    ${WORKDIR}${/}encrypted.pdf    ${PASSWORD}
    ${is_encrypted}=    Is PDF encrypted    ${WORKDIR}${/}encrypted.pdf
    Should Be True    ${is_encrypted}

Get information from PDF
    &{info}=    Get Info    ${IMAGES_PDF}
    Should Be Equal   ${info}[Author]   Mathieu Samyn
    Should Be Equal   ${info}[Title]    EnergyDailyPricesReport-EUROPA

Extract pages from PDF
    Extract pages from pdf    ${VERO_PDF}   ${WORKDIR}${/}extract.pdf  2
    ${pages}=                        Get number of pages    ${WORKDIR}${/}extract.pdf
    Should Be Equal As Integers      ${pages}    1
    &{item}=    Get Text From PDF    ${WORKDIR}${/}extract.pdf
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

Creating file with create_dirs false causes error
    Run Keyword And Expect Error  FileNotFoundError*  Html To Pdf   ${CONTENT}   ${WORK_DIR}${/}newdir${/}out.pdf  create_dirs=${FALSE}
    Run Keyword And Expect Error  FileNotFoundError*  Template Html To Pdf   ${TEMPLATE}   ${WORK_DIR}${/}newdir${/}out.pdf  create_dirs=${FALSE}

Overwriting file with exists_ok false causes error
    Html To Pdf   ${CONTENT}   ${WORK_DIR}${/}test_unique.pdf  exists_ok=${FALSE}
    Run Keyword And Expect Error   FileExistsError*   Html To Pdf   ${CONTENT}   ${WORK_DIR}${/}test_unique.pdf  exists_ok=${FALSE}
    Template Html To Pdf   ${TEMPLATE}   ${WORK_DIR}${/}newdir${/}fromtemplate.pdf  exists_ok=${FALSE}
    Run Keyword And Expect Error   FileExistsError*   Template Html To Pdf   ${TEMPLATE}   ${WORK_DIR}${/}newdir${/}fromtemplate.pdf  exists_ok=${FALSE}

*** Keywords ***
RPA Should Contain
    [Arguments]    ${text}    ${expected}
    Should Contain    ${text}    ${expected}     msg=Did not contain expected text: "${expected}"

RPA Should Not Contain
    [Arguments]    ${text}    ${expected}
    Should Not Contain    ${text}    ${expected}     msg=Did contain unexpected text: "${expected}"
