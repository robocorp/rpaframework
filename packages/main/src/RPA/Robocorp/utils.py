import json
import logging
import urllib.parse as urlparse
from pathlib import Path
from typing import Any, Callable, Dict, List, Union
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

import requests
from requests.exceptions import HTTPError
from tenacity import before_log, retry, stop_after_attempt, wait_exponential


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
            if not isinstance(fields, dict):
                # For some reason we might still get a string from the deserialized
                # retrieved JSON payload.
                fields = json.loads(fields)
        except ValueError:
            response.raise_for_status()

        try:
            status_code = fields.get("status", response.status_code)
            status_msg = fields.get("error", {}).get("code", "Error")
            reason = fields.get("message") or fields.get("error", {}).get(
                "message", response.reason
            )

            raise HTTPError(f"{status_code} {status_msg}: {reason}")
        except Exception as err:  # pylint: disable=broad-except
            raise HTTPError(str(fields)) from err

    @retry(
        # try, wait 1s, retry, wait 2s, retry, wait 4s, retry, give-up
        stop=stop_after_attempt(4),
        wait=wait_exponential(min=1, max=4),
        before=before_log(logging.root, logging.DEBUG),
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
