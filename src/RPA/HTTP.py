from RequestsLibrary import RequestsLibrary


class HTTP(RequestsLibrary):
    """RPA Framework HTTP library which wraps
    `RequestsLibrary <https://hub.robocorp.com/libraries/bulkan-robotframework-requests/>`_ functionality.
    """  # noqa: E501; pylint: disable=line-too-long

    def __init__(self, *args, **kwargs) -> None:
        RequestsLibrary.__init__(self, *args, **kwargs)
