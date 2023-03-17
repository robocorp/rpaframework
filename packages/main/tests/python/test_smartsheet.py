import os
from itertools import chain
from json.encoder import JSONEncoder
from pathlib import Path
from typing import Iterable, List, Union

import pytest
import smartsheet.smartsheet as smart_sdk
from mock import MagicMock, patch
from pytest_mock import MockerFixture
from requests.models import PreparedRequest, Response

OperationResult = smart_sdk.OperationResult
OperationErrorResult = smart_sdk.OperationErrorResult

import RPA.Smartsheet as ss
from RPA.Tables import Table

Smartsheet = ss.Smartsheet

# You can set a personal testing token via the smartsheet_testvars.py file
try:
    from .smartsheet_testvars import ACCESS_TOKEN

    VARS = True
except ImportError:
    VARS = False

# Import mock data
from .smartsheet_vars import (
    ITEM_COLUMN_ID,
    MOCK_ACCESS_TOKEN,
    MOCK_IMAGE_ATTACHMENT,
    MOCK_SHEET_JSON,
    MOCK_TEXT_ATTACHMENT,
    MOCKED_ADD_ROW_SUCCESS,
    MOCKED_ATTACHMENT_LIST,
    MOCKED_CREATE_SHEET_SUCCESS,
    MOCKED_ROW,
    MOCKED_ROW_ATTACHMENTS,
    MOCKED_ROW_NO_ATTACHMENTS,
    MOCKED_SEARCH_RESULTS,
    MOCKED_UPDATE_ROW_SUCCESS,
    NAME_COLUMN_ID,
    NEW_ROWS,
    NEW_SHEET_COLUMNS,
    NEW_SHEET_NAME,
    UPDATED_ROW_1,
    UPDATED_ROWS,
    ZIP_COLUMN_ID,
)

# Testing Constants
TEMP_DIR = Path(__file__).parent.parent / "results"


# Need to skip if smartsheet_testvars could not be imported
@pytest.mark.skip("Test only used for debugging")
def test_debugging():
    """This test should always be skipped for automated tests."""
    lib = Smartsheet(access_token=ACCESS_TOKEN)
    orders = lib.get_sheet(sheet_name="orders", native=True)
    revisions = lib.get_cell_history(row=orders.rows[0], column=orders.columns[0])
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
    authorized_lib.get_sheet(7340596407887748, include="rowId")
    return authorized_lib


def _create_json_response(return_value: dict) -> MagicMock:
    mock_response = MagicMock(Response)
    mock_response.status_code = 200
    mock_response.reason = "OK"
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.json.return_value = return_value
    text = JSONEncoder().encode(return_value)
    mock_response.text = text
    mock_response.content.decode.return_value = text
    mock_response.request = MagicMock(PreparedRequest)
    mock_response.request.method = "TEST"
    mock_response.request.url = "TEST"
    mock_response.request.body = None
    return mock_response


def _create_file_response(
    expected_content: Union[str, bytes],
) -> MagicMock:
    if isinstance(expected_content, str):
        content = expected_content.encode()
    elif isinstance(expected_content, bytes):
        content = expected_content
    else:
        raise TypeError("Expected content must be str or bytes")
    file_response = MagicMock()
    file_response.content = content
    file_response.status_code = 200
    file_response.iter_content.return_value = iter([content])
    return file_response


def _create_file_json(
    expected_filename: str,
    mime_type: str = "text/plain;charset=UTF-8",
) -> dict:
    return {
        "id": 123,
        "name": str(expected_filename),
        "url": "http://localhost",
        "attachmentType": "FILE",
        "mimeType": str(mime_type),
        "urlExpiresInMillis": 120000,
        "sizeInKb": 1,
        "parentType": "ROW",
        "parentId": 456,
        "createdAt": "2023-02-22T22:46:44Z",
        "createdBy": {"email": "markmonkey@robocorp.com"},
    }


def _patch_file_response(
    library: Smartsheet,
    mocker: MockerFixture,
    expected_filename: str,
    expected_content: Union[str, bytes],
    mime_type: str = "text/plain;charset=UTF-8",
) -> MagicMock:
    _patch_response(library, mocker, _create_file_json(expected_filename, mime_type))
    mock_get = mocker.patch("smartsheet.attachments.requests.get")
    mock_get.return_value = _create_file_response(expected_content)
    return mock_get


