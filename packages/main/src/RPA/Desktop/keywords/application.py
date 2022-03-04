import os
import re
import subprocess
from pathlib import Path
from typing import List, Union
from RPA.Desktop import utils
from RPA.Desktop.keywords import LibraryContext, keyword

if utils.is_windows():
    import winreg


def output(*args):
    """Run command and return output."""
    return subprocess.check_output(args).decode().strip()


class Application:
    """Container for launched application."""

    def __init__(self, name: str, args: Union[List[str], str], shell: bool = False):
        self._name = name
        self._args = args
        self._shell = shell
        self._proc = None

    def __str__(self):
        return 'Application("{name}", pid:{pid})'.format(name=self._name, pid=self.pid)

    @property
    def is_running(self):
        if not self._proc:
            return False

        return self._proc.poll() is None

    @property
    def pid(self):
        return self._proc.pid if self._proc else None

    def start(self):
        if self._proc:
            raise RuntimeError("Application already started")

        # pylint: disable=consider-using-with
        self._proc = subprocess.Popen(self._args, shell=self._shell)

    def stop(self):
        if self._proc:
            self._proc.terminate()

    def wait(self, timeout=30):
        if not self._proc:
            raise RuntimeError("Application not started")

        self._proc.communicate(timeout=int(timeout))


class ApplicationKeywords(LibraryContext):
    """Keywords for starting and stopping applications."""

    def __init__(self, ctx):
        super().__init__(ctx)
        self._apps = []

    def _create_app(
        self, name: str, args: Union[List[str], str], shell: bool = False
    ) -> Application:
        cmd = " ".join(args) if not isinstance(args, str) else args
        self.logger.info("Starting application: %s", cmd)

        app = Application(name, args, shell)
        app.start()

        self._apps.append(app)
        return app

    @keyword
    def open_application(self, name_or_path: str, *args) -> Application:
        """Start a given application by name (if in PATH),
        or by path to executable.

        :param name_or_path: Name or path of application
        :param args:         Command line arguments for application
        :returns:            Application instance

        Example:

        .. code-block:: robotframework

            Open application    notepad.exe
            Open application    c:\\path\\to\\program.exe    --example-argument
        """
        name = Path(name_or_path).name
        return self._create_app(name, [name_or_path] + list(args))

    @keyword
    def open_file(self, path: str) -> Application:
        """Open a file with the default application.

        :param path: Path to file

        Example:

        .. code-block:: robotframework

            Open file    orders.xlsx
        """
        path: Path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")

        # TODO: Move implementations to platform-specific adapters
        if utils.is_windows():
            return self._open_default_windows(path)
        elif utils.is_linux():
            return self._open_default_linux(path)
        elif utils.is_macos():
            return self._open_default_macos(path)
        else:
            raise NotImplementedError("Not supported for current system")

    def _open_default_windows(self, path: Path):
        """Open given file with the default Windows application."""
        path = path.resolve()

        try:
            key_root = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, path.suffix)
            key_path = rf"{key_root}\shell\open\command"
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, key_path) as key:
                template = winreg.QueryValueEx(key, "")[0]
        except FileNotFoundError as err:
            raise ValueError(
                f"No default application associated for '{path.name}'"
            ) from err

        # Substitute variables in command, might need to implement
        # handling of more variables (or a more generic solution)
        cmd = os.path.expandvars(template)
        cmd = cmd.replace("%1", str(path))
        cmd = cmd.replace("%L", str(path))

        return self._create_app(path.name, cmd)

    def _open_default_linux(self, path: Path):
        """Open given file with the default Linux application."""
        mimetype = output("xdg-mime", "query", "filetype", path)
        applications = output("xdg-mime", "query", "default", mimetype)
        default = output("xdg-mime", "query", "default", "text/plain")

        def executable(app):
            with open(Path("/usr/share/applications/") / app, encoding="utf-8") as fd:
                matches = re.search(r"\bExec=(\S+)", fd.read(), re.MULTILINE)
                if not matches:
                    raise FileNotFoundError(f"No executable for application '{app}'")
                return matches.group(1)

        for app in applications.split(";") + default.split(";"):
            try:
                exe = executable(app)
                return self._create_app(path.name, [exe, str(path)])
            except FileNotFoundError as err:
                self.logger.info("Launching default failed: %s", err)

        raise RuntimeError(f"No default application associated for '{path.name}'")

    def _open_default_macos(self, path: Path):
        """Open given file with the default MacOS application."""
        # TODO: Find out way to get actual default application,
        #       because open does not expose the actual PID
        return self._create_app(path.name, ["open", "-W", str(path)])

    @keyword
    def close_application(self, app: Application) -> None:
        """Close given application. Needs to be started
        with this library.

        :param app: App instance

        Example:

        .. code-block:: robotframework

            ${word}=    Open file    template.docx
            # Do something with Word
            Close application    ${word}
        """
        if app.is_running:
            app.stop()

    @keyword
    def close_all_applications(self) -> None:
        """Close all opened applications.

        Example:

        .. code-block:: robotframework

            Open file    order1.docx
            Open file    order2.docx
            Open file    order3.docx
            # Do something with Word
            Close all applications
        """
        for app in self._apps:
            if app.is_running:
                app.stop()
