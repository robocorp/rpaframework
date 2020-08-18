import logging
from typing import Any
from robot.libraries.BuiltIn import BuiltIn

from RPA.core.helpers import required_param


class RobotLogListener:
    """RPA Framework library which implements Robot Framework Listener v2 interface.

    Is used to filter out logging for specified parts of the task execution.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 2

    KEYWORDS_TO_PROTECT = ["rpa.robocloud.secrets."]
    KEYWORDS_TO_MUTE = []
    INFO_LEVEL_KEYWORDS = []

    def __init__(self) -> None:
        self.ROBOT_LIBRARY_LISTENER = self
        self.logger = logging.getLogger(__name__)
        self.previous_level = None
        self.previous_kw = None
        self.rpabrowser_instance = None
        self.optional_keyword_to_run_failure = None

    def only_info_level(self, names: Any = None):
        """Register keywords that are allowed only INFO level logging

        :param names: list of keywords to protect
        """
        required_param(names, "only_info_level")
        if not isinstance(names, list):
            names = [names]
        for name in names:
            robotized_keyword = self._robotize_keyword(name)
            if robotized_keyword not in self.INFO_LEVEL_KEYWORDS:
                self.INFO_LEVEL_KEYWORDS.append(robotized_keyword)

    def register_protected_keywords(self, names: Any = None) -> None:
        """Register keywords that are not going to be logged into Robot Framework logs.

        :param names: list of keywords to protect
        """
        required_param(names, "register_protected_keywords")
        if not isinstance(names, list):
            names = [names]
        for name in names:
            robotized_keyword = self._robotize_keyword(name)
            if robotized_keyword not in self.KEYWORDS_TO_PROTECT:
                self.KEYWORDS_TO_PROTECT.append(robotized_keyword)

    def mute_run_on_failure(
        self, keywords: Any = None, optional_keyword_to_run: str = None
    ) -> None:
        """Set keywords which should not execute `SeleniumLibrary`
        default behaviour of running keyword on failure.

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

        :param keywords: list of keywords to mute
        :param optional_keyword_to_run: name of the keyword to execute
                                        if keyword defined by `keywords` fail
        """
        required_param(keywords, "mute_run_on_failure")
        if not isinstance(keywords, list):
            keywords = [keywords]
        for keyword in keywords:
            robotized_keyword = self._robotize_keyword(keyword)
            if robotized_keyword not in self.KEYWORDS_TO_MUTE:
                self.KEYWORDS_TO_MUTE.append(robotized_keyword)
        status, rpabrowser = BuiltIn().run_keyword_and_ignore_error(
            "get_library_instance", "RPA.Browser"
        )
        self.rpabrowser_instance = rpabrowser if status == "PASS" else None
        self.optional_keyword_to_run_failure = optional_keyword_to_run

    def start_keyword(self, name, attributes):  # pylint: disable=W0613
        """Listener method for keyword start.

        If `name` exists in the protected keywords list then log level is
        temporarily set to NONE.

        :param name: keyword name
        :param attributes: keyword attributes
        """
        robotized_keyword = self._robotize_keyword(name)
        if any(k in robotized_keyword for k in self.KEYWORDS_TO_PROTECT):
            self.logger.info("protecting keyword: %s", robotized_keyword)
            self.previous_level = BuiltIn().set_log_level("NONE")
        elif any(k in robotized_keyword for k in self.INFO_LEVEL_KEYWORDS):
            self.previous_level = BuiltIn().set_log_level("INFO")
        if self.rpabrowser_instance and any(
            k in robotized_keyword for k in self.KEYWORDS_TO_MUTE
        ):
            # pylint: disable=C0301
            self.previous_kw = self.rpabrowser_instance.register_keyword_to_run_on_failure(  # noqa: E501
                self.optional_keyword_to_run_failure
            )

    def end_keyword(self, name, attributes):  # pylint: disable=W0613
        """Listener method for keyword end.

        If `name` exists in the protected keywords list then log level is
        restored back to level it was before settings to NONE.

        :param name: keyword name
        :param attributes: keyword attributes
        """
        robotized_keyword = self._robotize_keyword(name)
        if any(k in robotized_keyword for k in self.KEYWORDS_TO_PROTECT):
            BuiltIn().set_log_level(self.previous_level)
        if self.rpabrowser_instance and any(
            k in robotized_keyword for k in self.KEYWORDS_TO_MUTE
        ):
            self.rpabrowser_instance.register_keyword_to_run_on_failure(
                self.previous_kw
            )

    def _robotize_keyword(self, kw_name: str) -> str:
        """Modifies keyword name for programmatic use.

        Keyword is lowercased and spaces are replaced by underscores.

        :param kw_name: keyword name to robotize
        :return: robotized keyword
        """
        return kw_name.lower().replace(" ", "_")
