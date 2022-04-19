import os
import tempfile
from collections import namedtuple, OrderedDict
from contextlib import contextmanager
from pathlib import Path

import pytest
from RPA.Tables import Table, Tables, Dialect


RESOURCES = Path(__file__).parent / ".." / "resources"

DATA_COLUMNS = ["one", "two", "three", "four"]

TUPLE_THREE = namedtuple("Three", ["one", "two", "three"])
TUPLE_FOUR = namedtuple("Four", ["one", "two", "three", "four"])
TUPLE_SPARSE = namedtuple("Sparse", ["one", "two", "four"])
TUPLE_EMPTY = namedtuple("Empty", [])

DATA_NAMEDTUPLE = [
    TUPLE_THREE(1, 2, 3),
    TUPLE_THREE("a", "b", "c"),
    TUPLE_SPARSE(1, 2, 4),
    TUPLE_EMPTY(),
    TUPLE_FOUR(1, 2, 3, 4),
    TUPLE_EMPTY(),
]

DATA_DICT_LIST = {
    "one": [1, "a", 1, None, 1, None],
    "two": [2, "b", 2, None, 2],
    "three": [3, "c", None, None, 3, None],
    "four": [None, None, 4, None, 4],
}

DATA_LIST_DICT = [
    {"one": 1, "two": 2, "three": 3},
    {"one": "a", "two": "b", "three": "c"},
    {"one": 1, "two": 2, "four": 4},
    {},
    {"one": 1, "two": 2, "three": 3, "four": 4},
    {},
]

DATA_LIST_LIST = [[1, 2, 3], ["a", "b", "c"], [1, 2, None, 4], [], [1, 2, 3, 4], []]

DATA_FIXTURE = {
    "dict-list": (DATA_DICT_LIST, None),
    "list-dict": (DATA_LIST_DICT, None),
    "list-list": (DATA_LIST_LIST, DATA_COLUMNS),
    "namedtuple": (DATA_NAMEDTUPLE, None),
}


@contextmanager
def temppath():
    with tempfile.NamedTemporaryFile() as fd:
        path = fd.name
    try:
        yield path
    finally:
        os.unlink(path)


@pytest.fixture
def library():
    return Tables()


@pytest.fixture(params=DATA_FIXTURE)
def table(request):
    data, columns = DATA_FIXTURE[request.param]
    return Table(data, columns)


def test_table_repr(table):
    assert str(table) == "Table(columns=['one', 'two', 'three', 'four'], rows=6)"


def test_table_compare(table):
    assert table == Table(DATA_NAMEDTUPLE)
    assert table != "not-comparable"


def test_table_from_table(table):
    copy = Table(table)
    assert copy.columns == table.columns
    assert copy.data == table.data

    copy = Table(table, columns=["first", "second", "third", "fourth"])
    assert copy.columns == ["first", "second", "third", "fourth"]
    assert copy.data == table.data


def test_table_from_dict():
    copy = Table(DATA_DICT_LIST)
    assert copy.columns == ["one", "two", "three", "four"]
    assert len(copy.data) == 6

    copy = Table(DATA_DICT_LIST, columns=["one", "two"])
    assert copy.columns == ["one", "two"]
    assert copy.data == Table(DATA_DICT_LIST).get(columns=["one", "two"]).data


def test_table_invalid_data():
    with pytest.raises(TypeError):
        Table("cool")


def test_table_columns(table):
    assert table.columns == ["one", "two", "three", "four"]


def test_table_index(table):
    assert table.index == [0, 1, 2, 3, 4, 5]


def test_table_pad_short(table):
    assert table[0] == [1, 2, 3, None]


def test_table_pad_sparse(table):
    assert table[2] == [1, 2, None, 4]


def test_table_empty_row(table):
    assert table[3] == [None, None, None, None]


def test_table_negative_row_index(table):
    assert table[-1] == [None, None, None, None]
    assert table[-2] == [1, 2, 3, 4]
    assert table[-3] == [None, None, None, None]


def test_table_negative_column_index(table):
    assert table[0, 1] == 2
    assert table[0, -1] == None
    assert table[0, -2] == 3


def test_table_slice_index(table):
    assert table[1:3] == [["a", "b", "c", None], [1, 2, None, 4]]


