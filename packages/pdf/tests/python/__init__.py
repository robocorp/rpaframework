import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from RPA.PDF import PDF


RESOURCE_DIR = Path(__file__).resolve().parent / ".." / "resources"


@pytest.fixture
def library():
    return PDF()


class TestFiles:
    imagesandtext_pdf = RESOURCE_DIR / "imagesandtext.pdf"
    invoice_pdf = RESOURCE_DIR / "invoice.pdf"
    vero_pdf = RESOURCE_DIR / "vero.pdf"
    customs_pdf = RESOURCE_DIR / "customs.pdf"
    pytest_pdf = RESOURCE_DIR / "18467.pdf"
    loremipsum_pdf = RESOURCE_DIR / "LoremIpsum.pdf"
    encrypted_pdf = RESOURCE_DIR / "encrypted.pdf"
    seal_of_approval = RESOURCE_DIR / "approved.png"
    big_nope = RESOURCE_DIR / "big_nope.png"


@contextmanager
def temp_filename(content=None):
    """Create temporary file and return filename, delete file afterwards.
    Needs to close file handle, since Windows won't allow multiple
    open handles to the same file.
    """
    with tempfile.NamedTemporaryFile(delete=False) as fd:
        path = fd.name
        if content:
            fd.write(content)

    try:
        yield path
    finally:
        try:
            os.unlink(path)
        except PermissionError:
            pass
