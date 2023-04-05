import platform

# pylint: disable=unused-import
from RPA.core.windows.helpers import IS_WINDOWS, get_process_list  # noqa: F401


def call_attribute_if_available(object_name, attribute_name):
    if hasattr(object_name, attribute_name):
        return getattr(object_name, attribute_name)()
    return None


def get_win_version() -> str:
    """Windows only utility which returns the current Windows major version."""
    # Windows terminal `ver` command is bugged, until that's fixed, check by build
    #  number. (the same applies for `platform.version()`)
    version_parts = platform.version().split(".")
    major = version_parts[0]
    if major == "10" and int(version_parts[2]) >= 22000:
        major = "11"

    return major
