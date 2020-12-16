*** Settings ***
Suite setup     Create mock files
Library         FilePreparer
Library         Process
Library         RPA.FileSystem

*** Variables ***
${MOCK_WORKSPACE}    ${OUTPUT_DIR}${/}workspace

*** Task ***
Test Find Files
    Verify length    3    Find files    *.test
    Verify length    2    Find files    **/*.ext

Test List Files In Directory
    Verify length    0    List files in directory    empty
    Verify length    1    List files in directory    subfolder/first

Test List Directories In Directory
    Verify length    2    List directories in directory    subfolder

Test Log Directory Tree
    # TODO: Test somehow
    Log directory tree

Test Does File Exist
    Verify true     Does file exist    subfolder/second/stuff.ext
    Verify false    Does file exist    subfolder/second/notexist

Test Does File Exist Glob
    Verify true     Does file exist    **/*.ext
    Verify false    Does file exist    **/*.noexist

Test Does File Exist Absolute
    Verify true     Does file exist    ${MOCK_WORKSPACE}/subfolder/second/stuff.ext
    Verify false    Does file exist    ${MOCK_WORKSPACE}/subfolder/second/notexist

Test Does File Not Exist
    Verify true     Does file not exist    subfolder/first/imaginary
    Verify false    Does file not exist    subfolder/first/stuff.ext

Test Does Directory Exist
    Verify true     Does directory exist    another/second
    Verify false    Does directory exist    another/third

Test Does Directory Exist Glob
    Verify true     Does directory exist    */first
    Verify false    Does directory exist    */third

Test Does Directory Not Exist
    Verify true     Does directory not exist    madeup
    Verify false    Does directory not exist    empty

Test Is Directory Empty
    Verify true     Is directory empty    empty
    Verify false    Is directory empty    subfolder

Test Is Directory Not Empty
    Verify true     Is directory not empty    another
    Verify false    Is directory not empty    empty

Test Is File Empty
    Verify true     Is file empty    emptyfile
    Verify false    Is file empty    notemptyfile

Test Is File Not Empty
    Verify true     Is file not empty    notemptyfile
    Verify false    Is file not empty    emptyfile

Test Read File
    Verify equal    some content here    Read file    notemptyfile

Test Read Binary File
    ${expected}=    Evaluate    bytes([0x00, 0x66, 0x6f, 0x6f, 0x00])
    Verify equal    ${expected}    Read binary file    somebytes

Test Create File
    Create file    subfolder/newfile    content=Some content here?
    Verify equal    Some content here?    Read file    subfolder/newfile
    [Teardown]    Run keyword and ignore error    Remove file    subfolder/newfile

Test Create Binary File
    ${content}=    Evaluate    bytes([0x00, 0x66, 0x6f, 0x6f, 0x00])
    Create binary file    binaryblob    content=${content}
    Verify equal    ${content}    Read binary file    binaryblob
    [Teardown]    Run keyword and ignore error    Remove file    binaryblob

Test Append To File
    Touch file    append_target
    Append to file    append_target    First line\n
    Append to file    append_target    Second line
    Verify equal    First line\nSecond line    Read file    append_target
    [Teardown]    Run keyword and ignore error    Remove file    append_target

Test Append To Binary File
    Touch file    append_target
    ${content}=    Evaluate    bytes([0x66, 0x6f, 0x6f])
    Append to binary file    append_target    ${content}
    Append to binary file    append_target    ${content}
    Append to binary file    append_target    ${content}
    Verify equal    foofoofoo    Read file    append_target
    [Teardown]    Run keyword and ignore error    Remove file    append_target

Test Create And Remove Directory
    Create directory    temp_folder
    Create directory    temp_folder/nested/dirs    parents=${TRUE}
    Verify true    Does directory exist    temp_folder/nested/dirs
    Remove directory    temp_folder/nested/dirs
    Verify true    Does directory not exist    temp_folder/nested/dirs
    Verify true    Does directory exist    temp_folder/nested/
    Remove directory    temp_folder    recursive=${TRUE}
    Verify true    Does directory not exist    temp_folder

Test Remove File
    Touch file     wont_be_missed
    Verify true    Does file exist    wont_be_missed
    Remove file    wont_be_missed
    Verify true    Does file not exist    wont_be_missed

Test Remove Unknown File
    Run keyword and expect error    *FileNotFoundError*    Remove file    not-a-file    missing_ok=${FALSE}
    Remove file    not-a-file

Test Remove Files
    Touch file    one.tmp
    Touch file    two.tmp
    Touch file    three.tmp
    Touch file    four.tmp
    Verify length    4    Find files   *.tmp
    Remove files    one.tmp  two.tmp  three.tmp  four.tmp
    Verify length    0    Find files   *.tmp

Test Empty Directory
    Create directory    temp_dir
    Touch file    temp_dir/one
    Touch file    temp_dir/two
    Touch file    temp_dir/three
    Verify length    3    List files in directory    temp_dir
    Empty directory    temp_dir
    Verify length    0    List files in directory    temp_dir
    [Teardown]    Remove directory    temp_dir

Test Copy File
    Copy file    notemptyfile    temptarget
    Verify true    Does file exist    temptarget
    Verify equal   some content here    Read file    temptarget
    [Teardown]    Remove file    temptarget

Test Copy Files
    Create directory    destdir
    Touch file    one.tmp
    Touch file    two.tmp
    Touch file    three.tmp
    ${files}=     Find files   *.tmp
    Copy files    ${files}    destdir
    ${src}=    Find files   *.tmp
    ${dst}=    List files in directory   destdir
    # Compare filenames only, not paths
    ${src}=    Evaluate    [p.name for p in $src]
    ${dst}=    Evaluate    [p.name for p in $dst]
    Length should be    ${src}    3
    Should be equal     ${src}    ${dst}
    [Teardown]    Remove directory    destdir    recursive=${TRUE}

