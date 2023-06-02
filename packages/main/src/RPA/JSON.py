import json
import logging
from typing import Any, Callable, Dict, Hashable, List, Optional, Union

from jsonpath_ng import Index, Fields
from jsonpath_ng.ext.filter import Filter
from jsonpath_ng.ext.parser import ExtentedJsonPathParser

from robot.api.deco import keyword


JSONValue = Optional[Union[str, int, float, bool, list, dict]]
JSONType = Union[Dict[Hashable, JSONValue], List[JSONValue], JSONValue]


class RPAFilter(Filter):
    """Extends default filtering JSON path logic."""

    def filter(self, fn: Callable[[JSONType], bool], data: JSONType) -> JSONType:
        for datum in reversed(self.find(data)):
            index_obj = datum.path
            if isinstance(data, dict):
                index_obj.index = list(data)[index_obj.index]
            index_obj.filter(fn, data)
        return data


class RPAJsonPathParser(ExtentedJsonPathParser):
    """Extends the default JSON path parser found in `jsonpath_ng.ext`."""

    def p_filter(self, p):
        """filter : '?' expressions"""
        p[0] = RPAFilter(p[2])


def parse(path: str, debug: bool = False) -> RPAJsonPathParser:
    return RPAJsonPathParser(debug=debug).parse(path)


