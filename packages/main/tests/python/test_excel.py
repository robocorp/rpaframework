import datetime
import pytest
from io import BytesIO
from pathlib import Path

from RPA.Excel.Files import Files, XlsxWorkbook, XlsWorkbook, ensure_unique
from RPA.Tables import Table


@pytest.fixture(
    params=[r"tests/resources/example.xlsx", r"tests/resources/example.xls"]
)
def library(request):
    lib = Files()
    lib.open_workbook(request.param)
    yield lib
    lib.close_workbook()


@pytest.mark.parametrize(
    "fmt, instance", [("xlsx", XlsxWorkbook), ("xls", XlsWorkbook)]
)
def test_create_workbook(fmt, instance):
    library = Files()
    library.create_workbook(fmt=fmt)
    assert isinstance(library.workbook, instance)
    assert library.workbook._book is not None
    assert library.workbook.extension is None


@pytest.mark.parametrize("fmt", ["xlsx", "xls"])
def test_create_after_close(fmt):
    library = Files()
    library.create_workbook(fmt=fmt)
    library.close_workbook()
    library.create_workbook(fmt=fmt)


@pytest.mark.parametrize("fmt", ["xlsx", "xls"])
def test_create_without_close(fmt):
    library = Files()
    library.create_workbook(fmt=fmt)
    library.create_workbook(fmt=fmt)


@pytest.mark.parametrize("filename", ["not-a-file.xlsx", "not-a-file.xls"])
def test_open_missing(filename):
    with pytest.raises(FileNotFoundError):
        lib = Files()
        lib.open_workbook(filename)


@pytest.mark.parametrize(
    "filename",
    [r"tests/resources/wrong_extension.xlsx", r"tests/resources/wrong_extension.xls"],
)
def test_wrong_extension_fallback(filename):
    library = Files()
    library.open_workbook(filename)
    assert library.workbook is not None
    library.close_workbook()


def test_extension_property(library):
    assert library.workbook.extension == Path(library.workbook.path).suffix


def test_save_workbook(library):
    fd = BytesIO()
    library.save_workbook(fd)
    # Exact size is unclear because some formatting, meta-data, etc.
    # might get stripped out
    content = fd.getvalue()
    assert len(content) > 1024


def test_list_worksheets(library):
    sheets = library.list_worksheets()
    assert sheets == ["First", "Second"]


def test_get_active_worksheet(library):
    active = library.get_active_worksheet()
    assert active == "Second"


def test_set_active_worksheet(library):
    library.set_active_worksheet("First")
    assert library.workbook.active == "First"


def test_set_active_worksheet_unknown(library):
    with pytest.raises(ValueError):
        library.set_active_worksheet("Third")
    assert library.workbook.active != "Third"


def test_create_worksheet(library):
    library.create_worksheet("New")
    assert library.list_worksheets() == ["First", "Second", "New"]


def test_create_worksheet_duplicate(library):
    library.create_worksheet("New")
    assert library.list_worksheets() == ["First", "Second", "New"]

    with pytest.raises(ValueError):
        library.create_worksheet("New")
    assert library.list_worksheets() == ["First", "Second", "New"]


def test_create_worksheet_content(library):
    table = Table({"one": [1, 2, 3], "two": ["a", "b", "c"]})

    library.create_worksheet("New", table)
    data = library.read_worksheet_as_table()
    assert len(data) == 3
    assert data.get_column("A", as_list=True) == [1, 2, 3]

    library.create_worksheet("New2", table, header=True)
    data = library.read_worksheet_as_table(header=True)
    assert len(data) == 3
    assert data.get_column("one", as_list=True) == [1, 2, 3]


def test_read_worksheet_default(library):
    data = library.read_worksheet()
    assert len(data) == 10
    assert data[5]["A"] == 5
    assert data[5]["C"] == 2468


def test_read_worksheet_by_index(library):
    data = library.read_worksheet(0)
    assert len(data) == 10
    assert data[2]["B"] == "Mara"
    assert data[2]["F"] == 25


def test_read_worksheet_by_name(library):
    data = library.read_worksheet("First")
    assert len(data) == 10
    assert data[2]["B"] == "Mara"
    assert data[2]["F"] == 25


