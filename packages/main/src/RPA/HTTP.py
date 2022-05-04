# pylint: disable=C0411,C0412,C0413
import logging
from pathlib import Path
from typing import Any, Union
from urllib.parse import urlparse

import RequestsLibrary.log
from RequestsLibrary.utils import is_file_descriptor
from robot.api import logger

from RPA.core.notebook import notebook_file
from RPA.FileSystem import FileSystem

LOG_CHAR_LIMIT = 10000


def log_response(response):
    logger.debug(
        "%s Response : url=%s \n " % (response.request.method.upper(), response.url)
        + "status=%s, reason=%s \n " % (response.status_code, response.reason)
        + "headers=%s \n " % response.headers
        + "body=%s \n " % format_data_to_log_string(response.text)
    )


def log_request(response):
    request = response.request
    if response.history:
        original_request = response.history[0].request
        redirected = "(redirected) "
    else:
        original_request = request
        redirected = ""
    logger.debug(
        "%s Request : " % original_request.method.upper()
        + "url=%s %s\n " % (original_request.url, redirected)
        + "path_url=%s \n " % original_request.path_url
        + "headers=%s \n " % original_request.headers
        + "body=%s \n " % format_data_to_log_string(original_request.body)
    )


def format_data_to_log_string(data, limit=LOG_CHAR_LIMIT):

    if not data:
        return None

    if is_file_descriptor(data):
        return repr(data)

    if len(data) > limit and logging.getLogger().level > 10:
        data = (
            "%s... (set the log level to DEBUG or TRACE to see the full content)"
            % data[:limit]
        )

    return data


RequestsLibrary.log.log_response = log_response
RequestsLibrary.log.log_request = log_request


from RequestsLibrary import RequestsLibrary  # noqa: E402

# NOTE. Above logging changes are related to. Especially on Automation Studio
# extensive INFO level logging makes readability problematic.
# https://github.com/MarketSquare/robotframework-requests/issues/353


class HTTP(RequestsLibrary):
    """RPA Framework HTTP library that extends functionality of RequestsLibrary,
    for more information see: https://github.com/MarketSquare/robotframework-requests
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "reST"

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
        verify: Union[bool, str] = True,
        force_new_session: bool = False,
        overwrite: bool = False,
        stream: bool = False,
        **kwargs,
    ) -> dict:
        """
        A helper method for ``Get Request`` that will create a session, perform GET
        request, and store the target file, if set by the ``target_file`` parameter.

        The old session will be used if the URL scheme and the host are the same as
        previously, e.g., 'https://www.google.fi' part of the URL.

        :param url: target URL for GET request
        :param target_file: filepath to save request content, default ``None``
        :param verify: if SSL verification should be done, default ``True``,
            a CA_BUNDLE path can also be provided
        :param force_new_session: if new HTTP session should be created,
            default ``False``
        :param overwrite: used together with ``target_file``, if ``True`` will overwrite
            the target file, default ``False``
        :param stream: if ``False``, the response content will be immediately downloaded
        :return: request response as a dict
        """
        uc = urlparse(url)

        http_host = f"{uc.scheme}://{uc.netloc}"
        request_alias = f"{self.session_alias_prefix}{uc.scheme}{uc.netloc}"
        url_path = url.replace(http_host, "")

        if force_new_session or not self.session_exists(request_alias):
            self.logger.info("Creating a new HTTP session")
            self.create_session(request_alias, http_host, verify=verify)
        else:
            self.logger.info("Using already existing HTTP session")

        self.current_session_alias = request_alias
        response = self.get_on_session(request_alias, url_path, stream=stream, **kwargs)

        if target_file is not None:
            self._create_or_overwrite_target_file(
                target_file, response.content, overwrite
            )

        return response

    def _create_or_overwrite_target_file(
        self,
        path: str,
        response: Any,
        overwrite: bool,
    ) -> None:
        CHUNK_SIZE = 32768
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        file_exists = Path(path).is_file()
        if not file_exists or (file_exists and overwrite):
            with open(path, "wb") as f:
                for chunk in response.iter_content(CHUNK_SIZE):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
        notebook_file(path)

    def get_current_session_alias(self) -> str:
        """Get request session alias that was used with the ``HTTP Get`` keyword.

        :return: name of session alias as a string
        """
        return self.current_session_alias

    def download(
        self,
        url: str,
        target_file: str = None,
        verify: Union[bool, str] = True,
        force_new_session: bool = False,
        overwrite: bool = False,
        stream: bool = False,
        **kwargs,
    ) -> dict:
        """An alias for the ``HTTP Get`` keyword.

        The difference in use is that the URL is always downloaded based on
        the URL path (even without ``target_file``). If there is a filename
        in the path, then that is used as ``target_file`` to save to. By default,
        the filename will be "downloaded.html".

        :param url: target URL for GET request
        :param target_file: filepath to save request content, default ``None``
        :param verify: if SSL verification should be done, default ``True``,
            a CA_BUNDLE path can also be provided
        :param force_new_session: if new HTTP session should be created,
            default ``False``
        :param overwrite: used together with ``target_file``, if ``True`` will overwrite
            the target file, default ``False``
        :param stream`` if ``False``, the response content will
            be immediately downloaded
        :return: request response as a dict
        """
        response = self.http_get(
            url,
            verify=verify,
            force_new_session=force_new_session,
            overwrite=overwrite,
            stream=stream,
            **kwargs,
        )

        dirname = Path()
        filename = None

        if target_file is not None:
            target = Path(target_file)
            if target.is_dir():
                dirname = target
            else:
                dirname = target.parent
                filename = target.name

        if filename is None:
            filename = urlparse(url).path.rsplit("/", 1)[-1] or "downloaded.html"

        self._create_or_overwrite_target_file(dirname / filename, response, overwrite)

        return response
