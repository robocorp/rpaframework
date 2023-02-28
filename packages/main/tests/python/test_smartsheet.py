import os
from pathlib import Path
from json.encoder import JSONEncoder
from requests.models import Response, PreparedRequest

import pytest
from mock import MagicMock, patch
from pytest_mock import MockerFixture

import smartsheet.smartsheet as smart_sdk

OperationResult = smart_sdk.OperationResult
OperationErrorResult = smart_sdk.OperationErrorResult

import RPA.Smartsheet as ss

Smartsheet = ss.Smartsheet

# You can set a personal testing token via the smartsheet_testvars.py file
try:
    from .smartshet_testvars import ACCESS_TOKEN, ORDERS_COLS

    VARS = True
except ImportError:
    VARS = False

# Testing Constants
TEMP_DIR = Path(__file__).parent.parent / "results"

# Mock Constants
MOCK_ACCESS_TOKEN = "smartsheetAccessToken{:0>2}"
"""You must use with .format(<int>)"""
MOCK_SHEET_JSON = {
    "id": 7340596407887748,
    "name": "orders",
    "version": 10,
    "totalRowCount": 9,
    "accessLevel": "OWNER",
    "effectiveAttachmentOptions": [
        "GOOGLE_DRIVE",
        "DROPBOX",
        "BOX_COM",
        "EVERNOTE",
        "ONEDRIVE",
        "LINK",
        "FILE",
        "EGNYTE",
    ],
    "ganttEnabled": False,
    "dependenciesEnabled": False,
    "resourceManagementEnabled": False,
    "resourceManagementType": "NONE",
    "cellImageUploadEnabled": True,
    "userSettings": {"criticalPathEnabled": False, "displaySummaryTasks": True},
    "permalink": "https://app.smartsheet.com/sheets/g4J274W3V7F549FvxPVrrWV3fJGCC9xGqjq9Gqm1",
    "createdAt": "2023-02-17T19:00:58Z",
    "modifiedAt": "2023-02-22T22:46:45Z",
    "isMultiPicklistEnabled": True,
    "columns": [
        {
            "id": 3471889768703876,
            "version": 0,
            "index": 0,
            "title": "Name",
            "type": "TEXT_NUMBER",
            "primary": True,
            "validation": False,
            "width": 144,
        },
        {
            "id": 7975489396074372,
            "version": 0,
            "index": 1,
            "title": "Item",
            "type": "TEXT_NUMBER",
            "validation": False,
            "width": 294,
        },
        {
            "id": 657140001597316,
            "version": 0,
            "index": 2,
            "title": "Zip",
            "type": "TEXT_NUMBER",
            "validation": False,
            "width": 51,
        },
    ],
    "rows": [
        {
            "id": 3218304495249284,
            "rowNumber": 1,
            "expanded": True,
            "createdAt": "2023-02-17T19:00:58Z",
            "modifiedAt": "2023-02-21T21:18:43Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Sol Heaton",
                    "displayValue": "Sol Heaton",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Bolt T-Shirt",
                    "displayValue": "Sauce Labs Bolt T-Shirt",
                },
                {
                    "columnId": 657140001597316,
                    "value": 3695.0,
                    "displayValue": "3695",
                },
            ],
        },
        {
            "id": 7721904122619780,
            "rowNumber": 2,
            "siblingId": 3218304495249284,
            "expanded": True,
            "createdAt": "2023-02-17T19:00:58Z",
            "modifiedAt": "2023-02-17T19:00:58Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Gregg Arroyo",
                    "displayValue": "Gregg Arroyo",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Onesie",
                    "displayValue": "Sauce Labs Onesie",
                },
                {
                    "columnId": 657140001597316,
                    "value": 4418.0,
                    "displayValue": "4418",
                },
            ],
        },
        {
            "id": 2092404588406660,
            "rowNumber": 3,
            "siblingId": 7721904122619780,
            "expanded": True,
            "createdAt": "2023-02-17T19:00:58Z",
            "modifiedAt": "2023-02-17T19:00:58Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Zoya Roche",
                    "displayValue": "Zoya Roche",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Bolt T-Shirt",
                    "displayValue": "Sauce Labs Bolt T-Shirt",
                },
                {
                    "columnId": 657140001597316,
                    "value": 3013.0,
                    "displayValue": "3013",
                },
            ],
        },
        {
            "id": 6596004215777156,
            "rowNumber": 4,
            "siblingId": 2092404588406660,
            "expanded": True,
            "createdAt": "2023-02-17T19:00:58Z",
            "modifiedAt": "2023-02-17T19:00:58Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Gregg Arroyo",
                    "displayValue": "Gregg Arroyo",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Bolt T-Shirt",
                    "displayValue": "Sauce Labs Bolt T-Shirt",
                },
                {
                    "columnId": 657140001597316,
                    "value": 4418.0,
                    "displayValue": "4418",
                },
            ],
        },
        {
            "id": 4344204402091908,
            "rowNumber": 5,
            "siblingId": 6596004215777156,
            "expanded": True,
            "createdAt": "2023-02-17T19:00:58Z",
            "modifiedAt": "2023-02-17T19:00:58Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Camden Martin",
                    "displayValue": "Camden Martin",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Bolt T-Shirt",
                    "displayValue": "Sauce Labs Bolt T-Shirt",
                },
                {
                    "columnId": 657140001597316,
                    "value": 1196.0,
                    "displayValue": "1196",
                },
            ],
        },
        {
            "id": 8847804029462404,
            "rowNumber": 6,
            "siblingId": 4344204402091908,
            "expanded": True,
            "createdAt": "2023-02-17T19:00:58Z",
            "modifiedAt": "2023-02-17T19:00:58Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Zoya Roche",
                    "displayValue": "Zoya Roche",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Fleece Jacket",
                    "displayValue": "Sauce Labs Fleece Jacket",
                },
                {
                    "columnId": 657140001597316,
                    "value": 3013.0,
                    "displayValue": "3013",
                },
            ],
        },
        {
            "id": 262817239787396,
            "rowNumber": 7,
            "siblingId": 8847804029462404,
            "expanded": True,
            "createdAt": "2023-02-17T19:00:58Z",
            "modifiedAt": "2023-02-17T19:00:58Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Zoya Roche",
                    "displayValue": "Zoya Roche",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Onesie",
                    "displayValue": "Sauce Labs Onesie",
                },
                {
                    "columnId": 657140001597316,
                    "value": 3013.0,
                    "displayValue": "3013",
                },
            ],
        },
        {
            "id": 4766416867157892,
            "rowNumber": 8,
            "siblingId": 262817239787396,
            "expanded": True,
            "createdAt": "2023-02-17T19:00:58Z",
            "modifiedAt": "2023-02-17T19:00:58Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Sol Heaton",
                    "displayValue": "Sol Heaton",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Fleece Jacket",
                    "displayValue": "Sauce Labs Fleece Jacket",
                },
                {
                    "columnId": 657140001597316,
                    "value": 3695.0,
                    "displayValue": "3695",
                },
            ],
        },
        {
            "id": 2514617053472644,
            "rowNumber": 9,
            "siblingId": 4766416867157892,
            "expanded": True,
            "createdAt": "2023-02-17T19:00:58Z",
            "modifiedAt": "2023-02-17T19:00:58Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Sol Heaton",
                    "displayValue": "Sol Heaton",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Onesee",
                    "displayValue": "Sauce Labs Onesee",
                },
                {
                    "columnId": 657140001597316,
                    "value": 3695.0,
                    "displayValue": "3695",
                },
            ],
        },
    ],
}


