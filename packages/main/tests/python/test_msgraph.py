from json.encoder import JSONEncoder
import time
from typing import List
from urllib.parse import parse_qs, urlencode, urlparse
from mock import MagicMock, ANY
import pytest
from pytest_mock import MockerFixture
from RPA.MSGraph import MSGraph, DEFAULT_REDIRECT_URI
from O365.sharepoint import Site
from pathlib import Path
import re

RESOURCE_DIR = Path(__file__).parent / "resources"
TEMP_DIR = Path(__file__).parent.parent / "results"
CONFIG_FILE = RESOURCE_DIR / "msgraph"
SCOPES = MSGraph().get_scopes()

DEFAULT_STATE = "123"
MOCK_CLIENT_ID = "my-client-id"
MOCK_CLIENT_SECRET = "my-client-secret"
MOCK_AUTH_CODE = "https://localhost/myapp/?code=my-mock-auth-code-123&state={}&session_state=mock-session-state#"
MOCK_ACCESS_TOKEN = "microsoft-access-token-{:0>2}"
MOCK_REFRESH_TOKEN = "microsoft-refresh-token-{:0>2}"


@pytest.fixture
def library() -> MSGraph:
    return MSGraph(file_backend_path=TEMP_DIR)


@pytest.fixture
def configured_lib(library: MSGraph) -> MSGraph:
    library.configure_msgraph_client(MOCK_CLIENT_ID, MOCK_CLIENT_SECRET)
    return library


@pytest.fixture
def init_auth(library: MSGraph, mocker: MockerFixture) -> str:
    return library.generate_oauth_authorization_url(MOCK_CLIENT_ID, MOCK_CLIENT_SECRET)


def _get_stateful_mock_auth_code(init_auth: str) -> str:
    init_query = parse_qs(urlparse(init_auth).query)
    return MOCK_AUTH_CODE.format(init_query["state"][0])


@pytest.fixture
def authorized_lib(
    configured_lib: MSGraph,
    mocker: MockerFixture,
    init_auth: str,
) -> MSGraph:
    _patch_token_response(configured_lib, mocker, 1)
    configured_lib.authorize_and_get_token(_get_stateful_mock_auth_code(init_auth))
    return configured_lib


@pytest.fixture
def sharepoint_site(authorized_lib: MSGraph, mocker: MockerFixture) -> Site:
    site_id = "contoso.sharepoint.com"
    response = {
        "id": "contoso.sharepoint.com,2C712604-1370-44E7-A1F5-426573FDA80A,2D2244C3-251A-49EA-93A8-39E1C3A060FE",
        "displayName": "OneDrive Team Site",
        "name": "1drvteam",
        "createdDateTime": "2017-05-09T20:56:00Z",
        "lastModifiedDateTime": "2017-05-09T20:56:01Z",
        "webUrl": "https://contoso.sharepoint.com/teams/1drvteam",
    }
    _patch_graph_response(authorized_lib, mocker, response)

    return authorized_lib.get_sharepoint_site(site_id)


def _patch_token_response(
    library: MSGraph, mocker: MockerFixture, iteration: int
) -> MockerFixture._Patcher:
    return _patch_graph_response(
        library,
        mocker,
        {
            "token_type": "Bearer",
            "scope": "%20F".join(SCOPES),
            "expires_in": 3600,
            "access_token": MOCK_ACCESS_TOKEN.format(iteration),
            "refresh_token": MOCK_REFRESH_TOKEN.format(iteration),
        },
    )


def _create_graph_json_response(return_value: dict) -> MagicMock:
    mock_graph_response = MagicMock()
    mock_graph_response.status_code = 200
    mock_graph_response.headers = {"Content-Type": "application/json"}
    mock_graph_response.json.return_value = return_value
    mock_graph_response.text = JSONEncoder().encode(return_value)
    return mock_graph_response


def _patch_graph_response(
    library: MSGraph, mocker: MockerFixture, return_value: dict
) -> MagicMock:
    mock_graph_response = _create_graph_json_response(return_value)
    config = {"return_value": mock_graph_response}

    return mocker.patch.object(library.client.connection.session, "request", **config)


