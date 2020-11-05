import json
import logging
from typing import Any

from jsonpath_ng import Index, Fields
from jsonpath_ng.ext import parse

from robot.api.deco import keyword


class JSON:
    """`JSON` is a library for manipulating `JSON`_ objects.
    Locating specific elements in the structure is done using `JSONPath`_.

    .. _JSON: http://json.org/
    .. _JSONPath: http://goessner.net/articles/JsonPath/
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @keyword("Load JSON from file")
    def load_json_from_file(self, filename: str) -> Any:
        """Load JSON data from a file and return as an object."""
        self.logger.info("Loading JSON from file: %s", filename)
        with open(filename) as json_file:
            return json.load(json_file)

    @keyword("Save JSON to file")
    def save_json_to_file(self, doc: Any, filename: str) -> None:
        """Save JSON object into a file."""
        self.logger.info("Saving JSON to file: %s", filename)
        doc = self.convert_string_to_json(doc) if isinstance(doc, str) else doc
        with open(filename, "w") as outfile:
            json.dump(doc, outfile)

    @keyword("Convert JSON to String")
    def convert_json_to_string(self, doc: Any) -> str:
        """Convert JSON object to a string."""
        return json.dumps(doc)

    @keyword("Convert String to JSON")
    def convert_string_to_json(self, doc: str) -> dict:
        """Convert a string to a JSON object."""
        return json.loads(doc)

    @keyword("Add to JSON")
    def add_to_json(self, doc: Any, expr: str, value: Any):
        """Add items into a JSON object.

        The given ``value`` is any JSON-serialazable object that
        should be added into the ``doc`` object.

        The location of the added value is given a JSONPath expression.
        """
        self.logger.info('Add to JSON with expression: "%s"', expr)
        for match in parse(expr).find(doc):
            if isinstance(match.value, dict):
                match.value.update(value)
            if isinstance(match.value, list):
                match.value.append(value)
        return doc

    @keyword("Get value from JSON")
    def get_value_from_json(self, doc: Any, expr: str):
        """Get a value from a JSON object.

        The location of the element is given with a JSONPath
        expression. It should be a unique match.
        """
        self.logger.info('Get value from JSON with expression: "%s"', expr)
        result = [match.value for match in parse(expr).find(doc)]
        if len(result) == 0:
            return None
        if len(result) == 1:
            return result[0]
        raise ValueError("Too many matches: %s" % (expr))

    @keyword("Get values from JSON")
    def get_values_from_json(self, doc: Any, expr: str):
        """Get values from a JSON object.

        The location of the element is given with a JSONPath
        expression. A list of matches is returned.
        """
        self.logger.info('Get values from JSON with expression: "%s"', expr)
        return [match.value for match in parse(expr).find(doc)]

    @keyword("Update value to JSON")
    def update_value_to_json(self, doc: Any, expr: str, value: Any):
        """Update value in a JSON object.

        The given ``value`` is any JSON-serialazable object that
        should be added into the ``doc`` object.

        The location of the updated value is given with a JSONPath expression.
        """
        self.logger.info('Update JSON with expression: "%s"', expr)
        for match in parse(expr).find(doc):
            path = match.path
            if isinstance(path, Index):
                match.context.value[match.path.index] = value
            elif isinstance(path, Fields):
                match.context.value[match.path.fields[0]] = value
        return doc

    @keyword("Delete from JSON")
    def delete_from_json(self, doc: Any, expr: str):
        """Delete item from a JSON object.

        The location of the element is given as a JSONPath expression.
        """
        self.logger.info('Delete from JSON with expression: "%s"', expr)
        for match in parse(expr).find(doc):
            path = match.path
            if isinstance(path, Index):
                del match.context.value[match.path.index]
            elif isinstance(path, Fields):
                del match.context.value[match.path.fields[0]]
        return doc
