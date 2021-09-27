import logging
import warnings
from typing import Union, List

try:
    from robot.libraries.BuiltIn import BuiltIn
    from robot.running.context import EXECUTION_CONTEXTS
except ModuleNotFoundError:
    BuiltIn = None
    EXECUTION_CONTEXTS = None

from RPA.core.helpers import required_param


def deprecation(message):
    """Emits once a deprecation warning log given the provided `message`."""
    logging.captureWarnings(True)
    try:
        warnings.warn(message, FutureWarning, stacklevel=2)
    finally:
        logging.captureWarnings(False)


class RobotLogListener:
    """`RobotLogListener` is a library for controlling logging during
    a Robot Framework execution using the listener API.

    **About keyword parameters**

    Parameters `names` and `keywords` for keywords `Mute Run On Failure` and `Register Protected Keywords`
    do not need to be full names of keywords, ie. all keywords matching even partially will be affected.
    `Run Keyword` would match all `BuiltIn` library keywords (17 keywords in RF 3.2.1) and of course all
    `Run Keyword` named keywords in any resource and/or library file which are imported would be matched also.

    **Mute Run On Failure**

    This keyword is to be used specifically with `RPA.Browser.Selenium` library, which extends
    `SeleniumLibrary`.  Normally most of the `SeleniumLibrary` keywords execute `run_on_failure`
    behaviour, which can be set at library initialization. By default this behaviour is running
    `Capture Page Screenshot` keyword on failure.

    In the example task `Check the official website` below the keyword `Run Keyword` is muted and when
    it runs the keyword `Element Should Be Visible` then those failures do not create page screenshots
    into log file.

    It is also possible to change default failure behaviour by giving parameter
    `optional_keyword_to_run` for `Mute Run On Failure`, see task `Check the official website with error log`.
    This optional keyword would be then executed on failure. Due to the underlying `SeleniumLibrary`
    implementation this keyword can't have arguments.

    Example of using `Mute Run On Failure` without and with optional keyword to run.

    .. code-block:: robotframework

       *** Settings ***
       Library         RPA.Browser.Selenium
       Library         RPA.RobotLogListener
       Task Setup      Set Task Variable   ${TRIES}   1
       Task Teardown   Close All Browsers

       *** Tasks ***
       Check the official website
          Mute Run On Failure   Run Keyword
          Open Available Browser   https://www.robocorp.com
          Check for visible element
          Capture Page Screenshot

       Check the official website with error log
          Mute Run On Failure   Run Keyword  optional_keyword_to_run=Log tries
          Open Available Browser   https://www.robocorp.com
          Check for visible element
          Capture Page Screenshot

       *** Keywords ***
       Check for visible element
          FOR  ${idx}  IN RANGE  1   20
             Set Task Variable   ${TRIES}   ${idx}
             ${status}   Run Keyword And Return Status   Element Should Be Visible  id:xyz
             Exit For Loop If   '${status}' == 'PASS'
             Sleep  2s
          END

       Log tries
          Log  Checked element visibility ${TRIES} times

    **Register Protected Keywords**

    This keyword is used to totally disable logging for named keywords. In the example below
    the keyword `This will not output` is protected and it will not be logging into Robot Framework
    log files.

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library         RPA.RobotLogListener

        *** Tasks ***
        Protecting keywords
           This will not output        # will output because called before register
           Register Protected Keywords    This will not output
           This will not output        # is now registered
           This will output

        *** Keywords ***
        This will not output
           Log   1

        This will output
           Log   2

    **Python**

    .. code-block:: python

        from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
        from RPA.RobotLogListener import RobotLogListener

        try:
           BuiltIn().import_library("RPA.RobotLogListener")
        except RobotNotRunningError:
           pass

        class CustomLibrary:

           def __init__(self):
              listener = RobotLogListener()
              listener.register_protected_keywords(
                    ["CustomLibrary.special_keyword"]
              )

           def special_keyword(self):
              print('will not be written to log')
              return 'not shown in the log'
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"
    ROBOT_LISTENER_API_VERSION = 2

    KEYWORDS_TO_PROTECT = ["rpa.robocloud.secrets.", "rpa.robocorp.vault."]
    KEYWORDS_TO_MUTE = []
    INFO_LEVEL_KEYWORDS = []

    def __init__(self) -> None:
        self.ROBOT_LIBRARY_LISTENER = self
        self.logger = logging.getLogger(__name__)
        self.stack = []

        # Run-on-failure
        self.muted_keyword = None
        self.muted_optionals = []
        self.muted_previous = {}

    def only_info_level(self, names: Union[str, List] = None):
        """Register keywords that are allowed only INFO level logging

        :param names: list of keywords to protect
        """
        required_param(names, "only_info_level")
        if not isinstance(names, list):
            names = [names]

        for name in names:
            normalized = self._normalize(name)
            if normalized not in self.INFO_LEVEL_KEYWORDS:
                self.INFO_LEVEL_KEYWORDS.append(normalized)

    def register_protected_keywords(self, names: Union[str, List] = None) -> None:
        """Register keywords that are not going to be logged into Robot Framework logs.

        :param names: list of keywords to protect
        """
        required_param(names, "register_protected_keywords")
        if not isinstance(names, list):
            names = [names]

        for name in names:
            normalized = self._normalize(name)
            if normalized not in self.KEYWORDS_TO_PROTECT:
                self.KEYWORDS_TO_PROTECT.append(normalized)

    def mute_run_on_failure(
        self, keywords: Union[str, List] = None, optional_keyword_to_run: str = None
    ) -> None:
        """Set keywords which should not execute `SeleniumLibrary`
        default behaviour of running keyword on failure.

        :param keywords: list of keywords to mute
        :param optional_keyword_to_run: name of the keyword to execute
            if keyword defined by `keywords` fail

        Keyword names do not need to be full names of keywords, ie. all keywords
        matching even partially will be affected. `Run Keyword` would match all
        `BuiltIn` library keywords (17 keywords in RF 3.2.1) and of course all
        `Run Keyword` named keywords in any resource and/or library file which
        are imported would be matched also.

        By default `SeleniumLibrary` executes `Capture Page Screenshot`
        on failure.

        If `optional_keyword_to_run` is not given then nothing is done
        on failure, but this can be set to override `SeleniumLibrary`
        default behaviour for a set of keywords.
        """
        if not self._is_robot_running():
            raise RuntimeError("Not supported outside Robot Framework")

        required_param(keywords, "mute_run_on_failure")
        if not isinstance(keywords, list):
            keywords = [keywords]

        for keyword in keywords:
            normalized = self._normalize(keyword)
            if normalized not in self.KEYWORDS_TO_MUTE:
                self.KEYWORDS_TO_MUTE.append(normalized)

        for library in ("RPA.Browser", "RPA.Browser.Selenium"):
            status, instance = BuiltIn().run_keyword_and_ignore_error(
                "get_library_instance", library
            )
            if status == "PASS":
                self.muted_optionals.append((instance, optional_keyword_to_run))

    def start_keyword(self, name, attributes):  # pylint: disable=W0613
        """Listener method for keyword start.

        :param name: keyword name
        :param attributes: keyword attributes

        If `name` exists in the protected keywords list then log level is
        temporarily set to NONE.
        """
        if not self._is_robot_running():
            return

        normalized = self._normalize(name)

        if any(name in normalized for name in self.KEYWORDS_TO_PROTECT):
            self.logger.info("Protecting keyword: %s", name)
            old = BuiltIn().set_log_level("NONE")
            self.stack.append((normalized, old))
        elif any(name in normalized for name in self.INFO_LEVEL_KEYWORDS):
            current = BuiltIn().get_variable_value("${LOG_LEVEL}")
            if current not in ("WARN", "ERROR", "NONE"):
                old = BuiltIn().set_log_level("INFO")
                self.stack.append((normalized, old))

        # Run-on-failure

        if self.muted_keyword:
            return

        previous = {}
        for library, optional in self.muted_optionals:
            if any(name in normalized for name in self.KEYWORDS_TO_MUTE):
                keyword = library.register_keyword_to_run_on_failure(optional)
                previous[library.__class__.__name__] = keyword

        if previous:
            self.logger.debug("Muting failures before keyword: %s", name)
            self.muted_keyword = normalized
            self.muted_previous = previous

    def end_keyword(self, name, attributes):  # pylint: disable=W0613
        """Listener method for keyword end.

        :param name: keyword name
        :param attributes: keyword attributes

        If `name` exists in the protected keywords list then log level is
        restored back to level it was before settings to NONE.
        """
        if not self._is_robot_running():
            return

        normalized = self._normalize(name)

        if self.stack and self.stack[-1][0] == normalized:
            _, old = self.stack.pop()
            BuiltIn().set_log_level(old)

        # Run-on-failure

        if normalized != self.muted_keyword:
            return

        self.logger.debug("Un-muting failures after keyword: %s", name)
        for library, _ in self.muted_optionals:
            previous = self.muted_previous.get(library.__class__.__name__)
            if previous:
                library.register_keyword_to_run_on_failure(previous)

        self.muted_keyword = None
        self.muted_previous = {}

    def _normalize(self, name: str) -> str:
        """Modifies keyword name for programmatic use.

        Keyword is lowercased and spaces are replaced by underscores.

        :param name: keyword name to normalize
        :return: normalized keyword
        """
        return name.lower().replace(" ", "_")

    def _is_robot_running(self):
        return BuiltIn is not None and EXECUTION_CONTEXTS.current is not None