def _patch_multiple_file_responses(
    library: Smartsheet,
    mocker: MockerFixture,
    expected_filenames: List[str],
    expected_contents: List[Union[str, bytes]],
    mime_types: List[str],
    send_patch: MagicMock = None,
) -> MagicMock:
    """Creates multiple file responses for a single request.

    Warning: Send patch is not returned, but is modified in place.
    """
    json_responses = []
    for filename, mime_type in zip(expected_filenames, mime_types):
        file_json = _create_file_json(filename, mime_type)
        json_responses.append(_create_json_response(file_json))

    if send_patch is None:
        _patch_multiple_responses(library, mocker, json_responses)
    else:
        _extend_patch(send_patch, json_responses)
    file_responses = []
    for content in expected_contents:
        file_responses.append(_create_file_response(content))
    mock_get = mocker.patch("smartsheet.attachments.requests.get")
    mock_get.side_effect = file_responses
    return mock_get


def _patch_response(
    library: Smartsheet, mocker: MockerFixture, return_value: dict
) -> MagicMock:
    mock_response = _create_json_response(return_value)
    config = {"return_value": mock_response}
    return mocker.patch.object(library.smart._session, "send", **config)


def _patch_multiple_responses(
    library: Smartsheet, mocker: MockerFixture, mocked_responses: Iterable[MagicMock]
) -> MagicMock:
    config = {"side_effect": mocked_responses}
    return mocker.patch.object(library.smart._session, "send", **config)


def _extend_patch(patch: MagicMock, mocked_responses: Iterable[MagicMock]) -> MagicMock:
    """This function will extend the side_effect of a patch with new responses.

    It does this by chaining the current side_effect with the new responses.

    :param patch: The patch to extend.
    :param mocked_responses: The responses to add to the patch.
    """
    current_side_effect = patch.side_effect
    if current_side_effect is None:
        patch.side_effect = mocked_responses
    else:
        patch.side_effect = chain(current_side_effect, mocked_responses)
    return patch


def _wrap_lib(lib_with_sheet: Smartsheet, mocker: MockerFixture) -> MagicMock:
    func_wrap = mocker.Mock(wraps=lib_with_sheet.smart)
    func_patch = mocker.patch.object(lib_with_sheet, "smart", func_wrap)
    return func_patch


def test_authorization(library: Smartsheet, mocker: MockerFixture) -> None:
    mock_client = mocker.patch("RPA.Smartsheet.SmartSDK", autospec=True)

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


def test_get_sheet(authorized_lib: Smartsheet, mocker: MockerFixture) -> None:
    patch = _patch_response(authorized_lib, mocker, MOCK_SHEET_JSON)

    sheet = authorized_lib.get_sheet(123, native=True)

    patch.assert_called()
    assert sheet.id == MOCK_SHEET_JSON["id"]
    assert [c.title for c in sheet.columns] == [
        c["title"] for c in MOCK_SHEET_JSON["columns"]
    ]
    for row in sheet.rows:
        assert row.id in [r["id"] for r in MOCK_SHEET_JSON["rows"]]


def test_convert_sheet_to_table(
    lib_with_sheet: Smartsheet, mocker: MockerFixture
) -> None:
    table = lib_with_sheet.convert_sheet_to_table()

    assert isinstance(table, Table)
    expected_columns = MOCK_SHEET_JSON["columns"].copy()
    expected_columns.append({"title": "rowId"})
    assert table.columns == [c["title"] for c in expected_columns]
    for table_row, sheet_row in zip(table, MOCK_SHEET_JSON["rows"]):
        expected_row = [cell["value"] for cell in sheet_row["cells"].copy()]
        expected_row.append(sheet_row["id"])
        assert list(table_row.values()) == expected_row


def test_download_attachment(lib_with_sheet: Smartsheet, mocker: MockerFixture) -> None:
    expected_filename = "dummy.txt"
    expected_content = "dummy file content"
    mock_get = _patch_file_response(
        lib_with_sheet, mocker, expected_filename, expected_content
    )

    downloaded_file = lib_with_sheet.download_attachment(123, TEMP_DIR)

    mock_get.assert_called()
    assert downloaded_file
    assert downloaded_file.exists()
    assert downloaded_file.read_text() == str(expected_content)