def _patch_multiple_graph_responses(
    library: MSGraph, mocker: MockerFixture, mocked_responses: List[MagicMock]
) -> MagicMock:
    config = {"side_effect": mocked_responses}

    return mocker.patch.object(library.client.connection.session, "request", **config)


def test_configuring_graph_client(library: MSGraph, mocker: MockerFixture) -> None:
    mock_client = mocker.patch("RPA.MSGraph.Account", autospec=True)

    library.generate_oauth_authorization_url(MOCK_CLIENT_ID, MOCK_CLIENT_SECRET)

    mock_client.assert_any_call((MOCK_CLIENT_ID, MOCK_CLIENT_SECRET), token_backend=ANY)


def test_generating_auth_url(init_auth: str) -> None:
    params = {
        "response_type": "code",
        "client_id": MOCK_CLIENT_ID,
        "redirect_uri": DEFAULT_REDIRECT_URI,
        "scope": " ".join(SCOPES),
    }
    encoded_params = urlencode(params).replace(r"+", r"\+")
    pattern = re.compile(
        rf"https:\/\/login.microsoftonline.com\/common\/oauth2\/v2.0\/authorize\?{encoded_params}"
        r"&state=[a-zA-Z0-9]*&access_type=offline"
    )
    result = re.match(pattern, init_auth)
    assert result


def test_auth_cycle(
    library: MSGraph,
    mocker: MockerFixture,
    init_auth: str,
) -> None:
    _patch_token_response(library, mocker, 1)

    refresh_token = library.authorize_and_get_token(
        _get_stateful_mock_auth_code(init_auth)
    )

    assert library.token_backend.get_token()[
        "access_token"
    ] == MOCK_ACCESS_TOKEN.format(1)
    assert refresh_token == MOCK_REFRESH_TOKEN.format(1)


def test_refreshing_token(configured_lib: MSGraph, mocker: MockerFixture) -> None:
    return_token = {
        "token_type": "Bearer",
        "expires_in": 3600,
        "access_token": MOCK_ACCESS_TOKEN.format(2),
        "refresh_token": MOCK_REFRESH_TOKEN.format(2),
        "expires_at": time.time() + 3600,
        "scope": "%20F".join(SCOPES),
        "scopes": SCOPES,
    }

    config = {"return_value.refresh_token.return_value": return_token}
    mocker.patch("O365.connection.OAuth2Session", **config)

    refresh_token = configured_lib.refresh_oauth_token(MOCK_REFRESH_TOKEN.format(1))

    assert configured_lib.token_backend.get_token()[
        "access_token"
    ] == MOCK_ACCESS_TOKEN.format(2)
    assert refresh_token == MOCK_REFRESH_TOKEN.format(2)


def test_get_me(authorized_lib: MSGraph, mocker: MockerFixture) -> None:
    data = {
        "businessPhones": ["+1 425 555 0109"],
        "displayName": "Adele Vance",
        "givenName": "Adele",
        "jobTitle": "Retail Manager",
        "mail": "AdeleV@contoso.onmicrosoft.com",
        "mobilePhone": "+1 425 555 0109",
        "officeLocation": "18/2111",
        "preferredLanguage": "en-US",
        "surname": "Vance",
        "userPrincipalName": "AdeleV@contoso.onmicrosoft.com",
        "id": "87d349ed-44d7-43e1-9a83-5f2406dee5bd",
    }
    m = _patch_graph_response(authorized_lib, mocker, data)

    user_me = authorized_lib.get_me()

    m.assert_called_once()
    assert str(user_me) == data["displayName"]
    assert user_me.object_id == data["id"]


