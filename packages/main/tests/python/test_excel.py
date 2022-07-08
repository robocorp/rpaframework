import contextlib
import datetime
from io import BytesIO
from pathlib import Path

import pytest
from RPA.Excel.Files import Files, XlsxWorkbook, XlsWorkbook, ensure_unique
from RPA.Tables import Table

from . import RESOURCES_DIR, RESULTS_DIR


EXCELS_DIR = RESOURCES_DIR / "excels"


@contextlib.contextmanager
def _library(excel_file):
    lib = Files()
    excel_path = EXCELS_DIR / excel_file
    lib.open_workbook(excel_path)
    yield lib
    lib.close_workbook()


@pytest.fixture(params=["example.xlsx", "example.xls"])
def library(request):
    with _library(request.param) as lib:
        yield lib


@pytest.fixture(params=["one-row.xlsx", "one-row.xls", "empty.xlsx", "empty.xls"])
def library_empty(request):
    with _library(request.param) as lib:
        yield lib


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


def test_wrong_extension_fallback_xlsx():
    # openpyxl does not support xls (actual format) but xlrd will succeed
    library = Files()
    path = str(EXCELS_DIR / "wrong_extension.xlsx")
    library.open_workbook(path)
    assert library.workbook is not None


def test_wrong_extension_fallback_xls():
    # openpyxl will refuse to read wrong extension and xlrd does not support xlsx
    library = Files()
    path = str(EXCELS_DIR / "wrong_extension.xls")
    with pytest.raises(ValueError, match=".*wrong_extension.xls.*path.*extension.*"):
        library.open_workbook(path)
    assert library.workbook is None


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


@pytest.mark.parametrize(
    "header, content",
    [
        (False, [{"A": "Single"}]),
        (True, []),
    ],
)
def test_read_worksheet_header_empty(library_empty, header, content):
    data = library_empty.read_worksheet("Sheet", header=header)
    excel_name = library_empty.workbook.path.stem
    if "empty" in excel_name:
        content = []  # there's no content at all, no matter the header switch
    assert data == content


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


def test_read_worksheet_as_table_start_offset_and_header(library):
    table = library.read_worksheet_as_table(name="First", start=2, header=True)
    assert len(table) == 8
    assert table.columns == ["1", "Dulce", "Abril", "Female", "United States", "32"]
    assert table[0, 2] == "Hashimoto"


def test_read_worksheet_empty(library):
    library.create_worksheet("Empty")

    data = library.read_worksheet(header=False)
    assert data == []

    data_header = library.read_worksheet(header=True)
    assert data_header == []

    table = library.read_worksheet_as_table(header=False)
    assert table.dimensions == (0, 0)

    table_header = library.read_worksheet_as_table(header=True)
    assert table_header.dimensions == (0, 0)


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
    library.set_active_worksheet("Second")

    library.remove_worksheet("Second")
    assert library.list_worksheets() == ["First"]
    assert library.get_active_worksheet() == "First"

    with pytest.raises(ValueError):
        library.remove_worksheet("First")


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


def test_get_worksheet_value(library):
    assert library.get_worksheet_value(5, "A") == 4
    assert library.get_worksheet_value(5, "C") == 3549
    assert library.get_worksheet_value(3, 3) == 1582
    assert library.get_worksheet_value(9, "E", "First") == "United States"


def test_set_worksheet_value(library):
    library.set_worksheet_value(11, "A", "First")
    library.set_worksheet_value(11, 2, "Second")
    library.set_worksheet_value(11, "3", "Third")

    data = library.read_worksheet()

    row = data[-1]
    assert row["A"] == "First"
    assert row["B"] == "Second"
    assert row["C"] == "Third"


def test_get_worksheet_value(library):
    assert library.get_cell_value(5, "A") == 4
    assert library.get_cell_value(5, "C") == 3549
    assert library.get_cell_value(3, 3) == 1582
    assert library.get_cell_value(9, "E", "First") == "United States"


def test_set_worksheet_value(library):
    library.set_cell_value(11, "A", "First")
    library.set_cell_value(11, 2, "Second")
    library.set_cell_value(11, "3", "Third", fmt="00.0")

    data = library.read_worksheet()

    row = data[-1]
    assert row["A"] == "First"
    assert row["B"] == "Second"
    assert row["C"] == "Third"


