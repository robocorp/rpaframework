import logging
import sys
from importlib.metadata import PackageNotFoundError, version as get_version

from packaging import version as version_parser


LOGGER = logging.getLogger(__name__)


def init_logger(args):
    level_param = "INFO"
    for idx, param in enumerate(args):
        if param in ("-L", "--loglevel"):
            level_param_idx = idx + 1
            if level_param_idx < len(args):
                level_param = args[level_param_idx]
                break
    robot_level = level_param.split(":", 1)[0]
    levels = {
        "TRACE": logging.DEBUG,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "NONE": logging.CRITICAL,
    }
    level = levels.get(robot_level, logging.INFO)
    LOGGER.setLevel(level)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)


def _check_pip_version(min_version: str) -> bool:
    try:
        pip_version = get_version("pip")
    except PackageNotFoundError:
        LOGGER.debug("'pip' is not installed!")
        return False

    if version_parser.parse(pip_version) >= version_parser.parse(min_version):
        LOGGER.debug(
            "Current 'pip' version %s satisfies minimum of %s.",
            pip_version,
            min_version,
        )
        return True

    LOGGER.debug(
        "Current 'pip' version %s doesn't satisfy minimum of %s.",
        pip_version,
        min_version,
    )
    return False


def use_system_certificates():
    """Exposes native system certificate stores.

    Call this before importing anything else.
    """
    # Works with Python 3.10.12, pip 23.2.1 and above.
    py_version = (3, 10, 12)
    pip_version_str = "23.2.1"
    if sys.version_info >= py_version and _check_pip_version(pip_version_str):
        try:
            import truststore  # pylint: disable=import-outside-toplevel
        except ImportError:
            LOGGER.debug("Dependency `truststore` is not installed!")
        else:
            truststore.inject_into_ssl()
            LOGGER.info(
                "Truststore injection done, using system certificate store to validate"
                " HTTPS."
            )
            return

    LOGGER.info(
        "Truststore not in use, HTTPS traffic validated against `certifi` package."
        " (requires Python %s and 'pip' %s at minimum)",
        ".".join(str(nr) for nr in py_version),
        pip_version_str,
    )


init_logger(sys.argv[1:])