@pytest.mark.parametrize(
    "search_string,response",
    [
        (
            "adam",
            {
                "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users",
                "value": [
                    {
                        "businessPhones": [],
                        "displayName": "Conf Room Adams",
                        "givenName": None,
                        "jobTitle": None,
                        "mail": "Adams@contoso.com",
                        "mobilePhone": None,
                        "officeLocation": None,
                        "preferredLanguage": None,
                        "surname": None,
                        "userPrincipalName": "Adams@contoso.com",
                        "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed0e0",
                    },
                    {
                        "businessPhones": ["425-555-0100"],
                        "displayName": "Adam Administrator",
                        "givenName": "Adam-adm",
                        "jobTitle": None,
                        "mail": None,
                        "mobilePhone": "425-555-0101",
                        "officeLocation": None,
                        "preferredLanguage": "en-US",
                        "surname": "Administrator",
                        "userPrincipalName": "admin@contoso.com",
                        "id": "4562bcc8-c436-4f95-b7c0-4f8ce89dca5e",
                    },
                ],
            },
        ),
        (
            "john",
            {
                "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users",
                "value": [
                    {
                        "businessPhones": ["555-555-0100"],
                        "displayName": "Johnny Apple",
                        "givenName": "John",
                        "jobTitle": "IT Admin",
                        "mail": "j.apple@contoso.com",
                        "mobilePhone": None,
                        "officeLocation": None,
                        "preferredLanguage": None,
                        "surname": None,
                        "userPrincipalName": "j.apple@contoso.com",
                        "id": "6ea91a8d-e32e-41a1-b7bd-d2d185eed123",
                    },
                    {
                        "businessPhones": ["555-123-0100"],
                        "displayName": "John Smith",
                        "givenName": "John",
                        "jobTitle": "BDR",
                        "mail": "j.smith@contoso.com",
                        "mobilePhone": "555-123-0101",
                        "officeLocation": None,
                        "preferredLanguage": "en-US",
                        "surname": "Administrator",
                        "userPrincipalName": "admin@contoso.com",
                        "id": "4562bcc8-c436-4f95-b7c0-4f8ce89dc123",
                    },
                ],
            },
        ),
    ],
)
def test_search_for_users(
    authorized_lib: MSGraph, mocker: MockerFixture, search_string: str, response: dict
) -> None:
    m = _patch_graph_response(authorized_lib, mocker, response)

    users = authorized_lib.search_for_users(search_string)

    m.assert_called_once()
    for user in users:
        assert user.display_name in [u["displayName"] for u in response["value"]]
        assert user.user_principal_name in [
            u["userPrincipalName"] for u in response["value"]
        ]


@pytest.mark.parametrize(
    "folder_path,responses",
    [
        (
            "/Path/To/Folder/",
            [
                {
                    "createdBy": {
                        "user": {
                            "id": "efee1b77-fb3b-4f65-99d6-274c11914d12",
                            "displayName": "Ryan Gregg",
                        }
                    },
                    "createdDateTime": "2016-03-21T20:01:37Z",
                    "cTag": '"c:{86EB4C8E-D20D-46B9-AD41-23B8868DDA8A},0"',
                    "eTag": '"{86EB4C8E-D20D-46B9-AD41-23B8868DDA8A},1"',
                    "folder": {"childCount": 120},
                    "id": "01NKDM7HMOJTVYMDOSXFDK2QJDXCDI3WUK",
                    "lastModifiedBy": {
                        "user": {
                            "id": "efee1b77-fb3b-4f65-99d6-274c11914d12",
                            "displayName": "Ryan Gregg",
                        }
                    },
                    "lastModifiedDateTime": "2016-03-21T20:01:37Z",
                    "name": "OneDrive",
                    "root": {},
                    "size": 157286400,
                    "webUrl": "https://contoso-my.sharepoint.com/personal/rgregg_contoso_com/Documents",
                },
                {
                    "value": [
                        {"name": "myfile.jpg", "size": 2048, "file": {}},
                        {"name": "Documents", "folder": {"childCount": 4}},
                        {"name": "Photos", "folder": {"childCount": 203}},
                        {"name": "my sheet(1).xlsx", "size": 197},
                    ],
                },
            ],
        )
    ],
)
def test_listing_files_onedrive_folder(
    authorized_lib: MSGraph,
    mocker: MockerFixture,
    folder_path: str,
    responses: List[dict],
) -> None:
    mocked_responses = [_create_graph_json_response(r) for r in responses]
    _patch_multiple_graph_responses(authorized_lib, mocker, mocked_responses)

    items = authorized_lib.list_files_in_onedrive_folder(folder_path)

    files_in_response = [
        item for item in responses[1]["value"] if not item.get("folder")
    ]
    for i, item in enumerate(items):
        assert item.name == files_in_response[i]["name"]
        assert not item.is_folder


