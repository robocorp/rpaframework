*** Settings ***
Library         RPA.RobotLogListener
Library         CustomLibrary
Default Tags    RPA.RobotLogListener


*** Tasks ***
Protecting keywords
    This will not output        # will output because called before register
    Register Protected Keywords    This will not output
    This will not output        # is now registered
    This will output

Protection added within Library
    ${ret}=     CustomLibrary.Special Keyword
    CustomLibrary.Assert Library Special Value  ${ret}

*** Keywords ***
This will not output
    Log   1

This will output
    Log   2
