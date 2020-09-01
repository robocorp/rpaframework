*** Settings ***
Suite Setup   Create mock files
Force Tags    ArchiveLibrary
Library  RPA.FileSystem
Library  FilePreparer
Library  OperatingSystem  WITH NAME  OS
Library  RPA.Archive

*** Variables ***
${MOCK_WORKSPACE}    ${OUTPUT_DIR}${/}workspace_for_archive
${RESOURCE_DIR}      .${/}..${/}..${/}resources
${TEST_ZIP_ARCHIVE}  ${CURDIR}${/}archive.zip

*** Keywords ***
Listing package files
    [Arguments]   ${packagename}
    @{files}   List archive   ${packagename}
    FOR  ${file}  IN  @{files}
      Log Many  ${file}
    END

Create mock files
    Prepare Files For Tests   root=${MOCK_WORKSPACE}

*** Tasks ***
Create ZIP archive from folder
    Archive Folder With Zip   ${MOCK_WORKSPACE}   ${TEST_ZIP_ARCHIVE}
    File Should Not Be Empty  ${TEST_ZIP_ARCHIVE}
    [Teardown]   OS.Remove File  ${TEST_ZIP_ARCHIVE}

Create TAR archive from folder
    Archive Folder With Tar   ${MOCK_WORKSPACE}   ${CURDIR}${/}archive.tar
    File Should Not Be Empty  ${CURDIR}${/}archive.tar
    [Teardown]   OS.Remove File  ${CURDIR}${/}archive.tar

Create TAR.GZ archive from folder
    Archive Folder With Tar   ${MOCK_WORKSPACE}   ${CURDIR}${/}archive.tar.gz
    File Should Not Be Empty  ${CURDIR}${/}archive.tar.gz
    [Teardown]   OS.Remove File  ${CURDIR}${/}archive.tar.gz

Create archive with file pattern
    Archive Folder With Zip   ${MOCK_WORKSPACE}   ${TEST_ZIP_ARCHIVE}  include=*.test
    File Should Not Be Empty  ${TEST_ZIP_ARCHIVE}
    [Teardown]   OS.Remove File  ${TEST_ZIP_ARCHIVE}

Create archive recursively
    Archive Folder With Zip   ${MOCK_WORKSPACE}   ${TEST_ZIP_ARCHIVE}  recursive=True
    File Should Not Be Empty  ${TEST_ZIP_ARCHIVE}
    [Teardown]   OS.Remove File  ${TEST_ZIP_ARCHIVE}

Create archive with all options
    Archive Folder With Zip   ${MOCK_WORKSPACE}   ${TEST_ZIP_ARCHIVE}  include=*.test  exclude=/.*  recursive=True
    File Should Not Be Empty  ${TEST_ZIP_ARCHIVE}
    [Teardown]   OS.Remove File  ${TEST_ZIP_ARCHIVE}

Add files into archive
    Archive Folder With Zip   ${MOCK_WORKSPACE}   ${TEST_ZIP_ARCHIVE}   include=*.test
    ${size1}                  OS.Get File Size    ${TEST_ZIP_ARCHIVE}
    Add To Archive            notemptyfile        ${TEST_ZIP_ARCHIVE}
    ${size2}                  OS.Get File Size    ${TEST_ZIP_ARCHIVE}
    Should Be True            ${size2} > ${size1}
    [Teardown]   OS.Remove File  ${TEST_ZIP_ARCHIVE}

List archive files
    @{files}  List archive    ${RESOURCE_DIR}${/}testarchive.zip
    Length Should Be   ${files}   6

Get archive info
    &{info}  Get Archive Info          ${RESOURCE_DIR}${/}testarchive.tar
    Log Many  ${info}
    Should Contain   ${info}[filename]   testarchive.tar
    Should Be Equal  ${info}[size]       ${300032}

