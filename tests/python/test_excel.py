import datetime
import pytest
from io import BytesIO

from RPA.Excel.Files import Files, XlsxWorkbook, XlsWorkbook
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
