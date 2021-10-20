import json
import logging
import urllib.parse as urlparse
from json import JSONDecodeError  # pylint: disable=no-name-in-module
from pathlib import Path
from typing import Any, Callable, Dict, List, Union
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

import requests
from requests.exceptions import HTTPError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)


JSONType = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


def url_join(*parts):
    """Join parts of URL and handle missing/duplicate slashes."""
    return "/".join(str(part).strip("/") for part in parts)


def json_dumps(payload: JSONType, **kwargs):
    """Create JSON string in UTF-8 encoding."""
    kwargs.setdefault("ensure_ascii", False)
    return json.dumps(payload, **kwargs)


def is_json_equal(left: JSONType, right: JSONType):
    """Deep-compare two output JSONs."""
    return json_dumps(left, sort_keys=True) == json_dumps(right, sort_keys=True)


def truncate(text: str, size: int):
    """Truncate a string from the middle."""
    if len(text) <= size:
        return text

    ellipsis = " ... "
    segment = (size - len(ellipsis)) // 2
    return text[:segment] + ellipsis + text[-segment:]


def resolve_path(path: str) -> Path:
    """Resolve a string-based path, and replace variables."""
    try:
        safe = str(path).replace("\\", "\\\\")
        path = BuiltIn().replace_variables(safe)
    except RobotNotRunningError:
        pass

    return Path(path).expanduser().resolve()


class RequestsHTTPError(HTTPError):
    """Custom `requests` HTTP error with status code and message."""

    def __init__(
        self, *args, status_code: int = 0, status_message: str = "Error", **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.status_code = status_code
        self.status_message = status_message


class Requests:
    """Wrapper over `requests` 3rd-party with error handling and retrying support."""

    def __init__(self, route_prefix: str, default_headers: dict = None):
        self._route_prefix = route_prefix
        self._default_headers = default_headers

    @staticmethod
    def handle_error(response: requests.Response):
        if response.ok:
            return

        fields = {}
        try:
            fields = response.json()
            while not isinstance(fields, dict):
                # For some reason we might still get a string from the deserialized
                # retrieved JSON payload. If a dictionary couldn't be obtained at all,
                # it will end up raising `RequestsHTTPError`.
                fields = json.loads(fields)
        except (JSONDecodeError, ValueError, TypeError):
            # No `fields` dictionary can be obtained at all.
            try:
                response.raise_for_status()
            except Exception as exc:  # pylint: disable=broad-except
                raise RequestsHTTPError(exc, status_code=response.status_code) from exc

        status_code = 0
        status_message = "Error"
        try:
            status_code = int(fields.get("status", response.status_code))
            status_message = fields.get("error", {}).get("code", "Error")
            reason = fields.get("message") or fields.get("error", {}).get(
                "message", response.reason
            )

            raise HTTPError(f"{status_code} {status_message}: {reason}")
        except Exception as exc:  # pylint: disable=broad-except
            raise RequestsHTTPError(
                str(fields), status_code=status_code, status_message=status_message
            ) from exc

    # pylint: disable=no-self-argument
    def _needs_retry(exc: BaseException) -> bool:
        # Don't retry on server (500/internal/unexpected) and auth errors (401/403).
        no_retry_codes = [400, 401, 403, 409, 500]
        no_retry_messages = ["ERR_UNEXPECTED"]

        if isinstance(exc, RequestsHTTPError):
            if (
                exc.status_code in no_retry_codes
                or exc.status_message in no_retry_messages
            ):
                return False

        return True

    @retry(
        # Retry until either succeed or trying for the fifth time and still failing.
        # So sleep and retry for 4 times at most.
        stop=stop_after_attempt(5),
        # If the exception is no worth retrying or the number of tries is depleted,
        # then re-raise the last raised exception.
        reraise=True,
        # Decide if the raised exception needs retrying or not.
        retry=retry_if_exception(_needs_retry),
        # Produce debugging logging prior to each time we sleep & re-try.
        before_sleep=before_sleep_log(logging.root, logging.DEBUG),
        # Sleep between the tries with a random float amount of seconds like so:
        # 1. [0, 2]
        # 2. [0, 4]
        # 3. [0, 5]
        # 4. [0, 5]
        wait=wait_random_exponential(multiplier=2, max=5),
    )
    def _request(
        self,
        func: Callable[..., requests.Response],
        url: str,
        *args,
        _handle_error: Callable[[requests.Response], None] = None,
        headers: dict = None,
        **kwargs,
    ) -> requests.Response:
        url = urlparse.urljoin(self._route_prefix, url)
        headers = headers if headers is not None else self._default_headers
        handle_error = _handle_error or self.handle_error

        response = func(url, *args, headers=headers, **kwargs)
        handle_error(response)

        return response

    def get(self, *args, **kwargs) -> requests.Response:
        return self._request(requests.get, *args, **kwargs)

    def post(self, *args, **kwargs) -> requests.Response:
        return self._request(requests.post, *args, **kwargs)

    def put(self, *args, **kwargs) -> requests.Response:
        return self._request(requests.put, *args, **kwargs)

    def delete(self, *args, **kwargs) -> requests.Response:
        return self._request(requests.delete, *args, **kwargs)
