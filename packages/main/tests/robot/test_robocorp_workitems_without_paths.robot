*** Settings ***
Test Setup       Load mock library
Library          OperatingSystem


*** Variables ***
${output_items_file}     ${OUTPUT_DIR}/output.json


*** Keywords ***
Load mock library
    Remove environment variable    RPA_INPUT_WORKITEM_PATH
    Remove environment variable    RPA_OUTPUT_WORKITEM_PATH

    Import library    RPA.Robocorp.WorkItems     default_adapter=FileAdapter
    # For some reason autoload (which is True here) doesn't work.
    Get Input Work Item  # so we call it explicitly


*** Tasks ***
Create output item with no paths at all
    Create Output Work Item
    Set Work Item Variables    user=Cosmin    mail=cosmin@robocorp.com
    Save Work Item

    File should exist    ${output_items_file}
    [Teardown]  Remove file     ${output_items_file}
