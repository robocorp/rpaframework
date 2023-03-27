import logging
from typing import Any, Callable, Optional, Union

from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from robot.errors import RobotError


class CallbackRunner:
    """provides helper functionality for running Robot and Python callbacks in
    RPA.Assistant."""

    def __init__(self, client) -> None:
        self.logger = logging.getLogger(__name__)
        self._client = client

    def _python_callback(
        self, function: Callable[[Any], None], *args, **kwargs
    ) -> Callable[[], None]:
        """wrapper code that is used to add wrapping for user functions when binding
        them to be run by buttons
        """

        def func_wrapper() -> None:
            return self._run_python_callback(function, *args, **kwargs)

        return func_wrapper

    def python_validation(
        self, function: Callable[[Any], Optional[str]]
    ) -> Callable[[Any], Optional[str]]:
        """wrapper code that is used to add wrapping for user functions when binding
        them to be run on validations buttons
        """

        def func_wrapper(value) -> Optional[str]:
            return self._run_python_callback(function, value)

        return func_wrapper

    def _run_python_callback(self, function: Callable, *args, **kwargs):
        try:
            return function(*args, **kwargs)

        # This can be anything since it comes from the user function, we don't
        # want to let the user function crash the UI
        except Exception as err:  # pylint: disable=broad-except
            self.logger.error(f"Error calling Python function {function.__name__}")
            self.logger.error(err)
        finally:
            self._client.unlock_elements()
            self._client.flet_update()
        return None

    def _robot_callback(self, kw_name: str, *args, **kwargs) -> Callable[[], None]:
        """wrapper code that is used to add wrapping for user functions when binding
        them to be run by buttons
        """

        def func_wrapper() -> None:
            return self._run_robot_callback(kw_name, *args, **kwargs)

        return func_wrapper

    def robot_validation(self, kw_name: str) -> Callable[[Any], Optional[str]]:
        """wrapper code that is used to add wrapping for user functions when binding
        them to be run on validation
        """

        def func_wrapper(value) -> Optional[str]:
            return self._run_robot_callback(kw_name, value)

        return func_wrapper

    def _run_robot_callback(self, kw_name: str, *args, **kwargs):
        try:
            self._client.lock_elements()
            self._client.flet_update()
            return BuiltIn().run_keyword(kw_name, *args, **kwargs)
        except RobotNotRunningError:
            self.logger.error(
                f"Robot Framework not running so cannot call keyword {kw_name}"
            )
        except RobotError as e:
            self.logger.error(f"Error calling robot keyword {kw_name}")
            self.logger.error(e)
        # This can be anything since it comes from the user function, we don't
        # want to let the user function crash the UI
        except Exception as err:  # pylint: disable=broad-except
            self.logger.error(f"Unexpected error running robot keyword {kw_name}")
            self.logger.error(err)
        finally:
            self._client.unlock_elements()
            self._client.flet_update()
        return None

    def queue_fn_or_kw(self, function: Union[Callable, str], *args, **kwargs):
        """Check if function is a Python function or a Robot Keyword, and schedule it
        for execution appropriately.
        """
        if self._client.pending_operation:
            self.logger.error("Can't have more than one pending operation.")
            return
        self._client.lock_elements()
        self._client.flet_update()

        if isinstance(function, Callable):
            self._client.pending_operation = self._python_callback(
                function, *args, **kwargs
            )
        else:
            self._client.pending_operation = self._robot_callback(
                function, *args, **kwargs
            )
