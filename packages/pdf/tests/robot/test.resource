*** Variables ***
${WORK_DIR}       ${OUTPUT_DIR}${/}pdftests
${RESOURCE_DIR}    ${CURDIR}${/}..${/}resources
${CONTENT}        <h1>Order confirmation</h1><p>Thank you for the order {{name}}</p>
${TEMPLATE_ORDER}       ${RESOURCE_DIR}${/}order.template
${TEMPLATE_GREETING}    ${RESOURCE_DIR}${/}greeting.template
${NORMAL_PDF}       ${RESOURCE_DIR}${/}generated.pdf
${INVOICE_PDF}      ${RESOURCE_DIR}${/}invoice.pdf
${VERO_PDF}         ${RESOURCE_DIR}${/}vero.pdf
${ENCRYPTED_PDF}    ${RESOURCE_DIR}${/}encrypted.pdf
${IMAGES_PDF}       ${RESOURCE_DIR}${/}imagesandtext.pdf
${BOOK_PDF}         ${RESOURCE_DIR}${/}18467.pdf
${RECEIPT_PDF}      ${RESOURCE_DIR}${/}receipt.pdf
${ROBOT_PNG}        ${RESOURCE_DIR}${/}robot.png

${PDF}            ${WORK_DIR}${/}result.pdf
${UNICODE_PDF}    ${WORK_DIR}${/}öåäă.pdf
&{VARS_ORDER}     name=Robot Generated
...               email=robot@domain.com
...               zip=00100
...               items=Item 1, Item 2
${PASSWORD}       mysecretpassword
${XML_FILE}       ${WORK_DIR}${/}result.xml


*** Keywords ***
RPA Should Contain
    [Arguments]    ${text}    ${expected}
    Should Contain    ${text}    ${expected}    msg=Did not contain expected text: "${expected}"

RPA Should Not Contain
    [Arguments]    ${text}    ${expected}
    Should Not Contain    ${text}    ${expected}    msg=Did contain unexpected text: "${expected}"
