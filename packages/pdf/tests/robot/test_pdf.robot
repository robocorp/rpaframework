*** Settings ***
Library           OperatingSystem
Library           RPA.PDF
Library           XML
Resource          test.resource
Task Teardown     Close all PDFs
Suite Teardown    Empty Directory    ${WORK_DIR}


*** Tasks ***
Create PDF from HTML content
    HTML to PDF    ${CONTENT}    ${PDF}
    Should Exist    ${PDF}
    ${text_dict} =   Get Text From Pdf   ${PDF}
    RPA Should Contain    ${text_dict}[${1}]     Thank you for the order

Create PDF from HTML template
    Template HTML to PDF    ${TEMPLATE_ORDER}    ${PDF}    ${VARS_ORDER}
    Should Exist    ${PDF}
    ${text_dict} =   Get Text From Pdf   ${PDF}
    RPA Should Contain    ${text_dict}[${1}]     ${VARS_ORDER}[zip]

Unicode HTML text to PDF
    ${VARS_GREETING} =    Create Dictionary    header=Hyvää yötä ja nÄkemiin
    Template HTML to PDF    ${TEMPLATE_GREETING}    ${UNICODE_PDF}    ${VARS_GREETING}
    Should Exist    ${UNICODE_PDF}

Get text from one page
    &{text} =    Get Text From PDF    ${VERO_PDF}    1
    RPA Should Contain    ${text}[${1}].text    Omaisuus on saatu

Get text from multiple pages as string parameter
    &{text} =    Get Text From PDF    ${VERO_PDF}    1,2
    RPA Should Contain    ${text}[${1}].text    Omaisuus on saatu
    RPA Should Contain    ${text}[${2}].text    4.5 Omaisuuden hankkimisesta aiheutuneet menot
    RPA Should Not Contain    ${text}[${2}].text    Omaisuus on saatu

Get text from multiple pages as list parameter
    @{pages} =    Create List    0    1
    &{text} =    Get Text From PDF    ${VERO_PDF}    ${pages}
    RPA Should Contain    ${text}[${1}]    Omaisuus on saatu

Get text from all pages
    &{text} =    Get Text From PDF    ${VERO_PDF}
    RPA Should Contain    ${text}[${1}].text    Omaisuus on saatu
    RPA Should Contain    ${text}[${2}].text    4.5 Omaisuuden hankkimisesta aiheutuneet menot

Get number of pages
    ${pages} =    Get number of pages    ${NORMAL_PDF}
    Should Be Equal As Integers    ${pages}    1
    ${pages} =    Get number of pages    ${VERO_PDF}
    Should Be Equal As Integers    ${pages}    2

PDF decrypt
    ${isdecrypted} =    Is PDF encrypted    ${NORMAL_PDF}
    Should Not Be True    ${isdecrypted}
    ${result} =    Decrypt PDF    ${ENCRYPTED_PDF}    ${WORKDIR}${/}now_decrypted.pdf    password=${PASSWORD}
    Should Be True    ${result}

PDF encrypt
    Encrypt PDF    ${NORMAL_PDF}    ${WORKDIR}${/}encrypted.pdf    ${PASSWORD}
    ${is_encrypted} =    Is PDF encrypted    ${WORKDIR}${/}encrypted.pdf
    Should Be True    ${is_encrypted}

Get information from PDF
    &{info} =    Get PDF Info    ${IMAGES_PDF}
    Should Be Equal    ${info}[Author]    Mathieu Samyn
    Should Be Equal    ${info}[Title]    EnergyDailyPricesReport-EUROPA

Extract pages from PDF
    Extract pages from pdf    ${VERO_PDF}    ${WORKDIR}${/}extract.pdf    2
    ${pages} =    Get number of pages    ${WORKDIR}${/}extract.pdf
    Should Be Equal As Integers    ${pages}    1
    &{item} =    Get Text From PDF    ${WORKDIR}${/}extract.pdf
    RPA Should Contain    ${item}[${1}]    4.5 Omaisuuden hankkimisesta aiheutuneet menot

Get text closest to element on the right (default)
    Open PDF    ${INVOICE_PDF}
    ${item} =    Find Text    text:due date
    Should Be Equal    ${item.text}    January 31, 2016

Get text closest to element on the left
    Open PDF    ${INVOICE_PDF}
    ${item} =    Find Text    text:January 31, 2016    pagenum=1    direction=left
    Should Be Equal    ${item.text}    Due Date

Get text closest to element using regexp match for value
    Open PDF    ${INVOICE_PDF}
    ${item} =    Find Text    text:Hrs/Qty    pagenum=1    direction=bottom    regexp=\\d+[.]\\d+
    Should Be Equal    ${item.text}    1.00

Get figures from PDF
    Open PDF    ${VERO_PDF}
    &{figures} =    Get All Figures
    FOR    ${key}    ${figure}    IN    &{FIGURES}
        Log    ${key}
        Log    ${figure}
    END

Get input fields from PDF
    # vero.pdf
    &{fields} =    Get Input Fields    ${VERO_PDF}    replace_no_value=${TRUE}
    Log Many    &{fields}
    Should Be Equal    ${fields}[Paivays][value]    Paivays
    Should Be Equal    ${fields}[Allekirjoitus][value]    Allekirjoitus
    Should Be Equal    ${fields}[Puhelinnumero][value]    Puhelinnumero
    Should Be Equal    ${fields}[Tulosta][value]    Tulosta
    Should Be Equal    ${fields}[Tyhjennä][value]    Tyhjennä

Adding Files to PDF
    ${files} =    Create List
    ...    ${RESOURCE_DIR}${/}big_nope.png
    ...    ${RESOURCE_DIR}${/}approved.png
    ...    ${RESOURCE_DIR}${/}vero.pdf
    Add Files To PDF    ${files}    ${WORK_DIR}${/}composed.pdf

XML Dumping And Parsing
    ${xml} =     Dump PDF as XML    ${INVOICE_PDF}
    Should Not Be Empty    ${xml}
    ${elem} =    Parse Xml    ${xml}
    Save Xml    ${elem}    ${XML_FILE}
    Should Exist    ${XML_FILE}
    HTML to PDF    ${xml}    ${PDF}
    ${text_dict} =   Get Text From Pdf   ${PDF}
    RPA Should Contain    ${text_dict}[${1}]     t e s t @ t e s t . c o m
