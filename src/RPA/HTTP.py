from RequestsLibrary import RequestsLibrary


class HTTP(RequestsLibrary):
    """RPA Framework HTTP library which wraps
    `RequestsLibrary <https://hub.robocorp.com/libraries/bulkan-robotframework-requests/>`_ functionality.
    """  # noqa: E501

    def __init__(self, *args, **kwargs):
        RequestsLibrary.__init__(self, *args, **kwargs)
