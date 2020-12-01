import platform
import time


class Buffer:
    """A context manager that waits for a guaranteed minimum interval
    between the previous exit and next enter.
    """

    def __init__(self, logger, interval=0.1):
        self.logger = logger
        self.default = float(interval)
        self.interval = self.default
        self.previous = 0.0

    def __call__(self, interval=None):
        if interval is not None:
            self.interval = float(interval)

        return self

    def __enter__(self):
        duration = time.time() - self.previous
        if duration < self.interval:
            sleep_time = self.interval - duration
            self.logger.debug("Buffering input for %.2f seconds", sleep_time)
            time.sleep(sleep_time)

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.previous = time.time()
        self.interval = self.default


def is_windows():
    return platform.system() == "Windows"


def is_macos():
    return platform.system() == "Darwin"


def is_linux():
    return platform.system() == "Linux"
