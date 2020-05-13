import pytest
from collections import namedtuple, OrderedDict
from RPA.Tables import Table, Tables


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

DATA_DICT = [
    {"one": 1, "two": 2, "three": 3},
    {"one": "a", "two": "b", "three": "c"},
    {"one": 1, "two": 2, "four": 4},
    {},
    {"one": 1, "two": 2, "three": 3, "four": 4},
    {},
]

DATA_LIST = [[1, 2, 3], ["a", "b", "c"], [1, 2, None, 4], [], [1, 2, 3, 4], []]

DATA_FIXTURE = {
    "dict": (DATA_DICT, None),
    "list": (DATA_LIST, DATA_COLUMNS),
    "namedtuple": (DATA_NAMEDTUPLE, None),
}


@pytest.fixture
def library():
    return Tables()


@pytest.fixture(params=DATA_FIXTURE)
def table(request):
    data, columns = DATA_FIXTURE[request.param]
    return Table(data, columns)


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


def test_table_negative_index(table):
    assert table[-1] == [None, None, None, None]
    assert table[-2] == [1, 2, 3, 4]
    assert table[-3] == [None, None, None, None]


def test_table_length(table):
    assert len(table) == 6


def test_table_append_rows_index(table):
    table.append_rows(["first", "second", "third"], indexes=["new_one", "new_two"])
    assert len(table) == 9
    assert table.index[-3] == "new_one"
    assert table.index[-2] == "new_two"
    assert table.index[-1] == 8


def test_table_invalid_column(table):
    with pytest.raises(ValueError):
        table.get_column("not_exist")


def test_table_range_columns():
    table = Table(DATA_LIST)
    assert table.columns == [0, 1, 2, 3]


def test_table_named_columns():
    table = Table(DATA_NAMEDTUPLE, columns=["two", "four"])
    assert table.columns == ["two", "four"]
    assert table.index == [0, 1, 2, 3, 4, 5]
    assert table[0] == [2, None]
    assert table[4] == [2, 4]


def test_table_none_columns():
    with pytest.raises(ValueError):
        Table([{"one": 1, "two": 2, None: 3}, {"one": 1, None: 3, "four": 4}])


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


def test_keyword_get_table_dimensions(library, table):
    rows, columns = library.get_table_dimensions(table)
    assert rows == 6
    assert columns == 4


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


@pytest.mark.skip(reason="Not implemented")
def test_keyword_get_table_row(library, table):
    library.get_table_row(table, index)


@pytest.mark.skip(reason="Not implemented")
def test_keyword_get_table_column(library, table):
    library.get_table_column(table, column)


def test_keyword_set_table_row(library, table):
    assert table[1] == ["a", "b", "c", None]
    library.set_table_row(table, 1, ["w", "x", "y", "z"])
    assert table[1] == ["w", "x", "y", "z"]


def test_keyword_set_table_column(library, table):
    library.set_table_column(table, "one", "NaN")
    for row in table:
        assert row["one"] == "NaN"


@pytest.mark.skip(reason="Not implemented")
def test_keyword_pop_table_row(library, table):
    library.pop_table_row(table, index=None)


@pytest.mark.skip(reason="Not implemented")
def test_keyword_pop_table_column(library, table):
    library.pop_table_column(table, column=None)


@pytest.mark.skip(reason="Not implemented")
def test_keyword_set_column_as_index(library, table):
    library.set_column_as_index(table, column=None)


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


@pytest.mark.skip(reason="Not implemented")
def test_keyword_table_tail(library, table):
    library.table_tail(table, count=5)


@pytest.mark.skip(reason="Not implemented")
def test_keyword_get_table_cell(library, table):
    library.get_table_cell(table, row, column)


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
    library.sort_table_by_column(table, "three")
    values = library.get_table_column(table, "three", as_list=True)
    assert values == ["c", 3, 3, None, None, None]


@pytest.mark.skip(reason="Not implemented")
def test_keyword_group_table_by_column(library, table):
    library.group_table_by_column(table, column)


@pytest.mark.skip(reason="Not implemented")
def test_keyword_filter_table_by_column(library, table):
    library.filter_table_by_column(table, column, operator, value)


def test_keyword_filter_empty_rows(library, table):
    library.filter_empty_rows(table)
    assert len(table) == 4
    assert table[-1] == [1, 2, 3, 4]


def test_keyword_trim_empty_rows(library, table):
    library.trim_empty_rows(table)
    assert len(table) == 5
    assert table[-1] == [1, 2, 3, 4]
    assert table[-2] == [None, None, None, None]


@pytest.mark.skip(reason="Not implemented")
def test_keyword_read_table_from_csv(library, table):
    library.read_table_from_csv(path, header=None, columns=None, dialect=None)


@pytest.mark.skip(reason="Not implemented")
def test_keyword_write_table_to_csv(library, table):
    library.write_table_to_csv(path, table)


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