def test_table_length(table):
    assert len(table) == 6


def test_table_invalid_column(table):
    with pytest.raises(ValueError):
        table.get_column("not_exist")


def test_table_range_columns():
    table = Table(DATA_LIST_LIST)
    assert table.columns == [0, 1, 2, 3]


def test_table_named_columns():
    table = Table(DATA_NAMEDTUPLE, columns=["two", "four"])
    assert table.columns == ["two", "four"]
    assert table.index == [0, 1, 2, 3, 4, 5]
    assert table[0] == [2, None]
    assert table[4] == [2, 4]


def test_table_too_short_columns():
    with pytest.raises(ValueError):
        Table(DATA_LIST_LIST, columns=["two", "four"])


def test_table_duplicate_columns():
    with pytest.raises(ValueError):
        Table(DATA_NAMEDTUPLE, columns=["two", "four", "two"])


def test_table_iterate_tuples():
    table = Table(
        [{"valid_key": 1, "invalid-key1": 2, "invalid/key2": 3, "123invalidkey3": 4}]
    )

    assert table.columns == [
        "valid_key",
        "invalid-key1",
        "invalid/key2",
        "123invalidkey3",
    ]

    rows = list(table.iter_tuples(with_index=False))
    assert len(rows) == 1
    assert rows[0] == (1, 2, 3, 4)
    assert rows[0]._fields == (
        "valid_key",
        "invalid_key1",
        "invalid_key2",
        "invalidkey3",
    )


def test_table_iterate_tuples_invalid():
    table = Table([{"one": 1, "two": 2, "assert": 3, "": 4}])
    assert table.columns == [
        "one",
        "two",
        "assert",
        "",
    ]

    with pytest.raises(ValueError):
        list(table.iter_tuples(with_index=False))


@pytest.mark.parametrize(
    "data, columns", DATA_FIXTURE.values(), ids=DATA_FIXTURE.keys()
)
def test_keyword_create_table(data, columns, library):
    table = library.create_table(data)
    assert len(table) == 6


def test_keyword_export_table_as_list(library, table):
    exported = library.export_table(table)
    assert exported == [
        {"one": 1, "two": 2, "three": 3, "four": None},
        {"one": "a", "two": "b", "three": "c", "four": None},
        {"one": 1, "two": 2, "three": None, "four": 4},
        {"one": None, "two": None, "three": None, "four": None},
        {"one": 1, "two": 2, "three": 3, "four": 4},
        {"one": None, "two": None, "three": None, "four": None},
    ]


def test_keyword_export_table_as_dict(library, table):
    exported = library.export_table(table, with_index=True, as_list=False)
    assert exported == OrderedDict(
        {
            "index": [0, 1, 2, 3, 4, 5],
            "one": [1, "a", 1, None, 1, None],
            "two": [2, "b", 2, None, 2, None],
            "three": [3, "c", None, None, 3, None],
            "four": [None, None, 4, None, 4, None],
        }
    )


def test_keyword_copy_table(library, table):
    copied = library.copy_table(table)
    assert copied == table


def test_keyword_clear_table(library, table):
    library.clear_table(table)
    assert len(table) == 0
    assert len(table.index) == 0
    assert table.columns == DATA_COLUMNS


def test_merge_tables(library):
    prices = {"Name": ["Egg", "Cheese", "Ham"], "Price": [10.0, 15.0, 20.0]}
    stock = {"Name": ["Egg", "Cheese", "Ham", "Spider"], "Stock": [12, 99, 0, 1]}

    merged = library.merge_tables(Table(prices), Table(stock))
    assert len(merged) == 7
    assert merged.columns == ["Name", "Price", "Stock"]
    assert merged[None, "Name"] == [
        "Egg",
        "Cheese",
        "Ham",
        "Egg",
        "Cheese",
        "Ham",
        "Spider",
    ]

    merged = library.merge_tables(Table(prices), Table(stock), index="Name")
    assert len(merged) == 4
    assert merged.get_row(0) == {"Name": "Egg", "Price": 10.0, "Stock": 12}
    assert merged.get_row(1) == {"Name": "Cheese", "Price": 15.0, "Stock": 99}
    assert merged.get_row(2) == {"Name": "Ham", "Price": 20.0, "Stock": 0}
    assert merged.get_row(3) == {"Name": "Spider", "Price": None, "Stock": 1}


