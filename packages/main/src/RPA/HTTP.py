# pylint: disable=C0411,C0412,C0413
import logging
from pathlib import Path
import re
from typing import Any, Optional, Union, List
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
    """The *RPA.HTTP* library extends functionality of the `RequestsLibrary`_.
    See that documentation for several examples of how to issue ``GET``
    requests and utilize the returned ``result`` objects.

    .. _RequestsLibrary: https://marketsquare.github.io/robotframework-requests/doc/RequestsLibrary.html

    This extension provides helper keywords to get an HTTP resource on a
    session. The ``HTTP Get`` and ``Download`` keywords will initiate a
    session if one does not exist for the provided URL, or use an existing
    session. When using these keywords, you do not need to manage
    sessions with ``Create Session``. Session management is still
    required if you use the underlying session keywords, e.g.,
    ``* On Session``.

    """  # noqa: E501

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
        target_file: Optional[str] = None,
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

        .. code-block:: robotframework

            *** Settings ***
            Library    RPA.HTTP

            *** Variables ***
            ${DOWNLOAD_PATH}=   ${OUTPUT DIR}${/}downloads
            ${WORD_EXAMPLE}=    https://file-examples.com/wp-content/uploads/2017/02/file-sample_100kB.doc
            ${EXCEL_EXAMPLE}=   https://file-examples.com/wp-content/uploads/2017/02/file_example_XLS_10.xls

            *** Tasks ***
            Download files with reused session
                # Starts a new session
                HTTP Get    ${WORD_EXAMPLE}    target_file=${DOWNLOAD_PATH}${/}word-example.doc
                # Uses the previous session
                HTTP Get    ${EXCEL_EXAMPLE}    target_file=${DOWNLOAD_PATH}${/}excel-example.xls

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
        """  # noqa: E501
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
        target_file: Optional[str] = None,
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

        .. code-block:: robotframework

            *** Settings ***
            Library    RPA.HTTP

            *** Variables ***
            ${DOWNLOAD_PATH}=   ${OUTPUT DIR}${/}downloads
            ${WORD_EXAMPLE}=    https://file-examples.com/wp-content/uploads/2017/02/file-sample_100kB.doc
            ${EXCEL_EXAMPLE}=   https://file-examples.com/wp-content/uploads/2017/02/file_example_XLS_10.xls

            *** Tasks ***
            Download files with reused session with provided file names
                # Starts a new session
                Download    ${WORD_EXAMPLE}    target_file=${DOWNLOAD_PATH}
                # Uses the previous session
                Download    ${EXCEL_EXAMPLE}    target_file=${DOWNLOAD_PATH}
                # Above files are downloaded using the same names as they have
                # on the remote server.

        :param url: target URL for GET request
        :param target_file: filepath to save request content, default ``None``
        :param verify: if SSL verification should be done, default ``True``,
         a CA_BUNDLE path can also be provided
        :param force_new_session: if new HTTP session should be created,
         default ``False``
        :param overwrite: used together with ``target_file``, if ``True`` will overwrite
         the target file, default ``False``
        :param stream: if ``False`` the response content will be immediately downloaded
        :return: request response as a dict
        """  # noqa: E501
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

    def check_vulnerabilities(self) -> List:
        """Check for possible vulnerabilities in the installed runtime
        environment packages.

        Currently will check only for OpenSSL version and outputs warning message on any
        discovered vulnerability.

        :return: list of all check results

        .. code-block:: robotframework

            *** Tasks ***
            Vulnerability Check
                ${results}=    Check Vulnerabilities
                FOR    ${result}    IN    @{results}
                    Log To Console    TYPE: ${result}[type]
                    Log To Console    VULNERABLE: ${result}[vulnerable]
                    Log To Console    MESSAGE: ${result}[message]
                END
        """
        all_results = []
        vulnerable, message = self._check_openssl_vulnerabilities()
        all_results.append(
            {"type": "OpenSSL", "vulnerable": vulnerable, "message": message}
        )
        if vulnerable:
            self.logger.warning(message)
        return all_results

    def _check_openssl_vulnerabilities(self):
        message = "No OpenSSL detected"
        try:
            import ssl  # pylint: disable=C0415

            open_ssl_version = re.match(
                r"OpenSSL (\d+)\.(\d+)\.(\d+).*", ssl.OPENSSL_VERSION
            )
            if open_ssl_version and len(open_ssl_version.groups()) == 3:
                major, minor, fix = [int(val) for val in open_ssl_version.groups()]
                if major == 3 and minor == 0 and (0 <= fix <= 6):
                    return True, (
                        rf"Dependency with HIGH severity vulnerability detected: '{ssl.OPENSSL_VERSION}'. "  # noqa: E501
                        "For more information see https://robocorp.com/docs/faq/openssl-cve-2022-11-01"  # noqa: E501
                    )
            message = ssl.OPENSSL_VERSION
        except ImportError:
            pass
        return False, message