Test Copy Directory
    Copy directory    another    another_copy
    Verify true    Does file exist    another/first/noext
    Verify true    Does file exist    another_copy/first/noext
    [Teardown]    Remove directory    another_copy    recursive=${TRUE}

Test Move File
    Touch file    movable
    Move file    movable    moved
    Verify true    Does file not exist   movable
    Verify true    Does file exist       moved
    [Teardown]    Remove file    moved

Test Move Files
    Create directory    destdir
    Touch file    one.tmp
    Touch file    two.tmp
    Touch file    three.tmp
    ${files}=     Find files   *.tmp
    Move files    ${files}    destdir
    ${src}=    Find files   *.tmp
    ${dst}=    List files in directory   destdir
    Length should be    ${src}    0
    Length should be    ${dst}    3
    [Teardown]    Remove directory    destdir    recursive=${TRUE}

Test Move Directory
    Create directory    movable
    Move directory      movable    moved
    Verify true    Does directory not exist   movable
    Verify true    Does directory exist       moved
    [Teardown]    Remove directory    moved

Test Change File Extension
    Touch file    subfolder/tmpfile.old
    Change file extension    subfolder/tmpfile.old    .new
    Verify true    Does file not exist   subfolder/tmpfile.old
    Verify true    Does file exist       subfolder/tmpfile.new
    [Teardown]    Remove file    subfolder/tmpfile.new

Test Join Path
    Verify equal    ${/}home${/}user${/}folder${/}test${/}file.ext
    ...    Join path    ${/}    home  user  folder  test  file.ext

Test Absolute Path
    Verify equal    ${MOCK_WORKSPACE}${/}subfolder${/}first${/}stuff.ext
    ...    Absolute path    subfolder/first/stuff.ext

Test Normalize Path
    Verify equal    subfolder${/}stuff.ext
    ...    Normalize path    subfolder/first/../second/../third/fourth/../../stuff.ext
    Verify equal    stuff.ext
    ...    Normalize path    stuff.ext
    Verify equal    ${/}home${/}user${/}stuff${/}filename
    ...    Normalize path    ${/}home${/}user${/}stuff${/}.${/}filename

Test Get File Name
    Verify equal    stuff.ext
    ...    Get file name    subfolder/first/stuff.ext

Test Get File Extension
    ${result}=    Get file extension    subfolder/first/stuff.ext
    Should be equal    ${result}    .ext
    ${result}=    Get file extension    another/first/noext
    Should be equal    ${result}    ${EMPTY}

Test Get File Modified Date
    ${before}=    Get file modified date   another/second/one
    Touch file    another/second/one
    ${after}=    Get file modified date   another/second/one
    Should be true    0.0 < (${after} - ${before}) < 10.0

Test Get File Creation Date
    ${now}=    Evaluate    time.time()    time
    ${result}=    Get file creation date   subfolder/first/stuff.ext
    Should be true    0.0 < (${now} - ${result}) < 10.0

Test Get File Size
    ${result}=   Get file size    notemptyfile
    Should be equal as integers    ${result}    17
    ${result}=   Get file size    emptyfile
    Should be equal as integers    ${result}    0

Test Get File Owner
    ${result}=    Get file owner    notemptyfile
    Should not be empty    ${result}

Test Wait Until Created
    [Tags]   skip
    Execute deferred    touch will_exist    timeout=1.0
    Run keyword and expect error    *TimeoutException*    Wait until created    will_exist    timeout=0.5
    Wait until created    will_exist    timeout=1.0
    [Teardown]    Remove file    will_exist

Test Wait Until Removed
    Touch file   will_be_removed
    Execute deferred    rm will_be_removed    timeout=2.0
    Run keyword and expect error    *TimeoutException*    Wait until removed    will_be_removed    timeout=0.5
    Wait until removed    will_be_removed    timeout=4.0
    [Teardown]    Run keyword and ignore error    Remove file    will_be_removed

Test Wait Until Modified
    [Tags]    posix
    Touch file    will_be_modified
    Execute deferred    touch will_be_modified    timeout=2.0
    Run keyword and expect error    *TimeoutException*    Wait until modified    will_be_modified    timeout=0.5
    Wait until modified    will_be_modified    timeout=4.0
    [Teardown]    Remove file    will_be_modified

Test Run Keyword If File Exists
    Set test variable    ${value}    Before condition
    Run keyword if file exists    sorted1.test
    ...    Set test variable    \${value}    After condition
    Should be equal    ${value}    After condition

*** Keywords ***
Create mock files
    Prepare Files For Tests   root=${MOCK_WORKSPACE}

Execute deferred
    [Arguments]    ${command}    ${timeout}
    Evaluate    threading.Timer(${timeout}, lambda os=os: os.system("${command}")).start()    modules=threading,os

Verify true
    [Arguments]    ${keyword}    @{args}
    ${result}=    Run keyword    ${keyword}    @{args}
    Should be true    ${result}

Verify false
    [Arguments]    ${keyword}    @{args}
    ${result}=    Run keyword    ${keyword}    @{args}
    Should not be true    ${result}

Verify length
    [Arguments]    ${length}    ${keyword}    @{args}
    ${result}=    Run keyword    ${keyword}    @{args}
    Length should be    ${result}    ${length}

Verify equal
    [Arguments]    ${value}    ${keyword}    @{args}
    ${result}=    Run keyword    ${keyword}    @{args}
    Should be equal   ${result}    ${value}
