import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


RESOURCE_DIR = Path(__file__).resolve().parent / ".." / "resources"


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
        os.unlink(path)