def test_keyword_get_table_dimensions(library, table):
    rows, columns = library.get_table_dimensions(table)
    assert rows == 6
    assert columns == 4


def test_keyword_rename_table_columns(library, table):
    library.rename_table_columns(table, ["a", "b", "c", "d"])
    assert table.columns == ["a", "b", "c", "d"]
    assert table.get_column("a", as_list=True) == [1, "a", 1, None, 1, None]

    library.rename_table_columns(table, ["1", None, "2"])
    assert table.columns == ["1", "b", "2", "d"]


def test_keyword_add_table_column(library, table):
    library.add_table_column(table, name="five")
    assert table.columns == ["one", "two", "three", "four", "five"]
    assert table[0] == [1, 2, 3, None, None]


def test_keyword_add_table_rows(library, table):
    library.add_table_row(table, ["x", "y", "z"])
    assert len(table) == 7
    assert table.index[-2] == 5
    assert table[-1] == ["x", "y", "z", None]


def test_keyword_add_table_rows_too_long(library, table):
    library.add_table_row(table, ["x", "y", "z", "i", "j", "k"])
    assert len(table) == 7
    assert table.index[-2] == 5
    assert table[-1] == ["x", "y", "z", "i"]


def test_keyword_get_table_row(library, table):
    assert library.get_table_row(table, 0) == {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": None,
    }


def test_keyword_get_table_column(library, table):
    assert library.get_table_column(table, 0) == [1, "a", 1, None, 1, None]


def test_keyword_set_table_row(library, table):
    assert table[1] == ["a", "b", "c", None]
    library.set_table_row(table, 1, ["w", "x", "y", "z"])
    assert table[1] == ["w", "x", "y", "z"]


def test_keyword_set_table_column(library, table):
    library.set_table_column(table, "one", "NaN")
    for row in table:
        assert row["one"] == "NaN"


def test_keyword_pop_table_row(library, table):
    assert len(table) == 6
    assert table[0] == [1, 2, 3, None]

    row = library.pop_table_row(table, row=0, as_list=True)

    assert len(table) == 5
    assert table[0] == ["a", "b", "c", None]
    assert row == [1, 2, 3, None]


def test_keyword_pop_table_column(library, table):
    library.pop_table_column(table, "two")
    assert table.columns == ["one", "three", "four"]
    assert len(table) == 6
    assert table[0] == [1, 3, None]


def test_keyword_get_table_slice(library, table):
    result = library.get_table_slice(table)
    assert result == table

    result = library.get_table_slice(table, start=3)
    assert len(result) == 3

    result = library.get_table_slice(table, end=2)
    assert len(result) == 2

    result = library.get_table_slice(table, end=-1)
    assert len(result) == 5

    result = library.get_table_slice(table, start=2, end=3)
    assert len(result) == 1

    result = library.get_table_slice(table, start=3, end=2)
    assert len(result) == 0


def test_keyword_find_table_rows(library, table):
    matches = library.find_table_rows(table, "three", "==", 3)
    assert len(matches) == 2

    matches = library.find_table_rows(table, "four", "is", None)
    assert len(matches) == 4


def test_keyword_set_row_as_column_names(library, table):
    assert table.columns == ["one", "two", "three", "four"]
    assert len(table) == 6

    library.set_row_as_column_names(table, 4)
    assert table.columns == [1, 2, 3, 4]
    assert len(table) == 5


def test_keyword_table_head(library, table):
    head = library.table_head(table, count=3)
    assert isinstance(head, Table)
    assert len(head) == 3
    assert head[0] == table[0]
    assert head[-1] == table[2]


def test_keyword_table_head_list(library, table):
    head = library.table_head(table, count=3, as_list=True)
    assert isinstance(head, list)
    assert len(head) == 3
    assert head[0] == table[0]
    assert head[-1] == table[2]


def test_keyword_table_tail(library, table):
    tail = library.table_tail(table, count=2)
    assert len(tail) == 2
    assert tail[-1] == table[-1]


