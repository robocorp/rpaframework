import json
import logging
from typing import Any, Dict, List, Union

from jsonpath_ng import Index, Fields
from jsonpath_ng.ext import parse

from robot.api.deco import keyword


JSONType = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]


class JSON:
    r"""`JSON` is a library for manipulating `JSON`_ files and strings.

    JSON is a common data interchange format inspired by a subset of
    the Javascript programming language, but these days is a de facto
    standard in modern web APIs and is language agnostic.

    .. _JSON: http://json.org/

    **Serialization**

    The term `serialization` refers to the process of converting
    Robot Framework or Python types to JSON or the other way around.

    Basic types can be easily converted between the domains,
    and the mapping is as follows:

    ============= =======
    JSON          Python
    ============= =======
    object        dict
    array         list
    string        str
    number (int)  int
    number (real) float
    true          True
    false         False
    null          None
    ============= =======

    **About JSONPath**

    Reading and writing values from/to JSON serializable objects is done
    using `JSONPath`_. It's a syntax designed to quickly and easily refer to
    specific elements in a JSON structure.

    Compared to Python's normal dictionary access, JSONPath expressions can
    target multiple elements through features such as conditionals and wildcards,
    which can simplify many JSON-related operations. It's analogous to XPath
    for XML structures.

    .. _JSONPath: http://goessner.net/articles/JsonPath/

    **Syntax example**

    For this example consider the following structure:

    .. code-block:: json

       {
         "clients": [
           {
             "name": "Johnny Example",
             "email": "john@example.com",
             "orders": [
                 {"address": "Streetroad 123", "price": 103.20},
                 {"address": "Streetroad 123", "price": 98.99}
             ]
           },
           {
             "name": "Jane Example",
             "email": "jane@example.com",
             "orders": [
                 {"address": "Waypath 321", "price": 22.00},
                 {"address": "Streetroad 123", "price": 2330.01}
             ]
           }
         ]
       }

    In the simplest case JSONPath can replace nested access:

    .. code-block:: robotframework

       # First order of first client, with direct dictionary access
       ${value}=    Set variable    ${json}["clients"][0]["orders"][0]

       # JSONPath access
       ${value}=    Get value from JSON    ${json}    $.clients[0].orders[0]

    But the power comes from complicated expressions:

    .. code-block:: robotframework

       # Find delivery addresses for all orders
       ${prices}=        Get values from JSON    $..address

       # Find orders that cost over 100
       ${expensives}=    Get values from JSON    $..orders[?(@.price>100)]


    **Supported Expressions**

    The supported syntax elements are:

    ======== ===========
    Element  Description
    ======== ===========
    $        Root object/element
    @        Current object/element
    \. or [] Child operator
    \.\.     Recursive descent
    \*       Wilcard, any element
    [n]      Array index
    [a:b:c]  Array slice (start, end, step)
    [a,b]    Union of indices or names
    ?()      Apply a filter expression
    ()       Script expression
    ======== ===========

    There are a multitude of different script expressions
    in addition to the elements listed above, which can
    be seen in the `aforementioned article`__.

    For further library usage examples, see the individual keywords.

    __ JSONPath_
    """

    # TODO: Add more logging about affected rows, at least on debug level

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @keyword("Load JSON from file")
    def load_json_from_file(self, filename: str) -> JSONType:
        """Load JSON data from a file, and return it as JSON serializable object.
        Depending on the input file the object can be either a dictionary,
        a list, or a scalar value.

        :param filename: path to input file

        Example:

        .. code:: robotframework

           &{auth}=    Load JSON from file    auth.json
           Log   Current auth token: ${auth.token}

        """
        self.logger.info("Loading JSON from file: %s", filename)
        with open(filename) as json_file:
            return json.load(json_file)

    @keyword("Save JSON to file")
    def save_json_to_file(self, doc: JSONType, filename: str):
        """Save a JSON serializable object or a string containg
        a JSON value into a file.

        :param doc: JSON serializable object or string
        :param filename: path to output file

        Example:

        .. code:: robotframework

           # Save dictionary to file
           ${john}=    Create dictionary    name=John    mail=john@example.com
           Save JSON to file    ${john}    john.json

           # Save string to file
           ${mark}=    Set variable    {"name": "Mark", "mail": "mark@example.com"}
           Save JSON to file    ${mark}    mark.json

        """
        self.logger.info("Saving JSON to file: %s", filename)
        doc = self.convert_string_to_json(doc) if isinstance(doc, str) else doc
        with open(filename, "w") as outfile:
            json.dump(doc, outfile)

    @keyword("Convert JSON to String")
    def convert_json_to_string(self, doc: JSONType) -> str:
        """Convert a JSON serializable object to a string and return it.

        :param doc: JSON serializable object

        Example:

        .. code:: robotframework

           ${obj}=    Create dictionary    Key=Value
           ${json}=   Convert JSON to string    ${obj}
           Should be equal    ${json}     {"Key": "Value"}

        """
        return json.dumps(doc)

    @keyword("Convert String to JSON")
    def convert_string_to_json(self, doc: str) -> JSONType:
        """Convert a string to a JSON serializable object and return it.

        :param doc: JSON string

        Example:

        .. code:: robotframework

           ${json}=    Set variable    {"Key": "Value"}
           &{obj}=     Convert string to JSON    ${json}
           Should be equal    ${obj.Key}    Value

        """
        return json.loads(doc)

    @keyword("Add to JSON")
    def add_to_json(self, doc: JSONType, expr: str, value: JSONType):
        """Add items into a JSON serializable object and return the result.

        If the target is a list, the values are appended to the end.
        If the target is a dict, the keys are either added or updated.

        :param doc: JSON serializable object
        :param expr: JSONPath expression
        :param value: values to either append or update

        Example:

        .. code:: robotframework

           # Change the name value for all people
           &{before}=    Convert string to JSON   {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
           &{after}=     Add to JSON    ${json}   $.People.name    JohnMalkovich

        """  # noqa: E501
        self.logger.info('Add to JSON with expression: "%s"', expr)
        for match in parse(expr).find(doc):
            if isinstance(match.value, dict):
                match.value.update(value)
            if isinstance(match.value, list):
                match.value.append(value)
        return doc

    @keyword("Get value from JSON")
    def get_value_from_json(self, doc: JSONType, expr: str, default: Any = None):
        """Get a single value from a JSON serializable object that matches the given expression.

        Raises a ValueError if there is more than one match.
        Returns the given default argument (or None) if there
        were no matches.

        :param doc: JSON serializable object or string
        :param expr: jsonpath expression

        Example:

        .. code:: robotframework

           # Get the name value for the first person
           &{people}=    Convert string to JSON   {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
           ${first}=     Get value from JSON      ${people}   $.People[0].name

        """  # noqa: E501
        self.logger.info('Get value from JSON with expression: "%s"', expr)
        result = [match.value for match in parse(expr).find(doc)]
        if len(result) == 0:
            return default
        elif len(result) == 1:
            return result[0]
        else:
            raise ValueError(
                "Found {count} matches: {values}".format(
                    count=len(result), values=", ".join(str(r) for r in result)
                )
            )

    @keyword("Get values from JSON")
    def get_values_from_json(self, doc: JSONType, expr: str):
        """Get all values from a JSON serializable object that match the given expression.

        :param doc: JSON serializable object or string
        :param expr: JSONPath expression

        Example:

        .. code:: robotframework

           # Get all the names for all people
           &{people}=    Convert string to JSON   {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
           @{names}=     Get values from JSON     ${people}   $.People[*].name

        """  # noqa: E501
        self.logger.info('Get values from JSON with expression: "%s"', expr)
        return [match.value for match in parse(expr).find(doc)]

    @keyword("Update value to JSON")
    def update_value_to_json(self, doc: JSONType, expr: str, value: JSONType):
        """Update existing values in a JSON serializable object and return the result.
        Will change all values that match the expression.

        :param doc: JSON or string
        :param expr: JSONPath expression
        :param value: New value for the matching item(s)

        Example:

        .. code:: robotframework

           # Change the name key for all people
           &{before}=    Convert string to JSON   {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
           &{after}=     Update value to JSON     ${json}   $.People[*].name    JohnMalkovich

        """  # noqa: E501
        self.logger.info('Update JSON with expression: "%s"', expr)
        for match in parse(expr).find(doc):
            path = match.path
            if isinstance(path, Index):
                match.context.value[match.path.index] = value
            elif isinstance(path, Fields):
                match.context.value[match.path.fields[0]] = value
        return doc

    @keyword("Delete from JSON")
    def delete_from_json(self, doc: JSONType, expr: str):
        """Delete values from a JSON serializable object and return the result.
        Will delete all values that match the expression.

        :param doc: JSON serializable object or string
        :param expr: JSONPath expression

        Example:

        .. code:: robotframework

           # Delete all people
           &{before}=    Convert string to JSON   {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
           &{after}=     Delete from JSON    ${json}   $.People[*]
        """  # noqa: E501
        self.logger.info('Delete from JSON with expression: "%s"', expr)
        for match in parse(expr).find(doc):
            path = match.path
            if isinstance(path, Index):
                del match.context.value[match.path.index]
            elif isinstance(path, Fields):
                del match.context.value[match.path.fields[0]]
        return doc