@pytest.mark.parametrize(
    "file_path,responses",
    [
        (
            "/Path/To/File",
            [
                {
                    "name": "my notes.txt",
                    "size": 197,
                    "id": "01NKDM7HMOJTVYMDOSXFDK2QJDXCDI3WUK",
                },
                "dummy file content".encode(),
            ],
        )
    ],
)
def test_downloading_file_from_onedrive(
    authorized_lib: MSGraph,
    mocker: MockerFixture,
    file_path: str,
    responses: List[dict],
) -> None:
    mocked_responses = []
    mocked_responses.append(_create_graph_json_response(responses[0]))
    mocked_response = MagicMock()
    mocked_response.__enter__.return_value.status_code = 200
    mocked_response.__enter__.return_value.headers = {
        "Content-Type": "application/octet-stream"
    }
    mocked_response.__enter__.return_value.content = responses[1]
    mocked_responses.append(mocked_response)
    _patch_multiple_graph_responses(authorized_lib, mocker, mocked_responses)

    downloaded_file = authorized_lib.download_file_from_onedrive(file_path, TEMP_DIR)

    assert downloaded_file
    assert downloaded_file.exists()


@pytest.mark.parametrize(
    "file_path,responses",
    [
        (
            "/Path/To/File",
            [
                {
                    "createdBy": {
                        "user": {
                            "id": "efee1b77-fb3b-4f65-99d6-274c11914d12",
                            "displayName": "Ryan Gregg",
                        }
                    },
                    "createdDateTime": "2016-03-21T20:01:37Z",
                    "cTag": '"c:{86EB4C8E-D20D-46B9-AD41-23B8868DDA8A},0"',
                    "eTag": '"{86EB4C8E-D20D-46B9-AD41-23B8868DDA8A},1"',
                    "folder": {"childCount": 120},
                    "id": "01NKDM7HMOJTVYMDOSXFDK2QJDXCDI3WUK",
                    "lastModifiedBy": {
                        "user": {
                            "id": "efee1b77-fb3b-4f65-99d6-274c11914d12",
                            "displayName": "Ryan Gregg",
                        }
                    },
                    "lastModifiedDateTime": "2016-03-21T20:01:37Z",
                    "name": "OneDrive",
                    "root": {},
                    "size": 157286400,
                    "webUrl": "https://contoso-my.sharepoint.com/personal/rgregg_contoso_com/Documents",
                },
                {
                    "value": [
                        {"name": "myfile.jpg", "size": 2048, "file": {}},
                        {"name": "my sheet(1).xlsx", "size": 197},
                    ],
                },
                "dummy file content".encode(),
            ],
        )
    ],
)
def test_downloading_folder_from_onedrive(
    authorized_lib: MSGraph,
    mocker: MockerFixture,
    file_path: str,
    responses: List[dict],
) -> None:
    mocked_responses = [
        _create_graph_json_response(r) for r in (responses[0], responses[1])
    ]

    mocked_response = MagicMock()
    mocked_response.__enter__.return_value.status_code = 200
    mocked_response.__enter__.return_value.headers = {
        "Content-Type": "application/octet-stream"
    }
    mocked_response.__enter__.return_value.content = responses[2]
    for _ in responses[1]["value"]:
        mocked_responses.append(mocked_response)

    _patch_multiple_graph_responses(authorized_lib, mocker, mocked_responses)

    downloaded_folder = authorized_lib.download_folder_from_onedrive(
        file_path, TEMP_DIR / "downloaded_folder"
    )

    assert downloaded_folder
    assert downloaded_folder.exists()


