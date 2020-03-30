from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from RPA.RobotLogListener import RobotLogListener

try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


class CustomLibrary:
    SPECIAL_VALUE = 123456

    def __init__(self):
        listener = RobotLogListener()
        listener.register_protected_keywords(["CustomLibrary.special_keyword"])

    def special_keyword(self):
        print("will not be written to log")
        return self.SPECIAL_VALUE

    def assert_library_special_value(self, value):
        assert (
            value == self.SPECIAL_VALUE
        ), f"Value {value} did not match expected {self.SPECIAL_VALUE}"
