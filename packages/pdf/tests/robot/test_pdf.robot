*** Settings ***
Library           Collections
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
    ${text_dict} =    Get Text From Pdf    ${PDF}
    RPA Should Contain    ${text_dict}[${1}]    Thank you for the order

Create PDF from HTML template
    Template HTML to PDF    ${TEMPLATE_ORDER}    ${PDF}    ${VARS_ORDER}
    Should Exist    ${PDF}
    ${text_dict} =    Get Text From Pdf    ${PDF}
    RPA Should Contain    ${text_dict}[${1}]    ${VARS_ORDER}[zip]

Unicode HTML text to PDF
    ${header} =    Set Variable    Hyvääă yötä ja nÄkemiin
    ${VARS_GREETING} =    Create Dictionary    header=${header}
    Template HTML to PDF    ${TEMPLATE_GREETING}    ${UNICODE_PDF}    ${VARS_GREETING}
    Should Exist    ${UNICODE_PDF}
    &{text} =    Get Text From PDF    ${UNICODE_PDF}    1
    RPA Should Contain    ${text}[${1}]    ${header}

Get text from one page
    &{text} =    Get Text From PDF    ${VERO_PDF}    1
    RPA Should Contain    ${text}[${1}]    Omaisuus on saatu
    # The same, but using text boxes now.
    &{text} =    Get Text From PDF    ${VERO_PDF}    1    details=${True}
    @{text_boxes} =    Set Variable    ${text}[${1}]
    RPA Should Contain    ${text_boxes[0].text}    ILMOITA VERKOSSA

Get text from multiple pages as string parameter
    &{text} =    Get Text From PDF    ${VERO_PDF}    1,2
    RPA Should Contain    ${text}[${1}]    Omaisuus on saatu
    RPA Should Contain    ${text}[${2}]    4.5 Omaisuuden hankkimisesta aiheutuneet menot
    RPA Should Not Contain    ${text}[${2}]    Omaisuus on saatu

Get text from multiple pages as list parameter
    @{pages} =    Create List    0    1
    &{text} =    Get Text From PDF    ${VERO_PDF}    ${pages}
    RPA Should Contain    ${text}[${1}]    Omaisuus on saatu

Get text from all pages
    &{text} =    Get Text From PDF    ${VERO_PDF}
    RPA Should Contain    ${text}[${1}]    Omaisuus on saatu
    RPA Should Contain    ${text}[${2}]    4.5 Omaisuuden hankkimisesta aiheutuneet menot

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
    ${items} =    Find Text    text:due date
    Should Be Equal    ${items[0].neighbours}[0]    January 31, 2016

Get text closest to element on the left
    Open PDF    ${INVOICE_PDF}
    ${items} =    Find Text    text:January 31, 2016    pagenum=1    direction=left
    Should Be Equal    ${items[0].neighbours}[0]    Due Date

Get text closest to element using regexp match for value
    Open PDF    ${INVOICE_PDF}
    ${items} =    Find Text    text:Hrs/Qty    pagenum=1    direction=bottom    regexp=\\d+[.]\\d+
    Should Be Equal    ${items[0].neighbours}[0]    1.00

Get figures from PDF
    # In the PDF with images we get one figure for each page and each figure's `top`
    # value is found among the ones below.
    @{expect_tops} =    Create List    ${817}    ${587}
    Open PDF    ${IMAGES_PDF}
    &{figures_by_page} =    Get All Figures
    FOR    ${page}    ${figures}    IN    &{figures_by_page}
        Log    On page: ${page}
        FOR    ${figure_id}    ${figure}    IN    &{figures}
            Log    Figure ID: ${figure_id}
            Log    Figure: ${figure}
            Log    Figure bbox: ${figure.bbox}
            List Should Contain Value    ${expect_tops}    ${figure.top}
        END
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
    ${xml} =    Dump PDF as XML    ${INVOICE_PDF}
    Should Not Be Empty    ${xml}
    ${elem} =    Parse Xml    ${xml}
    Save Xml    ${elem}    ${XML_FILE}
    Should Exist    ${XML_FILE}
    HTML to PDF    ${xml}    ${PDF}
    ${text_dict} =    Get Text From Pdf    ${PDF}
    RPA Should Contain    ${text_dict}[${1}]    test@test.com

Find multiple anchors in multi-page PDF
    Open PDF    ${BOOK_PDF}
    @{all_matches} =    Create List
    ${pages} =    Get Number Of Pages
    FOR    ${page}    IN RANGE    1    ${pages + 1}
        ${matches} =    Find Text    regex:.*Python.*    pagenum=${page}    direction=down
        Append To List    ${all_matches}    @{matches}
    END
    # First text below first "Python" result.
    RPA Should Contain    ${all_matches[0].neighbours[0]}    Simple, Rapid, Effective, and Scalable
    # Second "Python" result's text.
    RPA Should Contain    ${all_matches[1].anchor}    13. A4. Packaging and Distributing Python Projects
    # Paragraph under the last "Python" match.
    RPA Should Contain    ${all_matches[7].neighbours[0]}    Flask is another popular framework

Add watermark into PDF
    ${pdf} =    Set Variable    ${WORK_DIR}${/}receipt.pdf
    Copy File    ${RECEIPT_PDF}    ${pdf}
    Open Pdf    ${pdf}
    Add Watermark Image to PDF    ${ROBOT_PNG}    ${pdf}

Figures to Images
    ${image_filenames}=    Save figures as images
    ...    source_path=${RESOURCE_DIR}${/}imagesandtext.pdf
    ...    images_folder=${WORK_DIR}
    ...    pages=${1}
    ...    file_prefix=Energy-price-developments
    File Should Exist    ${WORK_DIR}${/}Energy-*.bmp

Figure to Image
    Open Pdf    ${RESOURCE_DIR}${/}sparebin-receipt.pdf
    &{figures} =    Get All Figures
    Log Dictionary    ${figures}
    &{figure_dict} =    Get From Dictionary    ${figures}    ${2}    # page 2
    ${figure_obj} =    Get From Dictionary    ${figure_dict}    ${0}    # first object
    Log To Console    ${figure_obj}
    ${image_file_path} =    Save figure as image
    ...    figure=${figure_obj}
    ...    images_folder=${WORK_DIR}
    ...    file_prefix=robot-
    Log To Console    ${image_file_path}
    File Should Exist    ${WORK_DIR}${/}robot-*.bmp