def test_keyword_get_table_cell(library, table):
    assert library.get_table_cell(table, 0, 0) == 1
    assert library.get_table_cell(table, 2, 3) == 4


def test_keyword_set_table_cell_existing(library, table):
    library.set_table_cell(table, 0, 0, 123)
    assert table[0, 0] == 123
    library.set_table_cell(table, 1, "one", 321)
    assert table[1, 0] == 321


def test_keyword_set_table_cell_new(library, table):
    assert table.dimensions == (6, 4)
    library.set_table_cell(table, 9, 7, ">9000")
    assert table.dimensions == (10, 8)
    assert table[9, 7] == ">9000"


def test_keyword_sort_table_by_column(library, table):
    library.add_table_column(table, name="five", values=["bbb", 2, 3, 1, 3, "aaa"])

    library.sort_table_by_column(table, "five", ascending=True)
    assert library.get_table_column(table, "five") == [1, 2, 3, 3, "aaa", "bbb"]
    assert library.get_table_column(table, "one") == [None, "a", 1, 1, None, 1]

    library.sort_table_by_column(table, "five", ascending=False)
    assert library.get_table_column(table, "five") == ["bbb", "aaa", 3, 3, 2, 1]
    assert library.get_table_column(table, "one") == [1, None, 1, 1, "a", None]


def test_keyword_group_table_by_column(library, table):
    groups = library.group_table_by_column(table, "three")
    assert len(groups) == 3
    for group in groups:
        column = library.get_table_column(group, "three")
        assert len(set(column)) == 1


def test_keyword_filter_table_by_column(library, table):
    library.filter_table_by_column(table, "two", "==", 2)
    assert len(table) == 3
    assert all(row["two"] == 2 for row in table)


def test_keyword_filter_table_by_column_in(library, table):
    library.filter_table_by_column(table, "two", "in", ["b", None])
    assert len(table) == 3
    assert all(row["two"] != 2 for row in table)


def test_keyword_filter_table_by_column_not_contains(library):
    table = Table(
        [
            {"type": "Something", "value": 1},
            {"type": "Test", "value": 2},
            {"type": "Whatever", "value": 3},
            {"type": "Nothing", "value": 4},
        ]
    )
    library.filter_table_by_column(table, "type", "not contains", "thing")
    assert table.data == [["Test", 2], ["Whatever", 3]]


def test_keyword_filter_empty_rows(library, table):
    library.filter_empty_rows(table)
    assert len(table) == 4
    assert table[-1] == [1, 2, 3, 4]


def test_keyword_trim_empty_rows(library, table):
    library.trim_empty_rows(table)
    assert len(table) == 5
    assert table[-1] == [1, 2, 3, 4]
    assert table[-2] == [None, None, None, None]


def test_trim_column_names(library, table):
    library.rename_table_columns(table, ["a ", "b", "  c", " d "])
    assert table.columns == ["a ", "b", "  c", " d "]

    before = table.dimensions
    library.trim_column_names(table)
    after = table.dimensions

    assert before == after
    assert table.columns == ["a", "b", "c", "d"]


def test_keyword_read_table_from_csv(library):
    table = library.read_table_from_csv(RESOURCES / "easy.csv")
    assert len(table) == 3
    assert table.columns == ["first", "second", "third"]
    assert table[0] == ["1", "2", "3"]


def test_keyword_read_table_from_csv_no_header(library):
    table = library.read_table_from_csv(RESOURCES / "easy.csv", header=False)
    assert len(table) == 4
    assert table.columns == [0, 1, 2]
    assert table[0] == ["first", "second", "third"]


def test_keyword_read_table_from_csv_dialect_string(library):
    table = library.read_table_from_csv(
        RESOURCES / "hard.csv", dialect="excel", header=True
    )
    assert len(table) == 100


def test_keyword_read_table_from_csv_encoding(library):
    table = library.read_table_from_csv(RESOURCES / "easy.csv", encoding="utf-8")
    assert len(table) == 3
    assert table.columns == ["first", "second", "third"]
    assert table[0] == ["1", "2", "3"]


def test_keyword_read_table_from_csv_longer_lines(library):
    table = library.read_table_from_csv(
        RESOURCES / "big.csv", header=False, delimiters=";"
    )
    assert len(table) == 3
    assert len(table.columns) == 72
    table[-1][1] == "1121321715"


