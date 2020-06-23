import logging
from typing import Any
from robot.libraries.BuiltIn import BuiltIn
from RPA.core.utils import required_param


class RobotLogListener:
    """RPA Framework library which implements Robot Framework Listener v2 interface.

    Is used to filter out logging for specified parts of the task execution.
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LISTENER_API_VERSION = 2

    KEYWORDS_TO_PROTECT = ["rpa.robocloud.secrets."]
    INFO_LEVEL_KEYWORDS = []

    def __init__(self) -> None:
        self.ROBOT_LIBRARY_LISTENER = self
        self.logger = logging.getLogger(__name__)
        self.previous_level = None

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

    def _robotize_keyword(self, kw_name: str) -> str:
        """Modifies keyword name for programmatic use.

        Keyword is lowercased and spaces are replaced by underscores.

        :param kw_name: keyword name to robotize
        :return: robotized keyword
        """
        return kw_name.lower().replace(" ", "_")
