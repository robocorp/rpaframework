import os
import tempfile
from contextlib import contextmanager
import platform
from pathlib import Path


RESOURCE_DIR = Path(__file__).resolve().parent / ".." / "resources"

if platform.system() == "Windows":
    # workaround for comtypes._shutdown exception
    # https://issueexplorer.com/issue/pywinauto/pywinauto/1083
    import atexit
    import comtypes

    atexit.unregister(comtypes._shutdown)


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
