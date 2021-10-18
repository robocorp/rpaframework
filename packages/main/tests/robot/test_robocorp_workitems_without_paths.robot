*** Settings ***
Test Setup       Load mock library
Library          OperatingSystem


*** Variables ***
${err_no_input_path}     Can't save an input item without a path defined, use 'RPA_INPUT_WORKITEM_PATH' env for this matter
${err_no_paths}     You must provide a path for at least one of the input or output work items files


*** Keywords ***
Load mock library
    Remove environment variable    RPA_INPUT_WORKITEM_PATH
    Remove environment variable    RPA_OUTPUT_WORKITEM_PATH

    Import library    RPA.Robocorp.WorkItems     default_adapter=FileAdapter
    # Autoload (which is True here) doesn't work since the suite is already started.
    Get Input Work Item  # so we call it explicitly


*** Tasks ***
Try saving items with no paths at all
    Run Keyword And Expect Error    ${err_no_input_path}    Save Work Item

    Create Output Work Item
    Set Work Item Variables    user=Cosmin    mail=cosmin@robocorp.com
    Run Keyword And Expect Error    ${err_no_paths}     Save Work Item
