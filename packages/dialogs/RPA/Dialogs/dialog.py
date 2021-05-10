import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Union, Optional

from robot.utils import DotDict  # type: ignore
from .dialog_types import Elements, Result
from .utils import is_input, is_submit


class TimeoutException(RuntimeError):
    """Timeout while waiting for dialog to finish."""


class Dialog:
    """Container for a dialog running in a separate subprocess."""

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
            sys.executable,
            str(Path(__file__).parent / "runner.py"),
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

        if self._process.poll() is None:
            self._process.terminate()

        try:
            stdout, stderr = self._process.communicate(timeout=timeout)
            self._to_result(stdout, stderr)
        except (subprocess.TimeoutExpired, ValueError):
            pass

        if self._process.poll() is None:
            self._process.kill()

        if not self._result:
            self._result = {"error": "Stopped by execution"}

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
                result[key] = fields[key]
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

        out = stdout.decode()
        err = stderr.decode()

        if self._process.returncode != 0:
            self._result = {"error": str(err)}
            return

        try:
            self._result = json.loads(out)
        except ValueError:
            self._result = {"error": f"Malformed response:\n{out}"}
