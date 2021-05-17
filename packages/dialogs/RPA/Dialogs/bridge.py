import logging
import platform
import os
import shutil
import subprocess
from functools import wraps
from pathlib import Path
from threading import Timer
from typing import Optional, List, Dict

import webview  # type: ignore
from .dialog_types import Element, Elements, Result


def fatal(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as exc:  # pylint: disable=broad-except
            self.error = str(exc)
            if self.window:
                self.window.destroy()
            raise

    return wrapper


class Bridge:
    """API class for front-end, used to generate bindings
    in Javascript by pywebview.
    """

    def __init__(
        self,
        elements: Elements,
        auto_height: bool = False,
        max_height: int = 800,
        on_top: bool = False,
    ):
        self.logger = logging.getLogger(__name__)
        self.elements: Elements = elements

        self.auto_height = auto_height
        self.max_height = max_height
        self.on_top = on_top

        self.files: Dict[str, List[str]] = {}
        self.result: Optional[Result] = None
        self.error: Optional[str] = None

        # Injected after instantiation
        self.window: Optional[webview.Window] = None

    def _find_by_name(self, name: str) -> Element:
        for element in self.elements:
            if element.get("name") == name:
                return element
        raise ValueError(f"Unknown element: {name}")

    def _set_height(self, height: int) -> None:
        if not self.window:
            return

        height = min(int(height), self.max_height)
        self.logger.debug("Auto-resizing dialog height to %dpx", height)

        # Resize adjusts outer frame, but we care about content
        # TODO: Figure out some more robust solution
        if platform.system() == "Windows":
            height += 40
        elif platform.system() == "Linux":
            height += 1

        self.window.resize(self.window.width, height)

    @fatal
    def getElements(self) -> Elements:
        return self.elements

    @fatal
    def setResult(self, result: Result) -> None:
        self.result = result

        # Copy selected files to destination directory, if one is defined
        for name, files in self.files.items():
            element = self._find_by_name(name)

            dst_dir = element.get("destination")
            if dst_dir is not None:
                paths = []
                os.makedirs(dst_dir, exist_ok=True)
                for src in files:
                    dst = os.path.join(dst_dir, os.path.basename(src))
                    self.logger.debug("Copying file to %s", dst)
                    shutil.copy2(src, dst)
                    paths.append(dst)
                files = paths

            self.result[name] = files

        if self.window:
            # Call destroy() after function has returned, because
            # otherwise the bridge raises an exception
            Timer(0.1, self.window.destroy).start()

    @fatal
    def setHeight(self, height: int) -> None:
        if not self.window:
            return

        if self.auto_height:
            self._set_height(height)

        if not self.on_top:
            self.window.on_top = False

    def openFile(self, path: str) -> None:
        self.logger.info("Opening local file: %s", path)
        if platform.system() == "Windows":
            os.startfile(path)  # type: ignore # pylint: disable=no-member
        elif platform.system() == "Darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])

    def openFileDialog(self, name: str) -> List[str]:
        if not self.window:
            self.logger.error("No window available")
            return []

        element = self._find_by_name(name)
        if element["type"] != "input-file":
            self.logger.error("Attempted to open file dialog for non-file (%s)", name)
            return []

        source = element.get("source")
        source = str(source) if source is not None else str(Path.home())

        allow_multiple = element.get("multiple")
        allow_multiple = bool(allow_multiple) if allow_multiple is not None else False

        file_type = element.get("file_type")
        file_types = [str(file_type)] if file_type is not None else []

        self.logger.debug("Opening file dialog")
        files = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            directory=source,
            allow_multiple=allow_multiple,
            file_types=file_types,
        )

        files = list(files) if files is not None else []
        self.files[name] = files
        return files
