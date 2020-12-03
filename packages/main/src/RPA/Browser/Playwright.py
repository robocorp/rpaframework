try:
    from Browser import Browser
except ModuleNotFoundError:
    raise ModuleNotFoundError(
        "Please install robotframework-browser following these instructions ..."
    ) from None