@pytest.mark.parametrize(
    "search_string,response",
    [
        (
            "Contoso Project",
            {
                "value": [
                    {
                        "id": "0123456789abc!123",
                        "name": "Contoso Project",
                        "folder": {},
                        "searchResult": {
                            "onClickTelemetryUrl": "https://bing.com/0123456789abc!123"
                        },
                    },
                    {
                        "id": "0123456789abc!456",
                        "name": "Contoso Project 2016",
                        "folder": {},
                        "searchResult": {
                            "onClickTelemetryUrl": "https://bing.com/0123456789abc!456"
                        },
                    },
                ],
            },
        )
    ],
)
def test_finding_onedrive_file(
    authorized_lib: MSGraph, mocker: MockerFixture, search_string: str, response: dict
) -> None:
    m = _patch_graph_response(authorized_lib, mocker, response)

    items = authorized_lib.find_onedrive_file(search_string)

    m.assert_called_once()
    for item in items:
        assert item.object_id in [i["id"] for i in response["value"]]
        assert item.name in [i["name"] for i in response["value"]]


@pytest.mark.parametrize(
    "share_url,responses",
    [
        (
            "https://1drv.ms/v/s!AjonToUPWqXmgjO3RqDbhRaSMrOM",
            [
                {
                    "name": "report.txt",
                    "size": 1997,
                    "id": "01NKDM7HMOJTVYMDOSXFDK2QJDXCDI3WUK",
                },
                "dummy file content".encode(),
            ],
        )
    ],
)
def test_downloading_from_share_link(
    authorized_lib: MSGraph,
    mocker: MockerFixture,
    share_url: str,
    responses: List[dict],
) -> None:
    mocked_responses = []
    mocked_responses.append(_create_graph_json_response(responses[0]))
    mocked_response = MagicMock()
    mocked_response.__enter__.return_value.status_code = 200
    mocked_response.__enter__.return_value.headers = {
        "Content-Type": "application/octet-stream"
    }
    mocked_response.__enter__.return_value.content = responses[1]
    mocked_responses.append(mocked_response)
    _patch_multiple_graph_responses(authorized_lib, mocker, mocked_responses)

    downloaded_file = authorized_lib.download_file_from_share_link(share_url, TEMP_DIR)

    assert downloaded_file
    assert downloaded_file.exists()


@pytest.mark.parametrize(
    "file_path,folder_path,responses",
    [
        (
            "/Path/To/my notes.txt",
            "/Path/To/Folder/",
            [
                {
                    "createdBy": {
                        "user": {
                            "id": "efee1b77-fb3b-4f65-99d6-274c11914d12",
                            "displayName": "Ryan Gregg",
                        }
                    },
                    "createdDateTime": "2016-03-21T20:01:37Z",
                    "cTag": '"c:{86EB4C8E-D20D-46B9-AD41-23B8868DDA8A},0"',
                    "eTag": '"{86EB4C8E-D20D-46B9-AD41-23B8868DDA8A},1"',
                    "folder": {"childCount": 120},
                    "id": "01NKDM7HMOJTVYMDOSXFDK2QJDXCDI3WUK",
                    "lastModifiedBy": {
                        "user": {
                            "id": "efee1b77-fb3b-4f65-99d6-274c11914d12",
                            "displayName": "Ryan Gregg",
                        }
                    },
                    "lastModifiedDateTime": "2016-03-21T20:01:37Z",
                    "name": "OneDrive",
                    "root": {},
                    "size": 157286400,
                    "webUrl": "https://contoso-my.sharepoint.com/personal/rgregg_contoso_com/Documents",
                },
                {
                    "name": "my notes.txt",
                    "size": 197,
                    "id": "01NKDM7HMOJTVYMDOSXFDK2QJDXCDI3WUK",
                },
            ],
        )
    ],
)
def test_uploading_file_to_onedrive(
    authorized_lib: MSGraph,
    mocker: MockerFixture,
    file_path: str,
    folder_path: str,
    responses: List[dict],
) -> None:
    mocked_responses = [_create_graph_json_response(r) for r in responses]
    _patch_multiple_graph_responses(authorized_lib, mocker, mocked_responses)

    # Mock file interactions
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("pathlib.Path.is_file", return_value=True)
    mocked_path = MagicMock()
    mocked_path.st_size = 956514
    mocker.patch("pathlib.Path.stat", return_value=mocked_path)
    open_file = mocker.mock_open(read_data="secret notes")
    mocker.patch("io.open", open_file)
    try:
        mocker.patch("pathlib.Path._accessor.open", open_file, create=True)
    except AttributeError:
        pass

    item = authorized_lib.upload_file_to_onedrive(file_path, folder_path)

    assert item.name == responses[1]["name"]


