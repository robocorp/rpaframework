import os
import platform
import tempfile
from contextlib import contextmanager
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = TESTS_DIR / "resources"
RESULTS_DIR = TESTS_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


if platform.system() == "Windows":
    # workaround for comtypes._shutdown exception
    # https://issueexplorer.com/issue/pywinauto/pywinauto/1083
    import atexit

    import comtypes

    atexit.unregister(comtypes._shutdown)


@contextmanager
def temp_filename(content=None, **kwargs):
    """Create temporary file and return filename, delete file afterwards.
    Needs to close file handle, since Windows won't allow multiple
    open handles to the same file.
    """
    with tempfile.NamedTemporaryFile(delete=False, **kwargs) as fd:
        path = fd.name
        if content:
            fd.write(content)

    try:
        yield path
    finally:
        os.unlink(path)
