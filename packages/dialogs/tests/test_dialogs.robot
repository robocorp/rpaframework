*** Settings ***
Library    DateTime
Library    RPA.Dialogs

*** Variables ***
@{EMPTY_LIST}

*** Test Cases ***
Failure dialog
    Add icon       Failure
    Add heading    There was an error
    Add text       The assistant failed to login to the Enterprise portal
    Add link       https://robocorp.com/docs    label=Troubleshooting guide
    Run dialog     title=Failure

All elements
    Add heading         An default title
    Add heading         A sized title    size=large

    Add text            Some default text
    Add text            Some sized text    size=small

    Add link            https://www.robocorp.com
    Add link            www.robocorp.com
    Add link            www.robocorp.com    label=Robocorp

    Add image           http://placekitten.com/g/200/300
    Add image           http://placekitten.com/g/800/800
    Add image           http://placekitten.com/g/800/800    width=200
    Add image           ${CURDIR}${/}resources${/}cat.jpeg
    Add file            ${CURDIR}${/}resources${/}file1.txt
    Add file            ${CURDIR}${/}resources${/}file1.txt    label=Textfile

    Add files           ${CURDIR}${/}resources${/}*.txt
    Add files           *.robot

    Add icon            Success
    Add icon            Warning
    Add icon            Failure

    Add text input      text-field-1
    Add text input      text-field-2    label=Text input    placeholder=Text goes here

    Add password input  password-field-1
    Add password input  password-field-2    label=Password input    placeholder=Password goes here

    Add hidden input    hidden-field     Some hidden value

    Add file input      file-field-1
    Add file input      file-field-2    label=File input   source=~/Downloads    destination=/tmp/not-exist
    Add file input      file-field-3    label=File input   source=/home/ossi/Downloads/    multiple=True    file_type=Log files (*.log;*.txt)

    Add drop-down       dropdown-field-1   one,two,three
    Add drop-down       dropdown-field-2   one,two,three    default=three
    Add drop-down       dropdown-field-3   ${EMPTY_LIST}    label=Empty

    Add Date Input      dateinput-field-1
    Add Date Input      dateinput-field-2   default=2021-9-6    label=Join date
    ${date_obj} =       Convert Date    26/04/1993    date_format=%d/%m/%Y    result_format=datetime
    Add Date Input      dateinput-field-3   default=${date_obj}     label=Birthdate

    Add radio buttons   radio-field-1      one,two,three
    Add radio buttons   radio-field-2      one,two,three    default=three
    Add radio buttons   radio-field-3      ${EMPTY_LIST}    label=Empty

    Add checkbox        checkbox-field-1   Checkbox label
    Add checkbox        checkbox-field-2   Checkbox label    default=True

    Add submit buttons  one,two
    Add submit buttons  ${EMPTY_LIST}

    &{result}=    Run dialog
    Log many    &{result}

Multiple dialogs with next button
    Add heading    1/3
    Add text input      text-field-1
    Add dialog next page button         label=next1

    Add heading    2/3
    Add text input      text-field-2
    Add dialog next page button         label=next2

    Add heading    3/3
    Add text input      text-field-3
    Add submit buttons  submit

    ${result}=  Run dialog
    Log many    &{result}

Multiple dialogs
    Add heading    1/3
    Add hidden input    index  1
    ${one}=      Show dialog

    Add heading    2/3
    Add hidden input    index  2
    ${two}=      Show dialog

    Add heading    3/3
    Add hidden input    index  3
    ${three}=    Show dialog

    ${results}=  Wait all dialogs
    FOR    ${result}    IN     @{results}
        Log many    &{result}
    END

Delete confirmation
    ${username}=  Set variable    TestUser
    Add icon      Warning
    Add heading   Delete user ${username}?
    Add submit buttons    buttons=No,Yes    default=Yes
    ${result}=    Run dialog
    IF   $result.submit == "Yes"
        Log    ${username}
    END