# @skip  # Need to skip if smartsheet_testvars could not be imported
@pytest.mark.skip("Test only used for debugging")
def test_debugging():
    """This test should always be skipped for automated tests."""
    lib = Smartsheet(access_token=ACCESS_TOKEN)
    orders = lib.get_sheet(sheet_name="orders")
    attachments = lib.list_attachments()
    for a in attachments:
        lib.download_attachment(a, TEMP_DIR)


@pytest.fixture
def library() -> Smartsheet:
    return Smartsheet()


@pytest.fixture
def authorized_lib(
    library: Smartsheet, mocker: MockerFixture, iter: int = 1
) -> Smartsheet:
    library.set_access_token(MOCK_ACCESS_TOKEN.format(iter))
    return library


@pytest.fixture
def lib_with_sheet(authorized_lib: Smartsheet, mocker: MockerFixture) -> Smartsheet:
    _patch_response(authorized_lib, mocker, MOCK_SHEET_JSON)
    authorized_lib.get_sheet(7340596407887748)
    return authorized_lib


def _create_json_response(return_value: dict) -> MagicMock:
    mock_response = MagicMock(Response)
    mock_response.status_code = 200
    mock_response.reason = "OK"
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = return_value
    mock_response.text = JSONEncoder().encode(return_value)
    mock_response.content.decode.return_value = mock_response.text
    mock_response.request = MagicMock(PreparedRequest)
    mock_response.request.method = "TEST"
    mock_response.request.url = "TEST"
    mock_response.request.body = None
    return mock_response