def test_keyword_read_table_from_csv_extra(library):
    table = library.read_table_from_csv(
        RESOURCES / "extra.csv", column_unknown="whoknows"
    )
    assert len(table) == 4
    assert table.columns == ["first", "second", "third", "whoknows"]
    assert table[0] == ["1", "2", "3", None]
    assert table[2] == ["7", "8", "9", ["11", "12"]]


def test_keyword_read_table_from_csv_manual(library):
    table = library.read_table_from_csv(
        RESOURCES / "hard.csv", dialect=Dialect.Excel, header=True
    )
    assert len(table) == 100
    assert table.columns == [
        "Region",
        "Country",
        "Item Type",
        "Sales Channel",
        "Order Priority",
        "Order Date",
        "Order ID",
        "Ship Date",
        "Units Sold",
        "Unit Price",
        "Unit Cost",
        "Total Revenue",
        "Total Cost",
        "Total Profit",
    ]
    assert table[-1] == [
        "Sub-Saharan Africa",
        "Mozambique",
        "Household",
        "Offline",
        "L",
        "2/10/2012",
        "665095412",
        "2/15/2012",
        "5367",
        "668.27",
        "502.54",
        "3586605.09",
        "2697132.18",
        "889472.91",
    ]


def test_keyword_write_table_to_csv(library, table):
    with temppath() as path:
        library.write_table_to_csv(table, path)
        with open(path) as fd:
            data = fd.readlines()

    assert len(data) == 7
    assert data[0] == "one,two,three,four\n"


def test_keyword_write_table_to_csv_encoding(library, table):
    with temppath() as path:
        library.write_table_to_csv(table, path, encoding="utf-8")
        with open(path) as fd:
            data = fd.readlines()

    assert len(data) == 7
    assert data[0] == "one,two,three,four\n"


def test_keyword_write_table_to_csv_columns_range(library):
    table = Table([[1, 2, 3], [4, 5, 6]])

    with temppath() as path:
        library.write_table_to_csv(table, path)
        with open(path) as fd:
            data = fd.readlines()

    assert len(data) == 3
    assert data[0] == "0,1,2\n"
    assert data[1] == "1,2,3\n"


def test_keyword_write_table_to_csv_delimiter(library, table):
    with temppath() as path:
        library.write_table_to_csv(table, path, encoding="utf-8", delimiter=";")
        with open(path) as fd:
            data = fd.readlines()

    assert len(data) == 7
    assert data[0] == "one;two;three;four\n"


def test_import_with_integer_keys():
    data = [
        {1: "Sub Total", 2: "$85.00 "},
        {1: "Tax", 2: "$8.50 "},
        {1: "Total", 2: "$93.50 "},
    ]

    table = Table(data)
    assert table.dimensions == (3, 3)
    assert table[0, 0] == None

    table = Table(data, columns=("Field", "Value"))
    assert table.dimensions == (3, 2)


def test_set_cell_empty_table():
    table = Table()
    table.set_cell(0, 0, "value")
    assert table.dimensions == (1, 1)
    assert table[0, 0] == "value"


def test_create_table_1d_dict():
    data = {"a": 1, "b": 2, "c": 3}
    table = Table(data)
    assert len(table) == 1
    assert table.columns == ["a", "b", "c"]


def test_create_table_1d_list():
    data = [1, 2, 3]
    table = Table(data)
    assert len(table) == 3


def test_columns_without_data():
    data = []
    columns = ["one", "two", "three"]
    table = Table(data, columns=columns)
    assert table.dimensions == (0, 3)


def test_data_with_nonetype():
    data = [
        {"one": 1, "two": 2},
        {"one": 1, "two": 2, None: 3},
        {"two": 2},
        {"four": 4, None: 3},
    ]

    table = Table(data)
    assert len(table) == 4
    assert table.columns == ["one", "two", 2, "four"]
    assert table.data == [
        [1, 2, None, None],
        [1, 2, 3, None],
        [None, 2, None, None],
        [None, None, 3, 4],
    ]


def test_table_append_row():
    data = {"a": [1], "b": [2], "c": [3]}
    table = Table(data)
    table.append_row()
