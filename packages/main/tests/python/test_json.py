import pytest
from RPA.JSON import JSON


ORDERS = """
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
"""

MARKS = [
    '{"People": [{"Name": "Mark", "Email": "mark@robocorp.com"}, {"Name": "Jane", '
    '"Extra": 1}]}',
    '{"People": {"a": 1, "b": {"Name": "Mark", "Email": "mark@robocorp.com"}, "c": '
    '{"Name": "Jane", "Extra": 1}}}',
    '{"People": {"a": 1, "b": {"z": {"Name": "Mark", "Email": "mark@robocorp.com"}}, '
    '"c": {"Name": "Jane", "Extra": 1}}}',
]


@pytest.fixture
def lib():
    return JSON()


def str2json(json_string, *, lib):
    return lib.convert_string_to_json(json_string.strip())


@pytest.fixture
def orders(lib):
    return str2json(ORDERS, lib=lib)


@pytest.fixture(params=MARKS)
def mark(lib, request):
    return str2json(request.param, lib=lib)


def test_json_expression(lib, orders):
    result = lib.get_values_from_json(orders, "$..address")
    assert result == [
        "Streetroad 123",
        "Streetroad 123",
        "Waypath 321",
        "Streetroad 123",
    ]


def test_json_expression_filter(lib, orders):
    result = lib.get_values_from_json(orders, "$..orders[?(@.price>100)]")
    assert result == [
        {"address": "Streetroad 123", "price": 103.2},
        {"address": "Streetroad 123", "price": 2330.01},
    ]


def test_json_single_value(lib, orders):
    assert lib.get_value_from_json(orders, "$.clients[0].name") == "Johnny Example"


def test_json_single_value_default(lib, orders):
    assert (
        lib.get_value_from_json(orders, "$.clients[3].name", default="Notexist")
        == "Notexist"
    )


def test_json_update(lib, orders):
    result = lib.update_value_to_json(orders, "$.clients[*].name", "John Malkovich")
    assert all(client["name"] == "John Malkovich" for client in result["clients"])


@pytest.mark.parametrize(
    "expr",
    [
        '$.People[?(@..Name=="Mark")]',
        '$.People[?(@..Name=="Mark") & (@..Email=="mark@robocorp.com")]',
        '$[?(@..Name=="Other")] | $[?(@..Email=="mark@robocorp.com")]',
        '($[?(@..Name=="Other")] | $[?(@..Email=="mark@robocorp.com")])[?(@..Email=="mark@robocorp.com")]',
        '($|($.*)|($.*.*))[?(@.Name=="Mark")]',
    ],
)
def test_delete_from_json(lib, mark, expr):
    mark_dict = lib.delete_from_json(mark, expr)
    mark_str = lib.convert_json_to_string(mark_dict)
    assert "Mark" not in mark_str
