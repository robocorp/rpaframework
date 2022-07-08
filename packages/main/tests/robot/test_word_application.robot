*** Settings ***
Library         RPA.Word.Application
Force tags      windows  skip
Task Setup      Open Application
Task Teardown   Quit Application

*** Tasks ***
Creating new document
    Create New Document
    Write Text          This is an educational story of company called Robocorp.
    Set Header          11.03.2020
    Set Footer          Author: Mika Hänninen
    Replace Text        educational  inspirational
    Save Document As    robocorp_story.docx
    Export to pdf       robocorp_story.pdf