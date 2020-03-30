import importlib
import logging
import os
import string
import time
import unicodedata

# Sentinel value for undefined argument
UNDEFINED = object()


def delay(sleeptime=0):
    """delay execution for given seconds

    :param sleeptime: seconds as integer, defaults to 0
    """
    if sleeptime > 0:
        logging.debug(f"sleeping for {sleeptime} second(s)")
        time.sleep(sleeptime)


def clean_filename(filename, replace=" "):
    """clean filename to valid format which can be used file operations

    :param filename: name to be cleaned
    :param replace: characters to replace with underscore, defaults to " "
    :return: valid filename
    """
    valid_filename_chars = "-_.()%s%s" % (string.ascii_letters, string.digits)
    # replace spaces
    for r in replace:
        filename = filename.replace(r, "_")

    # keep only valid ascii chars
    cleaned_filename = (
        unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore").decode()
    )
    # keep only whitelisted chars
    cleaned_filename = "".join(c for c in cleaned_filename if c in valid_filename_chars)
    return cleaned_filename


def required_env(name, default=UNDEFINED):
    """Load required environment variable."""
    val = os.getenv(name, default)
    if val is UNDEFINED:
        raise KeyError(f"Missing required environment variable: {name}")
    return val


def import_by_name(name, caller=None):
    """Import module (or attribute) by name.

    :param name: Import path, e.g. RPA.WorkItems.RobocloudAdapter
    """
    name = str(name)

    # Attempt import as path module
    try:
        return importlib.import_module(name)
    except ImportError:
        pass

    # Attempt import from calling file
    if caller is not None:
        try:
            module = importlib.import_module(caller)
            return getattr(module, name)
        except AttributeError:
            pass

    # Attempt import as path to attribute inside module
    if "." in name:
        try:
            path, attr = name.rsplit(".", 1)
            module = importlib.import_module(path)
            return getattr(module, attr)
        except (AttributeError, ImportError):
            pass

    raise ValueError(f"No module/attribute with name: {name}")
