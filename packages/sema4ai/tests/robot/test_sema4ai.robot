*** Settings ***
Documentation     Robot Framework tests for RPA.Sema4AI against a temporary local workspace.
Library           RPA.Sema4AI    workspace_root=${WORKSPACE}
Library           OperatingSystem
Library           Collections
Suite Setup       Create Directory    ${WORKSPACE}
Suite Teardown    Remove Directory    ${WORKSPACE}    recursive=${TRUE}


*** Variables ***
${WORKSPACE}      ${TEMPDIR}${/}rpa-sema4ai-robot-workspace


*** Test Cases ***
Write Read And List Workspace Files
    ${written}=    Write Workspace File    reports/summary.md    All 12 invoices matched.
    Should Be Equal    ${written}    reports/summary.md
    ${text}=    Read Workspace File    reports/summary.md
    Should Be Equal    ${text}    All 12 invoices matched.
    ${files}=    List Workspace Files    reports    recursive=${FALSE}
    Length Should Be    ${files}    1
    Should Be Equal    ${files}[0][path]    reports/summary.md

Overwrite Can Be Refused
    Write Workspace File    notes.txt    first
    Run Keyword And Expect Error    *already exists*
    ...    Write Workspace File    notes.txt    second    overwrite=${FALSE}
    ${text}=    Read Workspace File    notes.txt
    Should Be Equal    ${text}    first

Move And Delete Workspace Files
    Write Workspace File    inbox/1234.txt    invoice
    Move Workspace File    inbox/1234.txt    processed/1234.txt
    ${moved}=    Workspace File Exists    processed/1234.txt
    Should Be True    ${moved}
    ${deleted}=    Delete Workspace File    processed/1234.txt
    Should Be True    ${deleted}
    ${deleted_again}=    Delete Workspace File    processed/1234.txt    missing_ok=${TRUE}
    Should Not Be True    ${deleted_again}

Paths Cannot Leave The Workspace
    Run Keyword And Expect Error    *'..' segment*
    ...    Write Workspace File    ../outside.txt    nope
    Run Keyword And Expect Error    *absolute*
    ...    Read Workspace File    /etc/hosts

Managed Content Is Protected
    Run Keyword And Expect Error    *platform-managed*
    ...    Write Workspace File    .blockparty/workflows/x.workflow.json    {}

Projects Need The Platform
    Run Keyword And Expect Error    *platform SDK*    List Projects