Extract files from tar archive
    [Setup]   OS.Create Directory      extraction
    Extract Archive   ${RESOURCE_DIR}${/}testarchive.tar  extraction
    OS.Directory Should Not Be Empty   extraction
    ${count}        OS.Count Files In Directory         extraction
    Should Be Equal    ${count}   ${6}
    [Teardown]  OS.Remove Directory    extraction  ${TRUE}

Extract selected file from tar archive
    [Setup]   OS.Create Directory      extraction
    @{files}  Create List              example.xlsx
    Extract Archive   ${RESOURCE_DIR}${/}testarchive.tar  extraction  ${files}
    OS.Directory Should Not Be Empty   extraction
    ${count}        OS.Count Files In Directory         extraction
    Should Be Equal    ${count}   ${1}
    [Teardown]  OS.Remove Directory    extraction  ${TRUE}

Extract files from tar.gz archive
    [Setup]   OS.Create Directory      extraction
    Extract Archive   ${RESOURCE_DIR}${/}testarchive.tar.gz  extraction
    OS.Directory Should Not Be Empty   extraction
    ${count}        OS.Count Files In Directory         extraction
    Should Be Equal    ${count}   ${6}
    [Teardown]  OS.Remove Directory    extraction  ${TRUE}

Extract selected file from tar.gz archive
    [Setup]   OS.Create Directory      extraction
    @{files}  Create List              example.xlsx
    Extract Archive   ${RESOURCE_DIR}${/}testarchive.tar.gz  extraction  ${files}
    OS.Directory Should Not Be Empty   extraction
    ${count}        OS.Count Files In Directory         extraction
    Should Be Equal    ${count}   ${1}
    [Teardown]  OS.Remove Directory    extraction  ${TRUE}

Extract all files from zip archive
    [Setup]   OS.Create Directory      extraction
    Extract Archive   ${RESOURCE_DIR}${/}testarchive.zip  extraction
    OS.Directory Should Not Be Empty   extraction
    ${count}        OS.Count Files In Directory         extraction
    Should Be Equal    ${count}   ${6}
    [Teardown]  OS.Remove Directory    extraction  ${TRUE}

Extract selected files from zip archive
    [Setup]   OS.Create Directory      extraction
    @{files}  Create List              approved.png  example.xlsx   invoice.pdf
    Extract Archive   ${RESOURCE_DIR}${/}testarchive.zip  extraction   ${files}
    OS.Directory Should Not Be Empty   extraction
    ${count}        OS.Count Files In Directory         extraction
    Should Be Equal    ${count}   ${3}
    [Teardown]  OS.Remove Directory    extraction  ${TRUE}

Extract single file from tar archive
    [Setup]   OS.Create Directory      extraction
    Extract File From Archive          approved.png  ${RESOURCE_DIR}${/}testarchive.tar  extraction
    OS.Directory Should Not Be Empty   extraction
    ${count}        OS.Count Files In Directory         extraction
    Should Be Equal    ${count}   ${1}
    OS.File Should Exist   extraction${/}approved.png
    [Teardown]  OS.Remove Directory    extraction  ${TRUE}

Extract single file from tar.gz archive
    [Setup]   OS.Create Directory      extraction
    Extract File From Archive          approved.png  ${RESOURCE_DIR}${/}testarchive.tar.gz  extraction
    OS.Directory Should Not Be Empty   extraction
    ${count}        OS.Count Files In Directory         extraction
    Should Be Equal    ${count}   ${1}
    OS.File Should Exist   extraction${/}approved.png
    [Teardown]  OS.Remove Directory    extraction  ${TRUE}

Extract single file from zip archive
    [Setup]   OS.Create Directory      extraction
    Extract File From Archive          approved.png  ${RESOURCE_DIR}${/}testarchive.zip  extraction
    OS.Directory Should Not Be Empty   extraction
    ${count}        OS.Count Files In Directory         extraction
    Should Be Equal    ${count}   ${1}
    OS.File Should Exist   extraction${/}approved.png
    [Teardown]  OS.Remove Directory    extraction  ${TRUE}
