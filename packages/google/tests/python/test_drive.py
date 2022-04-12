# import os
from . import RESOURCES_DIR
from resources.google_testvars import testvars
from RPA.Cloud.Google import Google

import pytest

DEFAULT_FOLDER = testvars["DEFAULT_DRIVE_PARENT_FOLDER"]


@pytest.fixture
def library():
    lib = Google()
    lib.init_drive(
        service_account="C:\\koodi\\testground\\rajobit\\serviceaccount.json"
    )
    yield lib
    # query = "name = 'okta.png'"
    # files = lib.search_drive_files(query, recurse=True)
    # for f in files:
    #    lib.delete_drive_file(file_id=f["id"], multiple_ok=True)


def test_drive_get_folder_id_of_known_folder(library: Google):
    file_id = library.get_drive_folder_id(DEFAULT_FOLDER)
    assert file_id is not None


def test_drive_get_folder_id_of_non_existing_folder(library: Google):
    file_id = library.get_drive_folder_id("This does not exist for the pytests")
    assert file_id is None


def test_upload_file_into_sub_folder(library: Google):
    library.upload_drive_file(
        RESOURCES_DIR / "okta.png",
        folder="sub1",
        parent_folder=DEFAULT_FOLDER,
        make_dir=True,
    )
    files = library.search_drive_files("name = 'okta.png'", recurse=True)
    assert len(files) == 1
