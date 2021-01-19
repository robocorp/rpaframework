*** Settings ***
Library  RPA.Desktop.Windows
Task Teardown   Close All Applications

*** Keywords ***
Connect to Calculator
    [Arguments]  ${handle}
    Connect By Handle  ${${handle}}  existing_app=True
    Send Keys  %2
    Sleep  2s
    Send Keys  %1
    Sleep  2s

*** Tasks ***
Use calculator
    Open Executable   calc.exe   Calculator
    ${controls}  ${elements}=   Get Window Elements
    FOR  ${elem}  IN  @{elements}
        Run Keyword If  "${elem}[control_type]" == "Window" and "${elem}[name]" == "Calculator" and "${elem}[class_name]" == "ApplicationFrameWindow"
        ...  Connect To Calculator  ${elem}[handle]
    END

Use Notepad
    ${app}=  Open From Search   notepad.exe   Notepad  wildcard=True
    Log Many   ${app}
    Open Dialog       Notepad   wildcard=True  existing_app=True
    ${process}=    Process ID Exists  25032
    Run Keyword If   ${process}  Log  Process exists
