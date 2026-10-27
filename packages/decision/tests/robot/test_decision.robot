*** Settings ***
Documentation     Robot Framework tests for RPA.Decision using an offline fake model.
Library           RPA.Decision    threshold=0.8
Library           Collections
Variables         ../resources/fake_model.py
Suite Setup       Set Decision Backend    ${FAKE_MODEL}


*** Variables ***
${INVOICE}        Please find attached invoice 1234, due in 14 days.
${REMINDER}       This is a friendly reminder that your payment is overdue.


*** Test Cases ***
Decide picks an option and exposes probabilities
    ${result}=    Decide    ${INVOICE}
    ...    question=What kind of document is this?
    ...    options=invoice=A request for payment,reminder,other
    Should Be Equal    ${result.choice}    invoice
    Should Be Equal    ${result}[choice]    invoice
    Should Be True    ${result.confidence} > 0.8
    Dictionary Should Contain Key    ${result.probabilities}    reminder
    Should Be Equal As Strings    ${result}    invoice

Decide Or Escalate fails loudly on low confidence
    TRY
        Decide Or Escalate    totally unrelated text
        ...    question=What kind of document is this?
        ...    options=a,b,c,d,e,f,g,h
        ...    threshold=0.95
        Fail    Expected LowConfidenceError
    EXCEPT    LowConfidenceError*    type=glob    AS    ${error}
        Should Contain    ${error}    below threshold
    END

Check works as a boolean in IF
    ${verdict}=    Check    I would like a refund for this    question=Does the writer ask for a refund?
    IF    ${verdict}
        Log    refund requested
    ELSE
        Fail    Expected a positive verdict
    END
    Should Be True    ${verdict.probability} >= 0.5

Score places text on a rubric
    ${tone}=    Score    ${REMINDER}    question=How urgent is the tone?    levels=Relaxed,Firm,Threatening
    Should Be Equal As Integers    ${tone.level}    1
    Should Be Equal    ${tone.label}    Firm

Ask several questions in one call
    &{kind}=    Create Dictionary    type=choice    question=What is this?    options=invoice,reminder,other
    &{refund}=    Create Dictionary    type=check    question=Refund requested?
    &{questions}=    Create Dictionary    kind=${kind}    refund=${refund}
    ${answers}=    Ask Questions    ${REMINDER}    ${questions}
    Should Be Equal    ${answers}[kind][choice]    reminder
    Should Not Be True    ${answers}[refund]

Audit log records every decision
    Clear Decision Audit Log
    Decide    ${INVOICE}    question=What?    options=invoice,other
    Check    ${INVOICE}    question=Refund?
    ${log}=    Get Decision Audit Log
    Length Should Be    ${log}    2
    Should Be Equal    ${log}[0][kind]    choice
    Should Be Equal    ${log}[0][answer]    invoice
    ${path}=    Save Decision Audit Log    ${OUTPUT_DIR}${/}decisions.jsonl
    File Should Exist    ${path}

Replay backend reproduces recorded decisions
    Clear Decision Audit Log
    Decide    ${INVOICE}    question=Replay me    options=invoice,other
    ${path}=    Save Decision Audit Log    ${OUTPUT_DIR}${/}replay.jsonl
    Set Decision Backend    replay    path=${path}
    ${result}=    Decide    something else entirely    question=Replay me    options=invoice,other
    Should Be Equal    ${result.choice}    invoice
    [Teardown]    Set Decision Backend    ${FAKE_MODEL}


*** Keywords ***
File Should Exist
    [Arguments]    ${path}
    ${exists}=    Evaluate    __import__('os').path.exists($path)
    Should Be True    ${exists}