@pytest.mark.parametrize(
    "args",
    [
        ("root"),
        ("contoso.sharepoint.com"),
        ("contoso.sharepoint.com", "/path/to/site"),
        (
            "contoso.sharepoint.com,a384ebb0-67a5-4976-a7eb-60bbd5d5f87a,f0a2c07f-bfa0-4259-b9cd-fbdab88ebcf4"
        ),
        (
            "contoso.sharepoint.com",
            "a384ebb0-67a5-4976-a7eb-60bbd5d5f87a",
            "f0a2c07f-bfa0-4259-b9cd-fbdab88ebcf4",
        ),
    ],
)
def test_get_sharepoint_site(
    authorized_lib: MSGraph, mocker: MockerFixture, args: tuple
) -> None:
    response = {
        "id": "contoso.sharepoint.com,2C712604-1370-44E7-A1F5-426573FDA80A,2D2244C3-251A-49EA-93A8-39E1C3A060FE",
        "displayName": "OneDrive Team Site",
        "name": "1drvteam",
        "createdDateTime": "2017-05-09T20:56:00Z",
        "lastModifiedDateTime": "2017-05-09T20:56:01Z",
        "webUrl": "https://contoso.sharepoint.com/teams/1drvteam",
    }
    m = _patch_graph_response(authorized_lib, mocker, response)

    if isinstance(args, str):
        site = authorized_lib.get_sharepoint_site(args)
    else:
        site = authorized_lib.get_sharepoint_site(*args)

    m.assert_called_once()
    assert site.display_name == response["displayName"]
    assert site.object_id == response["id"]


def test_get_items_from_sharepoint_list(
    authorized_lib: MSGraph, mocker: MockerFixture, sharepoint_site: Site
) -> None:
    list_name = "Documents"
    list_response = {
        "id": "b57af081-936c-4803-a120-d94887b03864",
        "name": "Documents",
        "createdDateTime": "2016-08-30T08:32:00Z",
        "lastModifiedDateTime": "2016-08-30T08:32:00Z",
        "list": {"hidden": False, "template": "documentLibrary"},
    }
    columns_response = {
        "value": [
            {
                "description": "",
                "displayName": "Name",
                "hidden": False,
                "id": "99ddcf45-e2f7-4f17-82b0-6fba34445103",
                "indexed": False,
                "name": "Name",
                "readOnly": False,
                "required": False,
                "text": {
                    "allowMultipleLines": False,
                    "appendChangesToExistingText": False,
                    "linesForEditing": 0,
                    "maxLength": 255,
                },
            },
            {
                "description": "",
                "displayName": "Color",
                "id": "11dfef35-e2f7-4f17-82b0-6fba34445103",
                "indexed": False,
                "name": "Color",
                "readOnly": False,
                "required": False,
                "text": {
                    "allowMultipleLines": False,
                    "appendChangesToExistingText": False,
                    "linesForEditing": 0,
                    "maxLength": 255,
                },
            },
            {
                "description": "",
                "displayName": "Quantity",
                "id": "27c36545-4c19-4af8-a5a1-eaf520dbba25",
                "indexed": False,
                "name": "Quantity",
                "readOnly": False,
                "required": False,
                "text": {
                    "allowMultipleLines": False,
                    "appendChangesToExistingText": False,
                    "linesForEditing": 0,
                    "maxLength": 255,
                },
            },
        ]
    }
    list_items_response = {
        "value": [
            {
                "id": "2",
                "fields": {"Name": "Gadget", "Color": "Red", "Quantity": 503},
            },
            {
                "id": "4",
                "fields": {"Name": "Widget", "Color": "Blue", "Quantity": 2357},
            },
            {
                "id": "7",
                "fields": {"Name": "Gizmo", "Color": "Green", "Quantity": 92},
            },
        ]
    }
    mocked_responses = [
        _create_graph_json_response(r)
        for r in (list_response, columns_response, list_items_response)
    ]
    _patch_multiple_graph_responses(authorized_lib, mocker, mocked_responses)

    items = authorized_lib.get_items_from_sharepoint_list(list_name, sharepoint_site)

    assert items
    for item in items:
        assert item["object_id"] in [i["id"] for i in list_items_response["value"]]