def test_cell_format(library):
    fmts = [
        "general",
        "0",
        "0.00",
        "#,##0",
        "#,##0.00",
        '"$"#,##0_);("$"#,##',
        '"$"#,##0_);[Red]("$"#,##',
        '"$"#,##0.00_);("$"#,##',
        '"$"#,##0.00_);[Red]("$"#,##',
        "0%",
        "0.00%",
        "0.00E+00",
        "# ?/?",
        "# ??/??",
        "M/D/YY",
        "D-MMM-YY",
        "D-MMM",
        "MMM-YY",
        "h:mm AM/PM",
        "h:mm:ss AM/PM",
        "h:mm",
        "h:mm:ss",
        "M/D/YY h:mm",
        "_(#,##0_);(#,##0)",
        "_(#,##0_);[Red](#,##0)",
        "_(#,##0.00_);(#,##0.00)",
        "_(#,##0.00_);[Red](#,##0.00)",
        '_("$"* #,##0_);_("$"* (#,##0);_("$"* "-"_);_(@_)',
        '_(* #,##0_);_(* (#,##0);_(* "-"_);_(@_)',
        '_("$"* #,##0.00_);_("$"* (#,##0.00);_("$"* "-"??_);_(@_)',
        '_(* #,##0.00_);_(* (#,##0.00);_(* "-"??_);_(@_)',
        "mm:ss",
        "[h]:mm:ss",
        "mm:ss.0",
        "##0.0E+0",
        "@",
        "BOOLEAN",
    ]

    value = -1278.9078
    library.create_worksheet("Formats")

    for idx, fmt in enumerate(fmts, 1):
        library.set_cell_value(idx, "A", fmt)
        library.set_cell_value(idx, "B", value)
        library.set_cell_format(idx, "B", fmt)


def test_insert_image_to_worksheet(library):
    path = str(RESOURCES_DIR / "faces.jpeg")
    library.insert_image_to_worksheet(10, "B", path, scale=4)
    library.save_workbook(BytesIO())


@pytest.mark.parametrize("fmt", ("xlsx", "xls"))
def test_create_workbook_default_sheet(fmt):
    library = Files()

    library.create_workbook(fmt=fmt)
    assert library.list_worksheets() == ["Sheet"]

    library.create_worksheet("Test")
    assert library.list_worksheets() == ["Sheet", "Test"]


@pytest.mark.parametrize(
    "excel_file, data_only",
    [
        ("formulas.xlsx", False),
        ("formulas.xls", False),
        ("formulas.xlsx", True),
        ("formulas.xls", True),
    ],
)
def test_read_worksheet_with_formulas(excel_file, data_only):
    library = Files()
    excel_path = EXCELS_DIR / excel_file
    library.open_workbook(excel_path, data_only=data_only)
    assert library.get_worksheet_value(2, "A") == 1
    assert library.get_worksheet_value(2, "B") == 3
    if library.workbook.path.suffix == ".xlsx":
        assert library.get_worksheet_value(2, "C") == 4 if data_only else "=A2+B2"
    else:
        assert library.get_worksheet_value(2, "C") == 4
    library.close_workbook()


@pytest.mark.parametrize("name", ["spaces.xls", "spaces.xlsx"])
def test_invalid_whitespace_fix(name):
    library = Files()
    if name.endswith("xlsx"):
        get_user = lambda book: book.properties.lastModifiedBy
        expected_user = "cmin  "
    else:
        get_user = lambda book: book.user_name
        expected_user = "cmin"

    library.open_workbook(EXCELS_DIR / name)
    assert get_user(library.workbook.book) == expected_user

    library.save_workbook(RESULTS_DIR / name)
    # Leading/trailing whitespace is stripped on save, thus not creating any unwanted
    #  `xml:space="preserve"` tag child under workbook properties. (which breaks
    #  validation with Microsoft)
    assert get_user(library.workbook.book) == "cmin"


@pytest.mark.parametrize("fmt", ["xlsx", "xls"])
def test_create_with_sheet_name(fmt):
    library = Files()
    path = RESULTS_DIR / f"custom-sheet-name.{fmt}"
    name = "CustomName"
    library.create_workbook(path, fmt=fmt, sheet_name=name)
    assert library.get_active_worksheet() == name