def _patch_response(
    library: Smartsheet, mocker: MockerFixture, return_value: dict
) -> MagicMock:
    mock_response = _create_json_response(return_value)
    config = {"return_value": mock_response}
    return mocker.patch.object(library.smart._session, "send", **config)


def _patch_multiple_responses(
    library: Smartsheet, mocker: MockerFixture, mocked_responses: list[MagicMock]
) -> MagicMock:
    config = {"side_effect": mocked_responses}
    return mocker.patch.object(library.smart._session, "send", **config)


def test_authorization(library: Smartsheet, mocker: MockerFixture) -> None:
    mock_client = mocker.patch("RPA.Smartsheet.smart_sdk", autospec=True)

    library.set_access_token(MOCK_ACCESS_TOKEN)

    mock_client.assert_called()


def test_get_application_constants(
    authorized_lib: Smartsheet, mocker: MockerFixture
) -> None:
    expected_response = {"supportedLocales": ["en_US"], "serverVersion": "207.0.0"}
    patch = _patch_response(authorized_lib, mocker, expected_response)

    server_info = authorized_lib.get_application_constants()

    patch.assert_called()
    assert list(server_info.supported_locales) == ["en_US"]


def test_get_me(authorized_lib: Smartsheet, mocker: MockerFixture) -> None:
    expected_response = {
        "id": 123123,
        "email": "markmonkey@robocorp.com",
        "locale": "en_US",
        "timeZone": "US/Pacific",
        "account": {
            "name": "markmonkey@robocorp.com (Developer)",
            "id": 789789,
        },
        "admin": True,
        "licensedSheetCreator": True,
        "groupAdmin": True,
        "resourceViewer": True,
        "alternateEmails": [],
        "sheetCount": 25,
        "lastLogin": "2023-02-28T18:15:56Z",
        "title": "",
        "department": "",
        "company": "",
        "workPhone": "",
        "mobilePhone": "",
        "role": "",
    }
    patch = _patch_response(authorized_lib, mocker, expected_response)

    me = authorized_lib.get_current_user()

    patch.assert_called()
    assert me.email == expected_response["email"]


def test_download_attachment(lib_with_sheet: Smartsheet, mocker: MockerFixture) -> None:
    json_response = {
        "id": 123,
        "name": "my notes.txt",
        "url": "http://localhost",
        "attachmentType": "FILE",
        "mimeType": "text/plain;charset=UTF-8",
        "urlExpiresInMillis": 120000,
        "sizeInKb": 1,
        "parentType": "ROW",
        "parentId": 456,
        "createdAt": "2023-02-22T22:46:44Z",
        "createdBy": {"email": "markmonkey@robocorp.com"},
    }
    _patch_response(lib_with_sheet, mocker, json_response)
    expected_content = b"dummy file content"
    file_response = MagicMock()
    file_response.content = expected_content
    file_response.status_code = 200
    file_response.iter_content.return_value = iter([expected_content])
    mock_get = mocker.patch("smartsheet.attachments.requests.get")
    mock_get.return_value = file_response

    downloaded_file = lib_with_sheet.download_attachment(123, TEMP_DIR)

    assert downloaded_file
    assert downloaded_file.exists()
    assert downloaded_file.read_text() == str(expected_content, "utf8")