def test_get_sheet_with_attachments(
    authorized_lib: Smartsheet, mocker: MockerFixture
) -> None:
    mock_sheet = MOCK_SHEET_JSON.copy()
    mock_sheet["rows"][0]["attachments"] = MOCKED_ATTACHMENT_LIST
    send_responses = []
    send_responses.append(_create_json_response(mock_sheet))
    send_responses.append(_create_json_response(MOCKED_ROW_ATTACHMENTS))
    send_patch = _patch_multiple_responses(authorized_lib, mocker, send_responses)
    attachments = [
        MOCK_IMAGE_ATTACHMENT,
        MOCK_TEXT_ATTACHMENT,
    ]
    attachment_patches = _patch_multiple_file_responses(
        authorized_lib,
        mocker,
        [a["expected_filename"] for a in attachments],
        [a["expected_content"] for a in attachments],
        [a["mime_type"] for a in attachments],
        send_patch,
    )
    # Return empty responses for all rows except the first one.
    empty_responses = []
    for _ in range(len(mock_sheet["rows"]) - 1):
        empty_responses.append(_create_json_response(MOCKED_ROW_NO_ATTACHMENTS))
    _extend_patch(send_patch, empty_responses)

    sheet_with_attachments: Table = authorized_lib.get_sheet(
        123, include="attachments, attachmentFiles", download_path=TEMP_DIR
    )

    send_patch.assert_called()
    assert authorized_lib.current_sheet.selected_includes == [
        "attachments",
        "attachmentFiles",
    ]
    files_row = sheet_with_attachments[:, "attachmentFiles"]
    for row in files_row:
        if row is not None:
            for file, expected_content in zip(row, attachments):
                assert file.exists()
                if expected_content["mime_type"] == "text/plain":
                    try:
                        decoded_content = expected_content["expected_content"].decode()
                    except (UnicodeDecodeError, AttributeError):
                        decoded_content = expected_content["expected_content"]
                    assert file.read_text() == decoded_content
                else:
                    assert file.read_bytes() == expected_content["expected_content"]
    attachment_patches.assert_called()


def test_get_row(lib_with_sheet: Smartsheet, mocker: MockerFixture) -> None:
    patch = _patch_response(lib_with_sheet, mocker, MOCKED_ROW)

    row = lib_with_sheet.get_row(123, native=False)

    patch.assert_called()
    for cell in MOCKED_ROW["cells"]:
        assert cell["value"] == row[cell["columnId"]]


def test_get_native_row(lib_with_sheet: Smartsheet, mocker: MockerFixture) -> None:
    patch = _patch_response(lib_with_sheet, mocker, MOCKED_ROW)

    row = lib_with_sheet.get_row(123, native=True)

    patch.assert_called()
    assert row.id == MOCKED_ROW["id"]
    for cell in MOCKED_ROW["cells"]:
        assert cell["value"] in [c.value for c in row.cells]


@pytest.mark.parametrize(
    "row",
    [
        {NAME_COLUMN_ID: "Mark", ITEM_COLUMN_ID: "Shirt", ZIP_COLUMN_ID: 12345},
        {"Name": "Mark", "Item": "Shirt", "Zip": 12345},
        [
            {"column_id": NAME_COLUMN_ID, "value": "Mark"},
            {"column_id": ITEM_COLUMN_ID, "value": "Shirt"},
            {"column_id": ZIP_COLUMN_ID, "value": 12345},
        ],
        [
            {"title": "Name", "value": "Mark"},
            {"title": "Item", "value": "Shirt"},
            {"title": "Zip", "value": 12345},
        ],
    ],
)
def test_create_row(lib_with_sheet: Smartsheet, row: Union[dict, List]) -> None:
    expected_cells = [
        {"column_id": NAME_COLUMN_ID, "value": "Mark"},
        {"column_id": ITEM_COLUMN_ID, "value": "Shirt"},
        {"column_id": ZIP_COLUMN_ID, "value": 12345},
    ]
    if isinstance(row, dict):
        new_row = lib_with_sheet._create_row_from_dict(row)
    else:
        new_row = lib_with_sheet._create_row_from_list(row)

    for cell, expected_cell in zip(new_row.cells, expected_cells):
        assert cell.column_id == expected_cell["column_id"]
        assert cell.value == expected_cell["value"]


