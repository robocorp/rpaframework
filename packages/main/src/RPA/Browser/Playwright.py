try:
    from Browser import Browser  # noqa: F401 # pylint: disable=unused-import
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "Please install robotframework-browser following these instructions ..."
    ) from None