def test_read_worksheet_header(library):
    data = library.read_worksheet("Second", header=True)
    assert len(data) == 9
    assert data[5]["Index"] == 6
    assert data[5]["Id"] == 2554


def test_read_worksheet_timestamp(library):
    data = library.read_worksheet(name="Second", header=True)
    assert data[5]["Date"] == datetime.datetime(2015, 5, 21)


def test_read_worksheet_as_table(library):
    table = library.read_worksheet_as_table(name="First")
    assert isinstance(table, Table)
    assert len(table) == 10
    assert table[2, 1] == "Mara"
    assert table[2, 2] == "Hashimoto"


def test_read_worksheet_as_table_start_offset(library):
    table = library.read_worksheet_as_table(name="First", start=3)
    assert len(table) == 8
    assert table[0, 1] == "Mara"
    assert table[0, 2] == "Hashimoto"


@pytest.mark.skip(reason="Bug in Tables integer column handling")
def test_read_worksheet_as_table_start_offset_and_header(library):
    table = library.read_worksheet_as_table(name="First", start=2, header=True)
    assert len(table) == 8
    assert table.columns == [1.0, "Dulce", "Abril", "Female", "United States", 32.0]
    assert table[0, 2] == "Hashimoto"


def test_append_to_worksheet_headers(library):
    table = Table(
        [
            {"Index": 98, "Date": "today", "Id": "some_value"},
            {"Index": 99, "Date": "tomorrow", "Id": "another_value"},
        ]
    )
    library.append_rows_to_worksheet(table, header=True)

    result = library.read_worksheet_as_table(header=True)
    assert len(result) == 11
    assert result[-1] == [99, "tomorrow", "another_value"]


@pytest.mark.parametrize("fmt", ("xlsx", "xls"))
def test_append_to_worksheet_empty(fmt):
    table = Table(
        [
            {"Index": 98, "Date": "today", "Id": "some_value"},
            {"Index": 99, "Date": "tomorrow", "Id": "another_value"},
        ]
    )
    library = Files()
    library.create_workbook(fmt=fmt)
    library.append_rows_to_worksheet(table)

    result = library.read_worksheet_as_table()
    assert len(result) == 2
    assert result[0] == [98, "today", "some_value"]


@pytest.mark.parametrize("fmt", ("xlsx", "xls"))
def test_append_to_worksheet_empty_with_headers(fmt):
    table = Table(
        [
            {"Index": 98, "Date": "today", "Id": "some_value"},
            {"Index": 99, "Date": "tomorrow", "Id": "another_value"},
        ]
    )
    library = Files()
    library.create_workbook(fmt=fmt)
    library.append_rows_to_worksheet(table, header=True)

    result = library.read_worksheet_as_table()
    assert len(result) == 3
    assert result[0] == ["Index", "Date", "Id"]


def test_remove_worksheet(library):
    library.remove_worksheet("Second")
    assert library.list_worksheets() == ["First"]


def test_rename_worksheet(library):
    library.rename_worksheet("Second", "Toinen")
    assert library.list_worksheets() == ["First", "Toinen"]


def test_ensure_unique():
    result = ensure_unique(["Banana", "Apple", "Lemon", "Apple", "Apple", "Banana"])
    assert result == ["Banana", "Apple", "Lemon", "Apple_2", "Apple_3", "Banana_2"]


def test_ensure_unique_nested():
    result = ensure_unique(["Banana", "Apple", "Lemon", "Apple", "Apple_2", "Banana"])
    assert result == ["Banana", "Apple", "Lemon", "Apple_2", "Apple_2_2", "Banana_2"]


def test_find_empty_row(library):
    row = library.find_empty_row()
    assert row == 11


def test_set_worksheet_value(library):
    library.set_worksheet_value(11, "A", "First")
    library.set_worksheet_value(11, 2, "Second")
    library.set_worksheet_value(11, "3", "Third")

    data = library.read_worksheet()

    row = data[-1]
    assert row["A"] == "First"
    assert row["B"] == "Second"
    assert row["C"] == "Third"


def test_insert_image_to_worksheet(library):
    library.insert_image_to_worksheet(10, "B", "tests/resources/faces.jpeg", scale=4)
    library.save_workbook(BytesIO())
