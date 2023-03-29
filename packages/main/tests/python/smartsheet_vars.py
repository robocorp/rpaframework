from pathlib import Path
from PIL import Image

_RESOURCE_DIR = Path(__file__).parent.parent / "resources"
_IMAGE_PATH = _RESOURCE_DIR / "images" / "source.png"

_MOCK_IMAGE_ATTACHMENT = Image.open(_IMAGE_PATH)
_MOCK_IMAGE_ATTACHMENT.load()


# Exported constants
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
"""A mocked sheet response"""
MOCK_IMAGE = _MOCK_IMAGE_ATTACHMENT.tobytes()
"""An image in bytes"""
MOCK_IMAGE_ATTACHMENT = {
    "expected_filename": "source.png",
    "expected_content": MOCK_IMAGE,
    "mime_type": "image/png",
}
"""A mocked image attachment"""
MOCK_TEXT_ATTACHMENT = {
    "expected_filename": "note01.txt",
    "expected_content": "Hello World! I'm note number 01!",
    "mime_type": "text/plain",
}
"""A mocked text attachment, use with `.format(<int>)`."""
ATTACHMENT_NODE = {
    "id": None,
    "name": None,
    "attachmentType": "FILE",
    "mimeType": None,
    "sizeInKb": 1,
    "createdAt": "2023-02-22T22:47:26Z",
    "createdBy": {"email": "markmonkey@robocorp.com"},
}
"""You should set the `id`, `name`, and `mimeType` attributes of this dict."""
_attach_one = ATTACHMENT_NODE.copy()
_attach_one["id"] = 123
_attach_one["name"] = "source.png"
_attach_one["mimeType"] = "image/png"
_attach_two = ATTACHMENT_NODE.copy()
_attach_two["id"] = 456
_attach_two["name"] = "note01.txt"
_attach_two["mimeType"] = "text/plain"
MOCKED_ATTACHMENT_LIST = [_attach_one, _attach_two]
"""A mocked attachment list"""
MOCKED_ROW_ATTACHMENTS = {
    "pageNumber": 1,
    "totalPages": 1,
    "totalCount": 2,
    "data": MOCKED_ATTACHMENT_LIST,
}
"""A mocked response for row attachments"""
MOCKED_ROW_NO_ATTACHMENTS = {
    "pageNumber": 0,
    "pageSize": 100,
    "totalPages": 0,
    "totalCount": 0,
    "data": [],
}
"""A mocked response for a row with no attachments"""
MOCKED_ROW = {
    "id": 3218304495249284,
    "sheetId": 7340596407887748,
    "rowNumber": 1,
    "version": 10,
    "permalink": "https://app.smartsheet.com/sheets/g4J274W3V7F549FvxPVrrWV3fJGCC9xGqjq9Gqm1?rowId=3218304495249284",
    "filteredOut": False,
    "expanded": True,
    "accessLevel": "OWNER",
    "createdAt": "2023-02-17T19:00:58Z",
    "createdBy": {"email": "markmonkey@robocorp.com"},
    "modifiedAt": "2023-02-21T21:18:43Z",
    "modifiedBy": {"email": "markmonkey@robocorp.com"},
    "cells": [
        {
            "columnId": 3471889768703876,
            "columnType": "TEXT_NUMBER",
            "value": "Sol Heaton",
            "objectValue": "Sol Heaton",
            "displayValue": "Sol Heaton",
            "format": ",,,,,,,3,1,2,,,,,,,",
        },
        {
            "columnId": 7975489396074372,
            "columnType": "TEXT_NUMBER",
            "value": "Sauce Labs Bolt T-Shirt",
            "objectValue": "Sauce Labs Bolt T-Shirt",
            "displayValue": "Sauce Labs Bolt T-Shirt",
            "format": ",,,,,,,3,1,2,,,,,,,",
        },
        {
            "columnId": 657140001597316,
            "columnType": "TEXT_NUMBER",
            "value": 3695.0,
            "objectValue": 3695.0,
            "displayValue": "3695",
            "format": ",,,,,,,3,1,2,,,,,,,",
        },
    ],
    "attachments": [
        {
            "id": 1037987386288004,
            "name": "test.zip",
            "attachmentType": "FILE",
            "mimeType": "application/zip",
            "sizeInKb": 1,
            "createdAt": "2023-02-22T22:47:26Z",
            "createdBy": {"email": "markmonkey@robocorp.com"},
        },
        {
            "id": 19892232316804,
            "name": "bitmap-Monkey learning processes.png",
            "attachmentType": "FILE",
            "mimeType": "image/png",
            "sizeInKb": 302,
            "createdAt": "2023-02-22T22:25:27Z",
            "createdBy": {"email": "markmonkey@robocorp.com"},
        },
    ],
}
NEW_ROW_1 = [
    {"title": "Name", "value": "Mark Monkey"},
    {"title": "Item", "value": "Sauce Labs Onesie"},
    {"title": "Zip", "value": "California"},
]
"""A mocked row to be added to a sheet"""
NEW_ROW_2 = [
    {"title": "Name", "value": "Mark Monkey"},
    {"title": "Item", "value": "Sauce Labs Fleece Jacket"},
    {"title": "Zip", "value": 90210},
]
NEW_ROWS = [NEW_ROW_1, NEW_ROW_2]
"""A list of mocked rows to be added to a sheet"""
MOCKED_ADD_ROW_SUCCESS = {
    "message": "SUCCESS",
    "resultCode": 0,
    "result": [
        {
            "id": 7859947312768900,
            "sheetId": 7340596407887748,
            "rowNumber": 10,
            "siblingId": 2514617053472644,
            "expanded": True,
            "createdAt": "2023-03-06T20:50:07Z",
            "modifiedAt": "2023-03-06T20:50:07Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Mark Monkey",
                    "displayValue": "Mark Monkey",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Onesie",
                    "displayValue": "Sauce Labs Onesie",
                },
                {
                    "columnId": 657140001597316,
                    "value": "California",
                    "displayValue": "California",
                },
            ],
        },
        {
            "id": 2230447778555780,
            "sheetId": 7340596407887748,
            "rowNumber": 11,
            "siblingId": 7859947312768900,
            "expanded": True,
            "createdAt": "2023-03-06T20:50:07Z",
            "modifiedAt": "2023-03-06T20:50:07Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Mark Monkey",
                    "displayValue": "Mark Monkey",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Fleece Jacket",
                    "displayValue": "Sauce Labs Fleece Jacket",
                },
                {"columnId": 657140001597316, "value": 90210, "displayValue": "90210"},
            ],
        },
    ],
    "version": 11,
}
"""A mocked response for a successful row add"""
UPDATED_ROW_1 = [
    {"title": "Name", "value": "Mark Monkey Jr"},
    {"title": "Item", "value": "Sauce Labs Onesie"},
    {"title": "Zip", "value": 90210},
]
"""A mocked row to be updated in a sheet"""
UPDATED_ROW_2 = [
    {"title": "Name", "value": "Mark Monkey Jr"},
    {"title": "Item", "value": "Sauce Labs Fleece Jacket"},
    {"title": "Zip", "value": 90210},
]
_row_1_with_id = UPDATED_ROW_1.copy()
_row_1_with_id.insert(0, {"rowId": 7859947312768900})
_row_2_with_id = UPDATED_ROW_2.copy()
_row_2_with_id.insert(0, {"rowId": 2230447778555780})
UPDATED_ROWS = [_row_1_with_id, _row_2_with_id]
"""A set of mocked rows to be updated in a sheet"""
NAME_COLUMN_ID = 3471889768703876
ITEM_COLUMN_ID = 7975489396074372
ZIP_COLUMN_ID = 657140001597316
MOCKED_UPDATE_ROW_SUCCESS = {
    "message": "SUCCESS",
    "resultCode": 0,
    "result": [
        {
            "id": 7859947312768900,
            "rowNumber": 1,
            "expanded": True,
            "createdAt": "2023-03-06T20:50:07Z",
            "modifiedAt": "2023-03-06T20:51:53Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Mark Monkey Jr",
                    "displayValue": "Mark Monkey Jr",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Onesie",
                    "displayValue": "Sauce Labs Onesie",
                },
                {"columnId": 657140001597316, "value": 90210, "displayValue": "90210"},
            ],
        },
        {
            "id": 2230447778555780,
            "rowNumber": 2,
            "siblingId": 7859947312768900,
            "expanded": True,
            "createdAt": "2023-03-06T20:50:07Z",
            "modifiedAt": "2023-03-06T20:51:53Z",
            "cells": [
                {
                    "columnId": 3471889768703876,
                    "value": "Mark Monkey Jr",
                    "displayValue": "Mark Monkey Jr",
                },
                {
                    "columnId": 7975489396074372,
                    "value": "Sauce Labs Fleece Jacket",
                    "displayValue": "Sauce Labs Fleece Jacket",
                },
                {"columnId": 657140001597316, "value": 90210, "displayValue": "90210"},
            ],
        },
    ],
    "version": 12,
}
"""A mocked response for a successful row update"""
NEW_SHEET_COLUMNS = [
    {"title": "Order Number", "type": "TEXT_NUMBER", "primary": True},
    {"title": "Customer Name", "type": "TEXT_NUMBER"},
    {"title": "Order Date", "type": "DATE"},
    {
        "title": "Items",
        "type": "MULTI_PICKLIST",
        "options": [
            "Sauce Labs Backpack",
            "Sauce Labs Bike Light",
            "Sauce Labs Bolt T-Shirt",
            "Sauce Labs Fleece Jacket",
            "Sauce Labs Onesie",
            "Test.allTheThings() T-Shirt (Red)",
        ],
    },
]
"""A mocked set of columns to be added to a new sheet"""
NEW_SHEET_NAME = "Test Sheet"
"""A mocked name for a new sheet"""
NEW_SHEET = {
    "name": NEW_SHEET_NAME,
    "columns": NEW_SHEET_COLUMNS,
}
"""A mocked new sheet object."""
MOCKED_CREATE_SHEET_SUCCESS = {
    "message": "SUCCESS",
    "resultCode": 0,
    "result": {
        "id": 842641693796228,
        "name": "Test Sheet",
        "accessLevel": "OWNER",
        "permalink": "https://app.smartsheet.com/sheets/v73m5PQq7g4W7cGmVc7CHPR5v74JG6wQvMFj5331",
        "columns": [
            {
                "id": 1502033234159492,
                "version": 0,
                "index": 0,
                "title": "Order Number",
                "type": "TEXT_NUMBER",
                "primary": True,
                "validation": False,
                "width": 150,
            },
            {
                "id": 6005632861529988,
                "version": 0,
                "index": 1,
                "title": "Customer Name",
                "type": "TEXT_NUMBER",
                "validation": False,
                "width": 150,
            },
            {
                "id": 3753833047844740,
                "version": 0,
                "index": 2,
                "title": "Order Date",
                "type": "DATE",
                "validation": False,
                "width": 150,
            },
            {
                "id": 8257432675215236,
                "version": 2,
                "index": 3,
                "title": "Items",
                "type": "MULTI_PICKLIST",
                "options": [
                    "Sauce Labs Backpack",
                    "Sauce Labs Bike Light",
                    "Sauce Labs Bolt T-Shirt",
                    "Sauce Labs Fleece Jacket",
                    "Sauce Labs Onesie",
                    "Test.allTheThings() T-Shirt (Red)",
                ],
                "validation": False,
                "width": 150,
            },
        ],
    },
}
"""A mocked response for a successful sheet creation"""
MOCKED_SEARCH_RESULTS = {
    "results": [
        {
            "text": "Sauce Labs Onesie",
            "objectType": "row",
            "objectId": 7859947312768900,
            "parentObjectType": "sheet",
            "parentObjectId": 7340596407887748,
            "parentObjectName": "orders",
            "contextData": ["Mark Monkey Jr"],
            "parentObjectFavorite": True,
        },
        {
            "text": "Sauce Labs Onesie",
            "objectType": "row",
            "objectId": 7721904122619780,
            "parentObjectType": "sheet",
            "parentObjectId": 7340596407887748,
            "parentObjectName": "orders",
            "contextData": ["Gregg Arroyo"],
            "parentObjectFavorite": True,
        },
        {
            "text": "Sauce Labs Onesie",
            "objectType": "row",
            "objectId": 262817239787396,
            "parentObjectType": "sheet",
            "parentObjectId": 7340596407887748,
            "parentObjectName": "orders",
            "contextData": ["Zoya Roche"],
            "parentObjectFavorite": True,
        },
        {
            "text": "Sauce Labs Onesee",
            "objectType": "row",
            "objectId": 2514617053472644,
            "parentObjectType": "sheet",
            "parentObjectId": 7340596407887748,
            "parentObjectName": "orders",
            "contextData": ["Sol Heaton"],
            "parentObjectFavorite": True,
        },
    ],
    "totalCount": 4,
}
