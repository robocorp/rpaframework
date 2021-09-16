import json
import logging
import subprocess
import time
from datetime import datetime
from typing import Any, Union, Optional

import robocorp_dialog  # type: ignore
from robot.utils import DotDict  # type: ignore
from .dialog_types import Element, Elements, Result
from .utils import is_input, is_submit


class TimeoutException(RuntimeError):
    """Timeout while waiting for dialog to finish."""


class Dialog:
    """Container for a dialog running in a separate subprocess."""

    # Post-process received result's values.
    POST_PROCESS_MAP = {
        "input-datepicker": lambda value, *, _format, **__: datetime.strptime(
            value, _format  # converts date strings to objects
        ).date(),
    }

    def __init__(
        self,
        elements: Elements,
        title: str,
        width: int,
        height: Union[int, str],
        on_top: bool,
        debug: bool = False,
    ):
        self.logger = logging.getLogger(__name__)
        self.timestamp = time.time()

        auto_height = height == "AUTO"
        if auto_height:
            height = 100

        self._elements = self._to_elements(elements)
        self._options = {
            "title": str(title),
            "width": int(width),
            "height": int(height),
        }
        self._flags = {
            "auto_height": bool(auto_height),
            "on_top": bool(on_top),
            "debug": bool(debug),
        }

        # Flag to indicate if someone has handled the result
        self._is_pending = True
        self._result: Optional[Result] = None
        self._process: Optional[subprocess.Popen] = None

    @property
    def is_pending(self):
        return self._is_pending

    def start(self) -> None:
        if self._process is not None:
            raise RuntimeError("Process already started")

        cmd = [
            robocorp_dialog.executable(),
            json.dumps(self._elements),
        ]

        for option, value in self._options.items():
            cmd.append(f"--{option}")
            cmd.append(str(value))

        for flag, value in self._flags.items():
            if value:
                cmd.append(f"--{flag}")

        # pylint: disable=consider-using-with
        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def stop(self, timeout: int = 15) -> None:
        if self._process is None:
            raise RuntimeError("Process not started")

        if self.poll():
            self.logger.debug("Process already finished")
            return

        self._result = {"error": "Stopped by execution"}
        self._process.terminate()

        try:
            self._process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.communicate()

    def poll(self) -> bool:
        if self._process is None:
            raise RuntimeError("Process not started")

        if self._result is not None:
            return True

        try:
            stdout, stderr = self._process.communicate(timeout=0.2)
        except subprocess.TimeoutExpired:
            return False

        self._to_result(stdout, stderr)
        return True

    def wait(self, timeout: int = 180) -> None:
        if self._process is None:
            raise RuntimeError("Process not started")

        if self._result is not None:
            return

        try:
            stdout, stderr = self._process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as err:
            raise TimeoutException("Reached timeout while waiting for dialog") from err

        self._to_result(stdout, stderr)

    def result(self) -> Result:
        if self._process is None:
            raise RuntimeError("Process not started")

        if self._result is None:
            raise RuntimeError("No result set, call poll() or wait() first")

        self._is_pending = False

        if "error" in self._result:
            raise RuntimeError(self._result["error"])

        result = DotDict()

        fields = self._result["value"]
        for element in self._elements:
            if is_input(element):
                key = element["name"]
                assert key in fields, f"Missing input value for '{key}'"
                result[key] = self._post_process_value(fields[key], element=element)
            elif is_submit(element):
                result["submit"] = fields["submit"]

        assert "submit" in result, "Missing submit value"
        return result

    def _to_elements(self, elements: Elements) -> Elements:
        has_submit = any(is_submit(element) for element in elements)
        has_input = any(is_input(element) for element in elements)

        if not has_submit:
            element = {
                "type": "submit",
                "buttons": ["Submit"] if has_input else ["Close"],
                "default": None,
            }
            elements.append(element)

        return elements

    def _to_result(self, stdout: bytes, stderr: bytes) -> None:
        if self._process is None:
            raise RuntimeError("Process not started")

        out = stdout.decode().strip()
        err = stderr.decode().strip()

        if self._process.returncode != 0:
            self._result = {"error": str(err)}
            return

        if not out:
            # Process didn't have non-zero exit code, but also didn't
            # print JSON output. Possibly flushing issue,
            # unhandled code path, or killed by OS.
            self._result = {"error": "Closed abruptly"}
            return

        try:
            self._result = json.loads(out)
        except ValueError:
            self._result = {"error": f"Malformed response:\n{out}"}

    @classmethod
    def _post_process_value(cls, value: Any, *, element: Element) -> Any:
        func = cls.POST_PROCESS_MAP.get(element["type"])
        if func:
            value = func(value, **element)

        return value
