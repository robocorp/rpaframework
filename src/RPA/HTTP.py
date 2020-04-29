import logging
from urllib.parse import urlparse
from RequestsLibrary import RequestsLibrary
from RPA.FileSystem import FileSystem


class HTTP(RequestsLibrary):
    """RPA Framework HTTP library which wraps
    `RequestsLibrary <https://github.com/MarketSquare/robotframework-requests/>`_ functionality.
    """  # noqa: E501; pylint: disable=line-too-long

    def __init__(self, *args, **kwargs) -> None:
        RequestsLibrary.__init__(self, *args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.fs = FileSystem()
        self.session_alias_prefix = "rpasession_alias."
        self.current_session_alias = None

    def http_get(
        self,
        url: str,
        target_file: str = None,
        binary: bool = True,
        verify: bool = True,
        force_new_session: bool = False,
    ) -> dict:
        """
        Helper method for `Get Request` which will create session and
        perform Get and stores target file if set by `target_file` parameter.

        Old session will be used if URL scheme and host are same as previously,
        eg. 'https://www.google.fi' part of the URL.

        :param url: target url for Get requesdt
        :param target_file: filepath to save request content, default `None`
        :param binary: if `True` file is saved as binary, default `True`
        :param verify: if SSL verification should be done, default `True`
        :param force_new_session: if new HTTP session should be created, default `False`
        :return: request response
        """
        uc = urlparse(url)

        http_host = f"{uc.scheme}://{uc.netloc}"
        request_alias = f"{self.session_alias_prefix}{uc.scheme}{uc.netloc}"
        url_path = url.replace(http_host, "")
        if force_new_session or not self.session_exists(request_alias):
            self.logger.info("Creating new HTTP session")
            self.create_session(request_alias, http_host, verify=verify)
        else:
            self.logger.info("Using already existing HTTP session")
        self.current_session_alias = request_alias
        response = self.get_request(request_alias, url_path)
        if target_file is not None:
            if binary:
                self.fs.create_binary_file(target_file, response.content)
            else:
                self.fs.create_file(target_file, response.content)
        return response

    def get_current_session_alias(self) -> str:
        """Get request session alias which was used with `HTTP Get` keyword.

        :return: name of session alias
        """
        return self.current_session_alias
