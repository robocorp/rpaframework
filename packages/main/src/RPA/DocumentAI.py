"""Generic Intelligent Document Processing generic keywords capable of working with
various engines.

Currently, supporting the following:
- Google Document AI
- Base64
- Nanonets
"""


from robot.api.deco import keyword, library

from RPA.JSON import JSONType


# FIXME: Type annotations.


@library
class DocumentAI:
    """<summary>

    <details>
    <engines examples>
    <extra requirements>
    <about models/processors>
    <input and output>
    <service setup>
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __int__(self):
        self._engine = None

    @keyword
    def init_engine(self, name, secret=None, vault=None, **kwargs):
        """<summary>

        <params>
        <example>
        """
        # TODO: Dependency check during lazy importing.

    @keyword
    def predict(self, location, model=None, **kwargs):
        """<summary>

        <params>
        <example>
        """

    @keyword
    def get_result(self) -> JSONType:
        """<summary>

        <example>
        """