def test_create_sharepoint_list(
    authorized_lib: MSGraph, mocker: MockerFixture, sharepoint_site: Site
) -> None:
    new_list_data = {
        "displayName": "Books",
        "columns": [
            {"name": "Author", "text": {}},
            {"name": "PageCount", "number": {}},
        ],
        "list": {"template": "genericList"},
    }
    list_response = {
        "id": "22e03ef3-6ef4-424d-a1d3-92a337807c30",
        "createdDateTime": "2017-04-30T01:21:00Z",
        "createdBy": {
            "user": {
                "displayName": "Ryan Gregg",
                "id": "8606e4d5-d582-4f5f-aeba-7d7c18b20cfd",
            }
        },
        "lastModifiedDateTime": "2016-08-30T08:26:00Z",
        "lastModifiedBy": {
            "user": {
                "displayName": "Ryan Gregg",
                "id": "8606e4d5-d582-4f5f-aeba-7d7c18b20cfd",
            }
        },
    }
    columns_response = {
        "value": [
            {
                "description": "",
                "displayName": "Author",
                "hidden": False,
                "id": "99ddcf45-e2f7-4f17-82b0-6fba34445103",
                "indexed": False,
                "name": "Author",
                "readOnly": False,
                "required": False,
                "text": {
                    "allowMultipleLines": False,
                    "appendChangesToExistingText": False,
                    "linesForEditing": 0,
                    "maxLength": 255,
                },
            },
            {
                "description": "",
                "displayName": "PageCount",
                "id": "11dfef35-e2f7-4f17-82b0-6fba34445103",
                "indexed": False,
                "name": "PageCount",
                "readOnly": False,
                "required": False,
                "text": {
                    "allowMultipleLines": False,
                    "appendChangesToExistingText": False,
                    "linesForEditing": 0,
                    "maxLength": 255,
                },
            },
        ]
    }
    mocked_responses = [
        _create_graph_json_response(r) for r in (list_response, columns_response)
    ]
    _patch_multiple_graph_responses(authorized_lib, mocker, mocked_responses)

    sp_list = authorized_lib.create_sharepoint_list(new_list_data, sharepoint_site)

    assert sp_list.object_id == list_response["id"]
    assert (
        sp_list.created_by.display_name
        == list_response["createdBy"]["user"]["displayName"]
    )


def test_list_sharepoint_drives(
    authorized_lib: MSGraph, mocker: MockerFixture, sharepoint_site: Site
) -> None:
    response = {
        "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#drives",
        "value": [
            {
                "createdDateTime": "2017-07-27T02:41:36Z",
                "description": "",
                "id": "b!-RIj2DuyvEyV1T4NlOaMHk8XkS_I8MdFlUCq1BlcjgmhRfAj3-Z8RY2VpuvV_tpd",
                "lastModifiedDateTime": "2018-03-27T07:34:38Z",
                "name": "OneDrive",
                "webUrl": "https://m365x214355-my.sharepoint.com/personal/meganb_m365x214355_onmicrosoft_com/Documents",
                "driveType": "business",
                "createdBy": {"user": {"displayName": "System Account"}},
                "lastModifiedBy": {
                    "user": {
                        "email": "MeganB@M365x214355.onmicrosoft.com",
                        "id": "48d31887-5fad-4d73-a9f5-3c356e68a038",
                        "displayName": "Megan Bowen",
                    }
                },
                "owner": {
                    "user": {
                        "email": "MeganB@M365x214355.onmicrosoft.com",
                        "id": "48d31887-5fad-4d73-a9f5-3c356e68a038",
                        "displayName": "Megan Bowen",
                    }
                },
                "quota": {
                    "deleted": 0,
                    "remaining": 1099217021300,
                    "state": "normal",
                    "total": 1099511627776,
                    "used": 294606476,
                },
            }
        ],
    }
    m = _patch_graph_response(authorized_lib, mocker, response)

    sp_drives = authorized_lib.list_sharepoint_site_drives(sharepoint_site)

    m.assert_called_once()
    assert sp_drives
    for sp_drive in sp_drives:
        assert sp_drive.object_id in [drive["id"] for drive in response["value"]]
        assert sp_drive.name in [drive["name"] for drive in response["value"]]