def test_set_row(lib_with_sheet: Smartsheet, mocker: MockerFixture) -> None:
    patch = _patch_response(lib_with_sheet, mocker, MOCKED_UPDATE_ROW_SUCCESS)
    func_patch = _wrap_lib(lib_with_sheet, mocker)

    row = lib_with_sheet.set_row(123, UPDATED_ROW_1, native=True)

    for call in func_patch.Sheets.update_rows.call_args_list:
        sheet_id_called = call[0][0]
        row_called = call[0][1][0]
        assert sheet_id_called == MOCK_SHEET_JSON["id"]
        assert row_called.id == 123
        for cell in row_called.cells:
            assert cell.value in [c["value"] for c in UPDATED_ROW_1]
    patch.assert_called()
    assert row.id == MOCKED_UPDATE_ROW_SUCCESS["result"][0]["id"]
    for cell in UPDATED_ROW_1:
        assert cell["value"] in [c.value for c in row.cells]


def test_set_rows(lib_with_sheet: Smartsheet, mocker: MockerFixture) -> None:
    patch = _patch_response(lib_with_sheet, mocker, MOCKED_UPDATE_ROW_SUCCESS)
    func_patch = _wrap_lib(lib_with_sheet, mocker)

    rows = lib_with_sheet.set_rows(UPDATED_ROWS, native=True)

    for call in func_patch.Sheets.update_rows.call_args_list:
        sheet_id_called = call[0][0]
        rows_called = call[0][1]
        assert sheet_id_called == MOCK_SHEET_JSON["id"]
        for row in rows_called:
            assert row.id in [c.get("rowId", None) for r in UPDATED_ROWS for c in r]
    patch.assert_called()
    assert len(rows) == len(MOCKED_UPDATE_ROW_SUCCESS["result"])


def test_add_rows(lib_with_sheet: Smartsheet, mocker: MockerFixture) -> None:
    patch = _patch_response(lib_with_sheet, mocker, MOCKED_ADD_ROW_SUCCESS)
    func_patch = _wrap_lib(lib_with_sheet, mocker)

    rows = lib_with_sheet.add_rows(NEW_ROWS, native=True)

    for call in func_patch.Sheets.add_rows.call_args_list:
        sheet_id_called = call[0][0]
        rows_called = call[0][1]
        assert sheet_id_called == MOCK_SHEET_JSON["id"]
        for row in rows_called:
            assert row.id is None
    patch.assert_called()
    assert len(rows) == len(MOCKED_ADD_ROW_SUCCESS["result"])


def test_create_sheet(authorized_lib: Smartsheet, mocker: MockerFixture) -> None:
    patch = _patch_response(authorized_lib, mocker, MOCKED_CREATE_SHEET_SUCCESS)
    func_patch = _wrap_lib(authorized_lib, mocker)

    sheet = authorized_lib.create_sheet(NEW_SHEET_NAME, NEW_SHEET_COLUMNS)

    for call in func_patch.Home.create_sheet.call_args_list:
        sheet_called = call[0][0]
        assert sheet_called.name == NEW_SHEET_NAME
        assert sheet_called.columns[0].title == NEW_SHEET_COLUMNS[0]["title"]
        assert sheet_called.columns[0].type == NEW_SHEET_COLUMNS[0]["type"]
    patch.assert_called()
    assert sheet.id == MOCKED_CREATE_SHEET_SUCCESS["result"]["id"]
    assert sheet.name == NEW_SHEET_NAME


def test_search(lib_with_sheet: Smartsheet, mocker: MockerFixture) -> None:
    patch = _patch_response(lib_with_sheet, mocker, MOCKED_SEARCH_RESULTS)
    func_patch = _wrap_lib(lib_with_sheet, mocker)

    results = lib_with_sheet.search(
        "onesie", include="favoriteFlag", scopes="comments,cellData"
    )

    for call in func_patch.Search.search.call_args_list:
        query_called = call[0][0]
        include_called = call[0][1]
        scope_called = call[0][4]
        assert query_called == "onesie"
        assert include_called == ["favoriteFlag"]
        assert scope_called == ["comments", "cellData"]
    patch.assert_called()
    assert len(results) == len(MOCKED_SEARCH_RESULTS["results"])
    for result in results:
        assert result.object_id in [
            r["objectId"] for r in MOCKED_SEARCH_RESULTS["results"]
        ]


def test_get_row_from_number(lib_with_sheet: Smartsheet, mocker: MockerFixture) -> None:
    row_id = lib_with_sheet._get_row_from_number(1)

    assert row_id == MOCK_SHEET_JSON["rows"][0]["id"]
