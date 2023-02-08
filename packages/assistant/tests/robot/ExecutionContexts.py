from robot.libraries import BuiltIn


class ExecutionContexts:
    def print_execution_context(self):
        from robot.running.context import EXECUTION_CONTEXTS

        current = EXECUTION_CONTEXTS.current
        print(current)
        BuiltIn.BuiltIn().log_to_console(current)
        return current