def test_list_files_in_sharepoint_drive(
    authorized_lib: MSGraph,
    mocker: MockerFixture,
    sharepoint_site: Site,
) -> None:
    drive_id = None
    response_folder = {
        "createdBy": {
            "user": {
                "id": "efee1b77-fb3b-4f65-99d6-274c11914d12",
                "displayName": "Ryan Gregg",
            }
        },
        "createdDateTime": "2016-03-21T20:01:37Z",
        "cTag": '"c:{86EB4C8E-D20D-46B9-AD41-23B8868DDA8A},0"',
        "eTag": '"{86EB4C8E-D20D-46B9-AD41-23B8868DDA8A},1"',
        "folder": {"childCount": 120},
        "id": "01NKDM7HMOJTVYMDOSXFDK2QJDXCDI3WUK",
        "lastModifiedBy": {
            "user": {
                "id": "efee1b77-fb3b-4f65-99d6-274c11914d12",
                "displayName": "Ryan Gregg",
            }
        },
        "lastModifiedDateTime": "2016-03-21T20:01:37Z",
        "name": "OneDrive",
        "root": {},
        "size": 157286400,
        "webUrl": "https://contoso-my.sharepoint.com/personal/rgregg_contoso_com/Documents",
    }

    response_files = {
        "value": [
            {"name": "myfile.jpg", "size": 2048, "file": {}},
            {"name": "Documents", "folder": {"childCount": 4}},
            {"name": "Photos", "folder": {"childCount": 203}},
            {"name": "my sheet(1).xlsx", "size": 197},
        ],
    }
    mocked_responses = [
        _create_graph_json_response(r) for r in (response_folder, response_files)
    ]
    _patch_multiple_graph_responses(authorized_lib, mocker, mocked_responses)

    sp_files = authorized_lib.list_files_in_sharepoint_site_drive(
        sharepoint_site, drive=drive_id
    )

    for file in sp_files:
        assert file.name in [file["name"] for file in response_files["value"]]


@pytest.mark.parametrize(
    "file_path, target_directory, drive_id, responses",
    [
        (
            "/Path/To/File",
            TEMP_DIR,
            None,
            [
                {
                    "name": "file-from-sharepoint.txt",
                    "size": 500097,
                    "id": "3JL14H5L1HJC0PPPQO7EMQB",
                },
                "dummy file content".encode(),
            ],
        ),
    ],
)
def test_download_file_from_sharepoint(
    authorized_lib: MSGraph,
    mocker: MockerFixture,
    sharepoint_site: Site,
    drive_id: str,
    file_path: str,
    target_directory: str,
    responses: List[dict],
) -> None:
    mocked_responses = []
    mocked_responses.append(_create_graph_json_response(responses[0]))
    mocked_response = MagicMock()
    mocked_response.__enter__.return_value.status_code = 200
    mocked_response.__enter__.return_value.headers = {
        "Content-Type": "application/octet-stream"
    }
    mocked_response.__enter__.return_value.content = responses[1]
    mocked_responses.append(mocked_response)
    _patch_multiple_graph_responses(authorized_lib, mocker, mocked_responses)

    downloaded_file = authorized_lib.download_file_from_sharepoint(
        file_path, sharepoint_site, target_directory, drive=drive_id
    )

    assert downloaded_file
    assert downloaded_file.exists()
