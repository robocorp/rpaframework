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
""".strip()


@pytest.fixture()
def orders():
    return JSON().convert_string_to_json(ORDERS)


def test_json_expression(orders):
    result = JSON().get_values_from_json(orders, "$..address")
    assert result == [
        "Streetroad 123",
        "Streetroad 123",
        "Waypath 321",
        "Streetroad 123",
    ]


def test_json_expression_filter(orders):
    result = JSON().get_values_from_json(orders, "$..orders[?(@.price>100)]")
    assert result == [
        {"address": "Streetroad 123", "price": 103.2},
        {"address": "Streetroad 123", "price": 2330.01},
    ]


def test_json_single_value(orders):
    assert JSON().get_value_from_json(orders, "$.clients[0].name") == "Johnny Example"


def test_json_single_value_default(orders):
    assert (
        JSON().get_value_from_json(orders, "$.clients[3].name", default="Notexist")
        == "Notexist"
    )


def test_json_update(orders):
    result = JSON().update_value_to_json(orders, "$.clients[*].name", "John Malkovich")
    assert all(client["name"] == "John Malkovich" for client in result["clients"])
