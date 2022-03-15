import importlib
import code
import logging
import os
import string
import sys
import time
import unicodedata
from typing import Any, Optional


# Sentinel value for undefined argument
UNDEFINED = object()


def delay(sleeptime: float = 0.0):
    """Delay execution for given amount of seconds.

    :param sleeptime: seconds as float, defaults to 0
    """
    if delay is None:
        return

    sleeptime = float(sleeptime)

    if sleeptime > 0:
        logging.debug("Sleeping for %f second(s)", sleeptime)
        time.sleep(sleeptime)


def clean_filename(filename: str, replace: str = " ") -> str:
    """Clean filename to valid format which can be used file operations.

    :param filename: name to be cleaned
    :param replace: characters to replace with underscore, defaults to " "
    :return: valid filename
    """
    valid_characters = "-_.()" + string.ascii_letters + string.digits

    for char in replace:
        filename = filename.replace(char, "_")

    clean = unicodedata.normalize("NFKD", filename)
    clean = clean.encode("ASCII", "ignore").decode()
    clean = "".join(char for char in filename if char in valid_characters)

    return clean


def required_env(name: str, default: Any = UNDEFINED) -> str:
    """Load required environment variable.

    :param name: Name of environment variable
    :param default: Value to use if variable is undefined.
                    If not given and variable is undefined, raises KeyError.
    """
    val = os.getenv(name, default)
    if val is UNDEFINED:
        raise KeyError(f"Missing required environment variable: {name}")
    return val


def required_param(param_name: Any = None, method_name: str = None):
    """Check that required parameter is not None"""
    if not isinstance(param_name, list):
        param_name = [param_name]
    if any(p is None for p in param_name):
        raise KeyError("Required parameter(s) missing for kw: %s" % method_name)


def import_by_name(name: str, caller: str = None) -> Any:
    """Import module (or attribute) by name.

    :param name: Import path, e.g. RPA.Robocorp.WorkItems.RobocorpAdapter
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


def interact(expression: Any = None, local: Optional[dict] = None):
    """Interrupts the execution with an interactive shell on `expression`."""
    if expression is not None and not expression:
        return

    sys.stdin, bkp_stdin = sys.__stdin__, sys.stdin
    sys.stdout, bkp_stdout = sys.__stdout__, sys.stdout
    sys.stderr, bkp_stderr = sys.__stderr__, sys.stderr
    try:
        code.interact(local=local or {**globals(), **locals()})
    finally:
        sys.stdin = bkp_stdin
        sys.stdout = bkp_stdout
        sys.stderr = bkp_stderr