class JSON:
    r"""`JSON` is a library for manipulating `JSON`_ files and strings.

    JSON is a common data interchange format inspired by a subset of
    the Javascript programming language, but these days is a de facto
    standard in modern web APIs and is language agnostic.

    .. _JSON: http://json.org/

    Serialization
    =============

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

    About JSONPath
    ==============

    Reading and writing values from/to JSON serializable objects is done
    using `JSONPath`_. It's a syntax designed to quickly and easily refer to
    specific elements in a JSON structure. The specific flavor used in this
    library is based on `jsonpath-ng`_.

    Compared to Python's normal dictionary access, JSONPath expressions can
    target multiple elements through features such as conditionals and wildcards,
    which can simplify many JSON-related operations. It's analogous to XPath
    for XML structures.

    .. _JSONPath: http://goessner.net/articles/JsonPath/
    .. _jsonpath-ng: https://pypi.org/project/jsonpath-ng/#description

    Syntax example
    --------------

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

        *** Tasks ***
        Nested access
            # First order of first client, with direct dictionary access
            ${value}=    Set variable    ${json}["clients"][0]["orders"][0]

            # JSONPath access
            ${value}=    Get value from JSON    ${json}    $.clients[0].orders[0]

    But the power comes from complicated expressions:

    .. code-block:: robotframework

        *** Tasks ***
        Complicated expressions
            # Find delivery addresses for all orders
            ${prices}=        Get values from JSON    $..address

            # Find orders that cost over 100
            ${expensives}=    Get values from JSON    $..orders[?(@.price>100)]


    Supported Expressions
    ---------------------

    The supported syntax elements are:

    =======================    ===========
    Element                    Description
    =======================    ===========
    ``$``                      Root object/element
    ``@``                      Current object/element inside expressions
    ``.`` or ``[]``            Child operator
    ``..``                     Recursive descendant operator
    ````parent````             Parent operator, see `functions`_
    ``*``                      Wilcard, any element
    ``,``                      Select multiple fields
    ``[n]``                    Array index
    ``[a:b:c]``                Array slice (start, end, step)
    ``[a,b]``                  Union of indices or names
    ``[?()]``                  Apply a filter expression
    ``()``                     Script expression
    ``[\\field]``              Sort descending by ``field``, cannot be combined with
                               filters.
    ``[/field]``               Sort ascending by ``field``, cannot be combined with
                               filters.
    ````str()````              Convert value to string, see `functions`_
    ````sub()````              Regex substitution function, see `functions`_
    ````len````                Calculate value's length, see `functions`_
    ````split()````            String split function, see `functions`_
    ``+`` ``-`` ``*`` ``/``    Arithmetic functions, see `functions`_
    =======================    ===========

    Functions
    ^^^^^^^^^

    This library allows JSON path expressions to include certain functions
    which can provide additional benefit to users. These functions are
    generally encapsulated in backticks (`````). Some functions require
    you to pass arguments similar to a Python function.

    For example, let's say a JSON has nodes on the JSON path
    ``$.books[*].genres`` which are represented as strings of genres with
    commas separating each genre. So for one book, this node might have a
    value like ``horror,young-adult``. You can return a list of first genre
    for each book by using the ``split`` function like so:

    .. code-block:: robotframework

        *** Task ***
        Get genres
            ${genres}=  Get values from JSON    $.books[*].genres.```split(,, 0, -1)```

    Each functions parameters are defined here:

    ===================================  =====
    Function                             Usage
    ===================================  =====
    ``str()``                            No parameters, but parenthesis are required
    ``sub(/regex/, repl)``               The regex pattern must be provided in *regex*
                                         and the replacement value provided in *repl*
    ``len``                              No parameters and no parenthesis
    ``split(char, segment, max_split)``  Separator character provided as *char*, which
                                         index from the resulting array to be returns
                                         provided as *segment*, and maximum number of
                                         splits to perform provided as *max_split*,
                                         ``-1`` for all splits.
    ``parent``                           No parameters, no parenthesis
    ===================================  =====

    **Arithmetic Functions**

    JSON Path can be written and combined to concatenate string values
    or perform arithmetic functions on numerical values. Each JSONPath
    expression used must return the same type, and when performing
    such functions between returned lists, each list must be the same
    length. An example is included in documentation for the keyword
    ``Get values from JSON``.

    Additional Information
    ^^^^^^^^^^^^^^^^^^^^^^

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
    def load_json_from_file(self, filename: str, encoding="utf-8") -> JSONType:
        """Load JSON data from a file, and return it as JSON serializable object.
        Depending on the input file the object can be either a dictionary,
        a list, or a scalar value.

        :param filename: path to input file
        :param encoding: file character encoding
        :return: JSON serializable object of the JSON file

        Example:

        .. code:: robotframework

            *** Task ***
            Load json
                &{auth}=    Load JSON from file    auth.json
                Log   Current auth token: ${auth.token}

        """
        self.logger.info("Loading JSON from file: %s", filename)
        with open(filename, "r", encoding=encoding) as json_file:
            return json.load(json_file)

    @keyword("Save JSON to file")
    def save_json_to_file(
        self,
        doc: JSONType,
        filename: str,
        indent: Optional[int] = None,
        encoding: str = "utf-8",
    ) -> None:
        """Save a JSON serializable object or a string containing
        a JSON value into a file.

        :param doc: JSON serializable object or string
        :param filename: path to output file
        :param indent: if given this value is used for json file indent
        :param encoding: file character encoding

        Robot Framework Example:

        .. code:: robotframework

            *** Tasks ***
            Save dictionary to file
                ${john}=    Create dictionary    name=John    mail=john@example.com
                Save JSON to file    ${john}    john.json

            Save string to file
                ${mark}=    Set variable    {"name": "Mark", "mail": "mark@example.com"}
                Save JSON to file    ${mark}    mark.json

        Python Example:

        .. code:: python

            from RPA.JSON import JSON

            # Save dictionary to file.
            john = {"name": "John", "mail": "john@example.com"}
            JSON().save_json_to_file(john, "john.json")

        """
        self.logger.info("Saving JSON to file: %s", filename)
        extra_args = {}
        if indent:
            extra_args["indent"] = indent
        doc = self.convert_string_to_json(doc) if isinstance(doc, str) else doc
        with open(filename, "w", encoding=encoding) as outfile:
            json.dump(doc, outfile, **extra_args)

    @keyword("Convert JSON to String")
    def convert_json_to_string(self, doc: JSONType) -> str:
        """Convert a JSON serializable object to a string and return it.

        :param doc: JSON serializable object
        :return: string of the JSON serializable object

        Robot Framework Example:

        .. code:: robotframework

            *** Task ***
            Convert to string
                ${obj}=    Create dictionary    Key=Value
                ${json}=   Convert JSON to string    ${obj}
                Should be equal    ${json}     {"Key": "Value"}

        Python Example:

        .. code:: python

            from RPA.JSON import JSON
            from robot.libraries.BuiltIn import BuiltIn

            obj = {"Key": "Value"}
            json = JSON().convert_json_to_string(obj)
            BuiltIn().should_be_equal(json, '{"Key": "Value"}')

        """
        return json.dumps(doc)

    @keyword("Convert String to JSON")
    def convert_string_to_json(self, doc: str) -> JSONType:
        """Convert a string to a JSON serializable object and return it.

        :param doc: JSON string
        :return: JSON serializable object of the string

        Robot Framework Example:

        .. code:: robotframework

            *** Task ***
            Convert to json
                ${json}=    Set variable    {"Key": "Value"}
                &{obj}=     Convert string to JSON    ${json}
                Should be equal    ${obj.Key}    Value

        Python Example:

        .. code:: python

            from RPA.JSON import JSON
            from robot.libraries.BuiltIn import BuiltIn

            json = '{"Key": "Value"}'
            obj = JSON().convert_string_to_json(json)
            BuiltIn().should_be_equal(obj["Key"], "Value")

        """
        return json.loads(doc)

    @keyword("Add to JSON")
    def add_to_json(self, doc: JSONType, expr: str, value: JSONType) -> JSONType:
        """Add items into a JSON serializable object and return the result.

        If the target is a list, the values are appended to the end.
        If the target is a dict, the keys are either added or updated.

        :param doc: JSON serializable object
        :param expr: JSONPath expression
        :param value: values to either append or update
        :return: JSON serializable object of the updated JSON

        Robot Framework Example:

        .. code:: robotframework

            *** Task ***
            Change the name value for all people
                &{before}=    Convert string to JSON   {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
                &{person}=    Create dictionary      Name=John
                &{after}=     Add to JSON    ${before}   $.People    ${person}

        Python Example:

        .. code:: python

            from RPA.JSON import JSON

            # Change the name value for all people
            js = JSON()
            before = js.convert_string_to_json('{"People": [{"Name": "Mark"}, {"Name": "Jane"}]}')
            person = {"Name": "John"}
            after = js.add_to_json(before, "$.People", person)

            print(after)

        """  # noqa: E501
        self.logger.info("Add to JSON with expression: %r", expr)
        for match in parse(expr).find(doc):
            if isinstance(match.value, dict):
                match.value.update(value)
            if isinstance(match.value, list):
                match.value.append(value)
        return doc

    @keyword("Get value from JSON")
    def get_value_from_json(
        self, doc: JSONType, expr: str, default: Optional[Any] = None
    ) -> str:
        """Get a single value from a JSON serializable object that matches the given expression.

        Raises a ValueError if there is more than one match.
        Returns the given default argument (or None) if there
        were no matches.

        :param doc: JSON serializable object or string
        :param expr: jsonpath expression
        :param default: default value to return in the absence of a match
        :return: string containing the match OR `default` if there are no matches
        :raises ValueError: if more than one match is discovered

        Short Robot Framework Example:

        .. code:: robotframework

            *** Task ***
            Get the name value for the first person
                &{people}=    Convert string to JSON   {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
                ${first}=     Get value from JSON      ${people}   $.People[0].Name

        Short Python Example:

        .. code:: python

            from RPA.JSON import JSON

            # Get the name value for the second person.
            people = {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
            second = JSON().get_value_from_json(people, "$.People[1].Name")
            print(second)

        Extended Robot Framework Example:

        .. code:: robotframework

            *** Settings ***
            Library         RPA.JSON
            Suite Setup     Ingest JSON

            *** Variables ***
            ${JSON_STRING}      {
            ...                   "clients": [
            ...                     {
            ...                       "name": "Johnny Example",
            ...                       "email": "john@example.com",
            ...                       "orders": [
            ...                         {"address": "Streetroad 123", "state": "TX", "price": 103.20, "id":"guid-001"},
            ...                         {"address": "Streetroad 123", "state": "TX", "price": 98.99, "id":"guid-002"}
            ...                       ]
            ...                     },
            ...                     {
            ...                       "name": "Jane Example",
            ...                       "email": "jane@example.com",
            ...                       "orders": [
            ...                         {"address": "Waypath 321", "state": "WA", "price": 22.00, "id":"guid-003"},
            ...                         {"address": "Streetroad 123", "state": "TX", "price": 2330.01, "id":"guid-004"},
            ...                         {"address": "Waypath 321", "state": "WA", "price": 152.12, "id":"guid-005"}
            ...                       ]
            ...                     }
            ...                   ]
            ...                 }
            ${ID}               guid-003

            *** Tasks ***
            Get email for specific order id
                ${email}=    Get value from json    ${JSON_DOC}    $.clients[?(@..id=="${ID}")].email
                Log    \\nOUTPUT IS\\n ${email}    console=${True}
                Should be equal as strings    ${email}    jane@example.com

            *** Keywords ***
            Ingest JSON
                ${doc}=    Convert string to json    ${JSON_STRING}
                Set suite variable    ${JSON_DOC}    ${doc}

        """  # noqa: E501
        self.logger.info("Get value from JSON with expression: %r", expr)
        result = [match.value for match in parse(expr).find(doc)]
        if len(result) > 1:
            raise ValueError(
                "Found {count} matches: {values}".format(
                    count=len(result), values=", ".join(str(r) for r in result)
                )
            )

        return result[0] if result else default

    @keyword("Get values from JSON")
    def get_values_from_json(self, doc: JSONType, expr: str) -> list:
        """Get all values from a JSON serializable object that match the given expression.

        :param doc: JSON serializable object or string
        :param expr: JSONPath expression
        :return: list of values that match

        Short Robot Framework Example:

        .. code:: robotframework

            *** Task ***
            Get all the names for all people
                &{people}=    Convert string to JSON   {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
                @{names}=     Get values from JSON     ${people}   $.People[*].Name

        Short Python Example:

        .. code:: python

            from RPA.JSON import JSON

            # Get all the names for all people
            people = {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
            names = JSON().get_values_from_json(people, "$.People[*].Name")
            print(second)

        Extended Robot Framework Example:

        .. code:: robotframework

            *** Settings ***
            Library         RPA.JSON
            Suite Setup     Ingest JSON

            *** Variables ***
            ${JSON_STRING}      {
            ...                   "clients": [
            ...                     {
            ...                       "name": "Johnny Example",
            ...                       "email": "john@example.com",
            ...                       "orders": [
            ...                         {"address": "Streetroad 123", "state": "TX", "price": 103.20, "id":"guid-001"},
            ...                         {"address": "Streetroad 123", "state": "TX", "price": 98.99, "id":"guid-002"}
            ...                       ]
            ...                     },
            ...                     {
            ...                       "name": "Jane Example",
            ...                       "email": "jane@example.com",
            ...                       "orders": [
            ...                         {"address": "Waypath 321", "state": "WA", "price": 22.00, "id":"guid-003"},
            ...                         {"address": "Streetroad 123", "state": "TX", "price": 2330.01, "id":"guid-004"},
            ...                         {"address": "Waypath 321", "state": "WA", "price": 152.12, "id":"guid-005"}
            ...                       ]
            ...                     }
            ...                   ]
            ...                 }
            ${ID}               guid-003

            *** Tasks ***
            Get All Prices and Order Ids
                # Arithmetic operations only work when lists are of equal lengths and types.
                ${prices}=    Get values from json
                ...    ${JSON_DOC}
                ...    $.clients[*].orders[*].id + " has price " + $.clients[*].orders[*].price.```str()```
                Log    \\nOUTPUT IS\\n ${prices}    console=${True}
                Should be equal as strings    ${prices}
                ...    ['guid-001 has price 103.2', 'guid-002 has price 98.99', 'guid-003 has price 22.0', 'guid-004 has price 2330.01', 'guid-005 has price 152.12']

            Find Only Valid Emails With Regex
                # The regex used in this example is simplistic and
                # will not work with all email addresses
                ${emails}=    Get values from json
                ...    ${JSON_DOC}
                ...    $.clients[?(@.email =~ "[a-zA-Z]+@[a-zA-Z]+\\.[a-zA-Z]+")].email
                Log    \\nOUTPUT IS\\n ${emails}    console=${True}
                Should be equal as strings    ${emails}    ['john@example.com', 'jane@example.com']

            Find Orders From Texas Over 100
                # The regex used in this example is simplistic and
                # will not work with all email addresses
                ${orders}=    Get values from json
                ...    ${JSON_DOC}
                ...    $.clients[*].orders[?(@.price > 100 & @.state == "TX")]
                Log    \\nOUTPUT IS\\n ${orders}    console=${True}
                Should be equal as strings    ${orders}
                ...    [{'address': 'Streetroad 123', 'state': 'TX', 'price': 103.2, 'id': 'guid-001'}, {'address': 'Streetroad 123', 'state': 'TX', 'price': 2330.01, 'id': 'guid-004'}]


            *** Keywords ***
            Ingest JSON
                ${doc}=    Convert string to json    ${JSON_STRING}
                Set suite variable    ${JSON_DOC}    ${doc}

        """  # noqa: E501
        self.logger.info("Get values from JSON with expression: %r", expr)
        return [match.value for match in parse(expr).find(doc)]

    @keyword("Update value to JSON")
    def update_value_to_json(
        self, doc: JSONType, expr: str, value: JSONType
    ) -> JSONType:
        """Update existing values in a JSON serializable object and return the result.
        Will change all values that match the expression.

        :param doc: JSON or string
        :param expr: JSONPath expression
        :param value: New value for the matching item(s)
        :return: JSON serializable object with updated results

        Short Robot Framework Example:

        .. code:: robotframework

            *** Tasks ***
            Change the name key for all people
                &{before}=    Convert string to JSON   {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
                &{after}=     Update value to JSON     ${before}   $.People[*].Name    JohnMalkovich

        .. code:: python

            from RPA.JSON import JSON

            # Change the name key for all people
            before = {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
            after = JSON().update_value_to_json(before, "$.People[*].Name","JohnMalkovich")
            print(after)

        Extended Robot Framework Example:

        .. code:: robotframework

            *** Settings ***
            Library         RPA.JSON
            Library    Collections
            Suite Setup     Ingest JSON

            *** Variables ***
            ${JSON_STRING}      {
            ...                   "clients": [
            ...                     {
            ...                       "name": "Johnny Example",
            ...                       "email": "john@example.com",
            ...                       "id": "user-001",
            ...                       "orders": [
            ...                         {"address": "Streetroad 123", "state": "TX", "price": 103.20, "id":"guid-001"},
            ...                         {"address": "Streetroad 123", "state": "TX", "price": 98.99, "id":"guid-002"}
            ...                       ]
            ...                     },
            ...                     {
            ...                       "name": "Jane Example",
            ...                       "email": "jane@example.com",
            ...                       "id": "user-002",
            ...                       "orders": [
            ...                         {"address": "Waypath 321", "state": "WA", "price": 22.00, "id":"guid-003"},
            ...                         {"address": "Streetroad 123", "state": "TX", "price": 2330.01, "id":"guid-004"},
            ...                         {"address": "Waypath 321", "state": "WA", "price": 152.12, "id":"guid-005"}
            ...                       ]
            ...                     }
            ...                   ]
            ...                 }
            ${ID}               guid-003

            *** Tasks ***
            Update user email
                ${updated_doc}=    Update value to json
                ...    ${JSON_DOC}
                ...    $.clients[?(@.id=="user-001")].email
                ...    johnny@example.com
                Log    \\nNEW JSON IS\\n ${updated_doc}    console=${True}
                ${new_email}=    Get value from json    ${updated_doc}    $.clients[?(@.id=="user-001")].email
                Should be equal as strings    ${new_email}    johnny@example.com

            Add additional charge to all prices in WA
                # This example also shows how the update keyword changes the original JSON doc in memory.
                ${id_price}=    Get values from json
                ...    ${JSON_DOC}
                ...    $.clients[*].orders[?(@.state=="WA")].id,price
                FOR    ${order_id}    ${price}    IN    @{id_price}
                    Update value to json    ${JSON_DOC}    $.clients[*].orders[?(@.id=="${order_id}")].price    ${{${price} * 1.06}}
                END
                Log    \\nNEW JSON IS\\n ${JSON_DOC}    console=${True}
                ${one_price}=    Get value from json    ${JSON_DOC}    $..orders[?(@.id==${ID})].price
                Should be equal as numbers    ${one_price}    23.32

            *** Keywords ***
            Ingest JSON
                ${doc}=    Convert string to json    ${JSON_STRING}
                Set suite variable    ${JSON_DOC}    ${doc}

        """  # noqa: E501
        self.logger.info("Update JSON with expression: %r", expr)
        for match in parse(expr).find(doc):
            path = match.path
            if isinstance(path, Index):
                match.context.value[match.path.index] = value
            elif isinstance(path, Fields):
                match.context.value[match.path.fields[0]] = value
        return doc

    @keyword("Delete from JSON")
    def delete_from_json(self, doc: JSONType, expr: str) -> JSONType:
        """Delete values from a JSON serializable object and return the result.
        Will delete all values that match the expression.

        :param doc: JSON serializable object or string
        :param expr: JSONPath expression
        :return: JSON serializable object with values removed

        Example:

        .. code:: robotframework

            *** Task ***
            Delete all people
                &{before}=    Convert string to JSON   {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
                &{after}=     Delete from JSON    ${before}   $.People[*]

        .. code:: python

            from RPA.JSON import JSON

            # Delete all people
            before = {"People": [{"Name": "Mark"}, {"Name": "Jane"}]}
            after = JSON().delete_from_json(before, "$.People[*]")
            print(after)

        """  # noqa: E501
        self.logger.info("Delete from JSON with expression: %r", expr)
        return parse(expr).filter(lambda _: True, doc)
