# pylint: disable=too-many-lines
# TODO: Implement column slicing
# TODO: Index name conflict in exports/imports
# TODO: Return Robot Framework DotDict instead of dict?
import copy
import csv
import logging
import re
from collections import OrderedDict, namedtuple
from enum import Enum
from keyword import iskeyword
from typing import (
    Any,
    Dict,
    Generator,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

from itertools import groupby, zip_longest
from numbers import Number
from operator import itemgetter

from robot.api.deco import keyword
from RPA.core.types import is_dict_like, is_list_like, is_namedtuple
from RPA.core.notebook import notebook_table, notebook_print

Index = int
Column = Union[int, str]
Row = Union[Dict, List, Tuple, NamedTuple, set]
Data = Union[Dict[Column, Row], List[Row], "Table", None]


def to_list(obj: Any, size: int = 1):
    """Convert (possibly scalar) value to list of `size`."""
    if not is_list_like(obj):
        return [obj] * int(size)
    else:
        return obj


def to_identifier(val: Any):
    """Convert string to valid identifier"""
    val = str(val).strip()
    # Replaces spaces, dashes, and slashes to underscores
    val = re.sub(r"[\s\-/\\]", "_", val)
    # Remove remaining invalid characters
    val = re.sub(r"[^0-9a-zA-Z_]", "", val)
    # Identifier can't start with digits
    val = re.sub(r"^[^a-zA-Z_]+", "", val)

    if not val or iskeyword(val):
        raise ValueError(f"Unable to convert to identifier: {val}")

    return val


def to_condition(operator: str, value: Any):
    """Convert string operator into callable condition function."""
    operator = str(operator).lower().strip()
    condition = {
        ">": lambda x: x is not None and x > value,
        "<": lambda x: x is not None and x < value,
        ">=": lambda x: x is not None and x >= value,
        "<=": lambda x: x is not None and x <= value,
        "==": lambda x: x == value,
        "!=": lambda x: x != value,
        "is": lambda x: x is value,
        "not is": lambda x: x is not value,
        "contains": lambda x: x is not None and value in x,
        "not contains": lambda x: x is not None and value not in x,
        "in": lambda x: x in value,
        "not in": lambda x: x not in value,
    }.get(operator)

    if not condition:
        raise ValueError(f"Unknown operator: {operator}")

    return condition


def if_none(value: Any, default: Any):
    """Return default if value is None."""
    return value if value is not None else default


def uniq(seq: Iterable):
    """Return list of unique values while preserving order.
    Values must be hashable.
    """
    seen, result = {}, []
    for item in seq:
        if item in seen:
            continue
        seen[item] = None
        result.append(item)
    return result


class Dialect(Enum):
    """CSV dialect"""

    Excel = "excel"
    ExcelTab = "excel-tab"
    Unix = "unix"


class Table:
    """Container class for tabular data.

    Supported data formats:

    - empty: None values populated according to columns/index
    - list: list of data Rows
    - dict: Dictionary of columns as keys and Rows as values
    - table: An existing Table

    Row: a namedtuple, dictionary, list or a tuple

    :param data:     Values for table,  see "Supported data formats"
    :param columns:  Names for columns, should match data dimensions
    """

    def __init__(self, data: Data = None, columns: Optional[List[str]] = None):
        self._data = []
        self._columns = []

        # Use public setter to validate data
        if columns is not None:
            self.columns = list(columns)

        if not data:
            self._init_empty()
        elif isinstance(data, Table):
            self._init_table(data)
        elif is_dict_like(data):
            self._init_dict(data)
        elif is_list_like(data):
            self._init_list(data)
        else:
            raise TypeError("Not a valid input format")

        if columns:
            self._sort_columns(columns)

        self._validate_self()

    def _init_empty(self):
        """Initialize table with empty data."""
        self._data = []

    def _init_table(self, table: "Table"):
        """Initialize table with another table."""
        if not self.columns:
            self.columns = table.columns
        self._data = table.data

    def _init_list(self, data: List[Any]):
        """Initialize table from list-like container."""
        # Assume data is homogenous in regard to row type
        obj = data[0]
        column_names = self._column_name_getter(obj)
        column_values = self._column_value_getter(obj)

        # Map of source to destination column
        column_map = {}

        # Do not update columns if predefined
        add_columns = not bool(self._columns)

        for obj in data:
            row = [None] * len(self._columns)

            for column_src in column_names(obj):
                # Check if column has been added with different name
                column_dst = column_map.get(column_src, column_src)

                # Dictionaries and namedtuples can
                # contain unknown columns
                if column_dst not in self._columns:
                    if not add_columns:
                        continue

                    col = self._add_column(column_dst)

                    # Store map of source column name to created name
                    column_dst = self._columns[col]
                    column_map[column_src] = column_dst

                    while len(row) < len(self._columns):
                        row.append(None)

                col = self.column_location(column_dst)
                row[col] = column_values(obj, column_src)

            self._data.append(row)

    def _init_dict(self, data: Dict[Column, Row]):
        """Initialize table from dict-like container."""
        if not self._columns:
            self._columns = list(data.keys())

        # Filter values by defined columns
        columns = (
            to_list(values)
            for column, values in data.items()
            if column in self._columns
        )

        # Convert columns to rows
        self._data = [list(row) for row in zip_longest(*columns)]

    def __repr__(self):
        return "Table(columns={}, rows={})".format(self.columns, self.size)

    def __len__(self):
        return self.size

    def __iter__(self):
        return self.iter_dicts(with_index=False)

    def __eq__(self, other: Any):
        if not isinstance(other, Table):
            return False
        return self._columns == other._columns and self._data == other._data

    @property
    def data(self):
        return self._data.copy()

    @property
    def size(self):
        return len(self._data)

    @property
    def dimensions(self):
        return self.size, len(self._columns)

    @property
    def index(self):
        return list(range(self.size))

    @property
    def columns(self):
        return self._columns.copy()

    @columns.setter
    def columns(self, names):
        """Rename columns with given values."""
        self._validate_columns(names)
        self._columns = list(names)

    def _validate_columns(self, names):
        """Validate that given column names can be used."""
        if not is_list_like(names):
            raise ValueError("Columns should be list-like")

        if len(set(names)) != len(names):
            raise ValueError("Duplicate column names")

        if self._data and len(names) != len(self._data[0]):
            raise ValueError("Invalid columns length")

    def _column_name_getter(self, obj):
        """Create callable that returns column names for given obj types."""
        if is_namedtuple(obj):
            # Use namedtuple fields as columns
            def get(obj):
                return list(obj._fields)

        elif is_dict_like(obj):
            # Use dictionary keys as columns
            def get(obj):
                return list(obj.keys())

        elif is_list_like(obj):
            # Use either predefined columns, or
            # generate range-based column values
            predefined = list(self._columns)

            def get(obj):
                count = len(obj)
                if predefined:
                    if count > len(predefined):
                        raise ValueError(
                            f"Data had more than defined {len(predefined)} columns"
                        )
                    return predefined[:count]
                else:
                    return list(range(count))

        else:
            # Fallback to single column
            def get(_):
                return self._columns[:1] if self._columns else [0]

        return get

    def _column_value_getter(self, obj):
        """Create callable that returns column values for given object types."""
        if is_namedtuple(obj):
            # Get values using properties
            def get(obj, column):
                return getattr(obj, column, None)

        elif is_dict_like(obj):
            # Get values using dictionary keys
            def get(obj, column):
                return obj.get(column)

        elif is_list_like(obj):
            # Get values using list indexes
            def get(obj, column):
                col = self.column_location(column)
                try:
                    return obj[col]
                except IndexError:
                    return None

        else:
            # Fallback to single column
            def get(obj, _):
                return obj

        return get

    def _sort_columns(self, order):
        """Sort columns to match given order."""
        unknown = set(self._columns) - set(order)
        if unknown:
            names = ", ".join(str(name) for name in unknown)
            raise ValueError(f"Unknown columns: {names}")

        cols = [self.column_location(column) for column in order]

        self._columns = [self._columns[col] for col in cols]
        self._data = [[row[col] for col in cols] for row in self._data]

    def _validate_self(self):
        """Validate that internal data is valid and coherent."""
        self._validate_columns(self._columns)

        if self._data:
            head = self._data[0]
            if len(head) != len(self._columns):
                raise ValueError("Columns length does not match data")

    def index_location(self, value):
        try:
            value = int(value)
        except ValueError as err:
            raise ValueError(f"Index is not a number: {value}") from err

        if value < 0:
            value += self.size

        if self.size == 0:
            raise IndexError("No rows in table")

        if (value < 0) or (value >= self.size):
            raise IndexError(f"Index ({value}) out of range (0..{self.size - 1})")

        return value

    def column_location(self, value):
        """Find location for column value."""

        # Try to use as-is
        try:
            return self._columns.index(value)
        except ValueError:
            pass

        # Try as integer index
        try:
            value = int(value)

            if value in self._columns:
                location = self._columns.index(value)
            elif value < 0:
                location = value + len(self._columns)
            else:
                location = value

            size = len(self._columns)
            if size == 0:
                raise IndexError("No columns in table")

            if location >= size:
                raise IndexError(f"Column ({location}) out of range (0..{size - 1})")

            return location
        except ValueError:
            pass

        # No matches
        options = ", ".join(str(col) for col in self._columns)
        raise ValueError(f"Unknown column name: {value}, current columns: {options}")

    def __getitem__(self, key):
        """Helper method for accessing items in the Table.

        Examples:
            table[:10]           First 10 rows
            table[0,1]           Value in first row and second column
            table[2:10,"email"]  Values in "email" column for rows 3 to 11
        """
        # Both row index and columns given
        if isinstance(key, tuple):
            index, column = key
            index = self._slice_index(index) if isinstance(index, slice) else index
            return self.get(indexes=index, columns=column, as_list=True)
        # Row indexed with slice, all columns
        elif isinstance(key, slice):
            return self.get(indexes=self._slice_index(key), as_list=True)
        # Single row
        else:
            return self.get(indexes=key, as_list=True)

    def __setitem__(self, key, value):
        """Helper method for setting items in the Table.

        Examples:
            table[5]  = ["Mikko", "Mallikas"]
            table[:2] = [["Marko", "Markonen"], ["Pentti", "Penttinen"]]
        """
        # Both row index and columns given
        if isinstance(key, tuple):
            index, column = key
            index = self._slice_index(index) if isinstance(index, slice) else index
            return self.set(indexes=index, columns=column, values=value)
        # Row indexed with slice, all columns
        elif isinstance(key, slice):
            return self.set(indexes=self._slice_index(key), values=value)
        # Single row
        else:
            return self.set(indexes=key, values=value)

    def _slice_index(self, slicer):
        """Create list of index values from slice object."""
        if slicer.start is not None:
            start = slicer.start
        else:
            start = 0

        if slicer.stop is not None:
            end = slicer.stop
        else:
            end = self.size

        if not isinstance(start, int) or not isinstance(end, int):
            raise IndexError("Index slices should be integers")

        if start < 0:
            start = self.size + start

        if end < 0:
            end = self.size + end

        return list(range(start, end))

    def copy(self):
        """Create a copy of this table."""
        return copy.deepcopy(self)

    def clear(self):
        """Remove all rows from this table."""
        self._data = []

    def head(self, rows, as_list=False):
        """Return first n rows of table."""
        indexes = self.index[: int(rows)]
        return self.get_table(indexes, as_list=as_list)

    def tail(self, rows, as_list=False):
        """Return last n rows of table."""
        indexes = self.index[-int(rows) :]
        return self.get_table(indexes, as_list=as_list)

    def get(self, indexes=None, columns=None, as_list=False):
        """Get values from table. Return type depends on input dimensions.

        If `indexes` and `columns` are scalar, i.e. not lists:
            Returns single cell value

        If either `indexes` or `columns` is a list:
            Returns matching row or column

        If both `indexes` and `columns` are lists:
            Returns a new Table instance with matching cell values

        :param indexes: List of indexes, or all if not given
        :param columns: List of columns, or all if not given
        """
        indexes = if_none(indexes, self.index)
        columns = if_none(columns, self._columns)

        if is_list_like(indexes) and is_list_like(columns):
            return self.get_table(indexes, columns, as_list)
        elif not is_list_like(indexes) and is_list_like(columns):
            return self.get_row(indexes, columns, as_list)
        elif is_list_like(indexes) and not is_list_like(columns):
            return self.get_column(columns, indexes, as_list)
        else:
            return self.get_cell(indexes, columns)

    def get_cell(self, index, column):
        """Get single cell value."""
        idx = self.index_location(index)
        col = self.column_location(column)

        return self._data[idx][col]

    def get_row(self, index, columns=None, as_list=False):
        """Get column values from row.

        :param index:   Index for row
        :param columns: Column names to include, or all if not given
        :param as_list: Return row as dictionary, instead of list
        """
        columns = if_none(columns, self._columns)
        idx = self.index_location(index)

        if as_list:
            row = []
            for column in columns:
                col = self.column_location(column)
                row.append(self._data[idx][col])
            return row
        else:
            row = {}
            for column in columns:
                col = self.column_location(column)
                row[self._columns[col]] = self._data[idx][col]
            return row

    def get_column(self, column, indexes=None, as_list=False):
        """Get row values from column.

        :param columns: Name for column
        :param indexes: Row indexes to include, or all if not given
        :param as_list: Return column as dictionary, instead of list
        """
        indexes = if_none(indexes, self.index)
        col = self.column_location(column)

        if as_list:
            column = []
            for index in indexes:
                idx = self.index_location(index)
                column.append(self._data[idx][col])
            return column
        else:
            column = {}
            for index in indexes:
                idx = self.index_location(index)
                column[idx] = self._data[idx][col]
            return column

    def get_table(self, indexes=None, columns=None, as_list=False):
        """Get a new table from all cells matching indexes and columns."""
        indexes = if_none(indexes, self.index)
        columns = if_none(columns, self._columns)

        if indexes == self.index and columns == self._columns:
            return self.copy()

        idxs = [self.index_location(index) for index in indexes]
        cols = [self.column_location(column) for column in columns]
        data = [[self._data[idx][col] for col in cols] for idx in idxs]

        if as_list:
            return data
        else:
            return Table(data=data, columns=columns)

    def get_slice(self, start=None, end=None):
        """Get a new table from rows between start and end index."""
        index = self._slice_index(slice(start, end))
        return self.get_table(index, self._columns)

    def _add_row(self, index):
        """Add a new empty row into the table."""
        if index is None:
            index = self.size

        if index < self.size:
            raise ValueError(f"Duplicate row index: {index}")

        for empty in range(self.size, index):
            self._add_row(empty)

        self._data.append([None] * len(self._columns))

        return self.size - 1

    def _add_column(self, column):
        """Add a new empty column into the table."""
        if column is None:
            column = len(self._columns)

        if column in self._columns:
            raise ValueError(f"Duplicate column name: {column}")

        if isinstance(column, int):
            assert column >= len(self._columns)
            for empty in range(len(self._columns), column):
                self._add_column(empty)

        self._columns.append(column)
        for idx in self.index:
            row = self._data[idx]
            row.append(None)

        return len(self._columns) - 1

    def set(self, indexes=None, columns=None, values=None):
        """Sets multiple cell values at a time.

        Both `indexes` and `columns` can be scalar or list-like,
        which enables setting individual cells, rows/columns, or regions.

        If `values` is scalar, all matching cells will be set to that value.
        Otherwise the length should match the cell count defined by the
        other parameters.
        """
        indexes = to_list(if_none(indexes, self.index))
        columns = to_list(if_none(columns, self._columns))

        size = len(indexes) + len(columns)
        values = to_list(values, size=size)
        if not len(values) == size:
            raise ValueError("Values size does not match indexes and columns")

        for index in indexes:
            idx = self.index_location(index)
            for column in columns:
                col = self.column_location(column)
                self.set_cell(index, column, values[idx + col])

    def set_cell(self, index, column, value):
        """Set individual cell value.
        If either index or column is missing, they are created.
        """
        try:
            idx = self.index_location(index)
        except (IndexError, ValueError):
            idx = self._add_row(index)

        try:
            col = self.column_location(column)
        except (IndexError, ValueError):
            col = self._add_column(column)

        self._data[idx][col] = value

    def set_row(self, index, values):
        """Set values in row. If index is missing, it is created."""
        try:
            idx = self.index_location(index)
        except (IndexError, ValueError):
            idx = self._add_row(index)

        column_values = self._column_value_getter(values)
        row = [column_values(values, column) for column in self._columns]

        self._data[idx] = row

    def set_column(self, column, values):
        """Set values in column. If column is missing, it is created."""
        values = to_list(values, size=self.size)

        if len(values) != self.size:
            raise ValueError(
                f"Values length ({len(values)}) should match data length ({self.size})"
            )

        if column not in self._columns:
            self._add_column(column)

        for index in self.index:
            self.set_cell(index, column, values[index])

    def append_row(self, row=None):
        """Append new row to table."""
        self.set_row(self.size, row)

    def append_rows(self, rows):
        """Append multiple rows to table."""
        for row in rows:
            self.append_row(row)

    def append_column(self, column=None, values=None):
        if column is not None and column in self._columns:
            raise ValueError(f"Column already exists: {column}")

        self.set_column(column, values)

    def delete_rows(self, indexes):
        """Remove rows with matching indexes."""
        indexes = to_list(indexes)

        unknown = set(indexes) - set(self.index)
        if unknown:
            names = ", ".join(str(name) for name in unknown)
            raise ValueError(f"Unable to remove unknown rows: {names}")

        for index in sorted(indexes, reverse=True):
            del self._data[index]

    def delete_columns(self, columns):
        """Remove columns with matching names."""
        columns = to_list(columns)

        unknown = set(columns) - set(self._columns)
        if unknown:
            names = ", ".join(str(name) for name in unknown)
            raise ValueError(f"Unable to remove unknown columns: {names}")

        for column in columns:
            col = self.column_location(column)
            for idx in self.index:
                del self._data[idx][col]
            del self._columns[col]

    def append_table(self, table):
        """Append data from table to current data."""
        if not table:
            return

        indexes = []
        for idx in table.index:
            index = self.size + idx
            indexes.append(index)

        self.set(indexes=indexes, columns=table.columns, values=table.data)

    def sort_by_column(self, columns, ascending=False):
        """Sort table by columns."""
        columns = to_list(columns)

        # Create sort criteria list, with each row as tuple of column values
        values = (self.get_column(column, as_list=True) for column in columns)
        values = list(zip(*values))
        assert len(values) == self.size

        def sorter(row):
            """Sort table by given values, while allowing for disparate types.
            Order priority:
                - Values by typename
                - Numeric types
                - None values
            """
            criteria = []
            for value in row[1]:  # Ignore enumeration
                criteria.append(
                    (
                        value is not None,
                        "" if isinstance(value, Number) else type(value).__name__,
                        value,
                    )
                )
            return criteria

        # Store original index order using enumerate() before sort,
        # and use it to sort data later
        values = sorted(enumerate(values), key=sorter, reverse=ascending)
        idxs = [value[0] for value in values]

        # Re-order data
        self._data = [self._data[idx] for idx in idxs]

    def group_by_column(self, column):
        """Group rows by column value and return as list of tables."""
        # TODO: Ensure original index is maintained?
        ref = self.copy()
        ref.sort_by_column(column)

        col = self.column_location(column)
        groups = groupby(ref.data, itemgetter(col))

        result = []
        ref.clear()
        for _, group in groups:
            table = ref.copy()
            table.append_rows(group)
            result.append(table)

        return result

    def filter_by_column(self, column, condition):
        """Remove rows by evaluating `condition` for all `column`
        values. All rows where it evaluates to falsy are removed.

        The filtering will be done in-place.
        """
        filtered = []
        for index in self.index:
            value = self.get_cell(index, column)
            if not condition(value):
                filtered.append(index)

        self.delete_rows(filtered)

    def iter_lists(self, with_index=True):
        """Iterate rows with values as lists."""
        for idx, row in zip(self.index, self._data):
            if with_index:
                yield idx, list(row)
            else:
                yield list(row)

    def iter_dicts(self, with_index=True) -> Generator[Dict[Column, Any], None, None]:
        """Iterate rows with values as dicts."""
        for index in self.index:
            row = {"index": index} if with_index else {}
            for column in self._columns:
                row[column] = self.get_cell(index, column)
            yield row

    def iter_tuples(self, with_index=True, name="Row"):
        """Iterate rows with values as namedtuples.
        Converts column names to valid Python identifiers,
        e.g. "First Name" -> "First_Name"
        """
        columns = {column: to_identifier(column) for column in self._columns}

        fields = ["index"] if with_index else []
        fields.extend(columns.values())

        container = namedtuple(name, fields)
        for row in self.iter_dicts(with_index):
            row = {columns[k]: v for k, v in row.items()}
            yield container(**row)

    def to_list(self, with_index=True):
        """Convert table to list representation."""
        export = []

        for index in self.index:
            row = OrderedDict()
            if with_index:
                row["index"] = index
            for column in self._columns:
                row[column] = self.get_cell(index, column)
            export.append(row)

        return export

    def to_dict(self, with_index=True):
        """Convert table to dict representation."""
        export = OrderedDict()

        if with_index:
            export["index"] = self.index

        for column in self._columns:
            export[column] = []

        for index in self.index:
            for column in self._columns:
                value = self.get_cell(index, column)
                export[column].append(value)

        return export


class Tables:
    """`Tables` is a library for manipulating tabular data inside Robot Framework.

    It can import data from various sources and apply different operations to it.
    Common use-cases are reading and writing CSV files, inspecting files in
    directories, or running tasks using existing Excel data.

    **Import types**

    The data a table can be created from can be of two main types:

    1. An iterable of individual rows, like a list of lists, or list of dictionaries
    2. A dictionary of columns, where each dictionary value is a list of values

    For instance, these two input values:

    .. code-block:: python

        data1 = [
            {"name": "Mark", "age": 58},
            {"name": "John", "age": 22},
            {"name": "Adam", "age": 67},
        ]

        data2 = {
            "name": ["Mark", "John", "Adam"],
            "age":  [    58,     22,     67],
        }

    Would both result in the following table:

    +-------+------+-----+
    | Index | Name | Age |
    +=======+======+=====+
    | 0     | Mark | 58  |
    +-------+------+-----+
    | 1     | John | 22  |
    +-------+------+-----+
    | 2     | Adam | 67  |
    +-------+------+-----+

    **Indexing columns and rows**

    Columns can be referred to in two ways: either with a unique string
    name or their position as an integer. Columns can be named either when
    the table is created, or they can be (re)named dynamically with keywords.
    The integer position can always be used, and it starts from zero.

    For instance, a table with columns "Name", "Age", and "Address" would
    allow referring to the "Age" column with either the name "Age" or the
    number 1.

    Rows do not have a name, but instead only have an integer index. This
    index also starts from zero. Keywords where rows are indexed also support
    negative values, which start counting backwards from the end.

    For instance, in a table with five rows, the first row could be referred
    to with the number 0. The last row could be accessed with either 4 or
    -1.

    **Examples**

    **Robot Framework**

    The `Tables` library can load tabular data from various other libraries
    and manipulate it inside Robot Framework.

    .. code-block:: robotframework

        *** Settings ***
        Library    RPA.Tables

        *** Keywords ***
        Files to Table
            ${files}=    List files in directory    ${CURDIR}
            ${files}=    Create table    ${files}
            Filter table by column    ${files}    size  >=  ${1024}
            FOR    ${file}    IN    @{files}
                Log    ${file}[name]
            END
            Write table to CSV    ${files}    ${OUTPUT_DIR}${/}files.csv

    **Python**

    The library is also available directly through Python, where it
    is easier to handle multiple different tables or do more bespoke
    manipulation operations.

    .. code-block:: python

        from RPA.Tables import Tables

        library = Tables()
        orders = library.read_table_from_csv(
            "orders.csv", columns=["name", "mail", "product"]
        )

        customers = library.group_table_by_column(rows, "mail")
        for customer in customers:
            for order in customer:
                add_cart(order)
            make_order()
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def _requires_table(obj: Any):
        if not isinstance(obj, Table):
            raise TypeError("Keyword requires Table object")

    def create_table(
        self, data: Data = None, trim: bool = False, columns: List[str] = None
    ) -> Table:
        """Create Table object from data.

        Data can be a combination of various iterable containers, e.g.
        list of lists, list of dicts, dict of lists.

        :param data:    Source data for table
        :param trim:    Remove all empty rows from the end of the worksheet,
                        default `False`
        :param columns: Names of columns (optional)

        See the main library documentation for more information about
        supported data types.
        """
        table = Table(data, columns)

        if trim:
            self.trim_empty_rows(table)
            self.trim_column_names(table)

        self.logger.info("Created table: %s", table)
        notebook_table(self.table_head(table, 10))

        return table

    def export_table(
        self, table: Table, with_index: bool = False, as_list: bool = True
    ) -> Union[List, Dict]:
        """Convert a table object into standard Python containers.

        :param table:       Table to convert to dict
        :param with_index:  Include index in values
        :param as_list:     Export data as list instead of dict

        Example:

        .. code-block:: robotframework

            ${orders}=       Read worksheet as table    orders.xlsx
            Sort table by column    ${orders}    CustomerId
            ${export}=       Export table    ${orders}
            # The following keyword expects a dictionary:
            Write as JSON    ${export}
        """
        self._requires_table(table)
        if as_list:
            return table.to_list(with_index)
        else:
            return table.to_dict(with_index)

    def copy_table(self, table: Table) -> Table:
        """Make a copy of a table object.

        :param table:   Table to copy
        """
        self._requires_table(table)
        return table.copy()

    def clear_table(self, table: Table):
        """Clear table in-place, but keep columns.

        :param table:   Table to clear
        """
        self._requires_table(table)
        table.clear()

    def merge_tables(self, *tables: Table, index: Optional[str] = None) -> Table:
        """Create a union of two tables and their contents.

        :param tables: Tables to merge
        :param index:  Column name to use as index for merge

        By default rows from all tables are appended one after the other.
        Optionally a column name can be given with ``index``, which is
        used to merge rows together.

        Example:

        For instance, a ``name`` column could be used to identify
        unique rows and the merge operation should overwrite values
        instead of appending multiple copies of the same name.

        ====== =====
        Name   Price
        ====== =====
        Egg    10.0
        Cheese 15.0
        Ham    20.0
        ====== =====

        ====== =====
        Name   Stock
        ====== =====
        Egg    12.0
        Cheese 99.0
        Ham    0.0
        ====== =====

        .. code-block:: robotframework

            ${products}=    Merge tables    ${prices}    ${stock}    index=Name
            FOR    ${product}    IN    @{products}
                Log many
                ...    Product: ${product}[Name]
                ...    Price: ${product}[Price]
                ...    Stock: ${product}[Stock]
            END
        """
        if index is None:
            return self._merge_by_append(tables)
        else:
            return self._merge_by_index(tables, index)

    def _merge_by_append(self, tables: Tuple[Table, ...]):
        """Merge tables by appending columns and rows."""
        columns = uniq(column for table in tables for column in table.columns)

        merged = Table(columns=columns)
        for table in tables:
            merged.append_rows(table)

        return merged

    def _merge_by_index(self, tables: Tuple[Table, ...], index: str):
        """Merge tables by using a column as shared key."""
        columns = uniq(column for table in tables for column in table.columns)
        merged = Table(columns=columns)

        seen = {}

        def find_index(row):
            """Find index for row, if key already exists."""
            value = row[index]
            if value in seen:
                return seen[value]
            for row_ in merged.iter_dicts(True):
                if row_[index] == value:
                    seen[value] = row_["index"]
                    return row_["index"]
            return None

        for table in tables:
            for row in table.iter_dicts(False):
                row_index = find_index(row)
                if row_index is None:
                    merged.append_row(row)
                else:
                    for column, value in row.items():
                        merged.set_cell(row_index, column, value)

        return merged

    def get_table_dimensions(self, table: Table) -> Tuple[int, int]:
        """Return table dimensions, as (rows, columns).

        :param table:    Table to inspect

        Examples:

        .. code-block:: robotframework

            ${rows}  ${columns}=    Get table dimensions    ${table}
            Log    Table has ${rows} rows and ${columns} columns.
        """
        self._requires_table(table)
        notebook_print(text=table.dimensions)
        return table.dimensions

    def rename_table_columns(
        self, table: Table, names: List[Union[str, None]], strict: bool = False
    ):
        """Renames columns in the Table with given values. Columns with
        name as ``None`` will use the previous value.

        :param table:   Table to modify
        :param names:   List of new column names
        :param strict:  If True, raises ValueError if column lengths
                        do not match

        The renaming will be done in-place.

        Examples:

        .. code-block:: robotframework

            ${columns}=    Create list   First  Second  Third
            Rename table columns    ${table}    ${columns}
            # First, Second, Third


            ${columns}=    Create list   Uno  Dos
            Rename table columns    ${table}    ${columns}
            # Uno, Dos, Third
        """
        self._requires_table(table)
        before = table.columns

        if strict and len(before) != len(names):
            raise ValueError("Column lengths do not match")

        after = []
        for old, new in zip_longest(before, names):
            if old is None:
                break
            elif new is None:
                after.append(old)
            else:
                after.append(new)

        table.columns = after

    def add_table_column(
        self, table: Table, name: Optional[str] = None, values: Any = None
    ):
        """Append a column to a table.

        :param table:   Table to modify
        :param name:    Name of new column
        :param values:  Value(s) for new column

        The ``values`` can either be a list of values, one for each row, or
        one single value that is set for all rows.

        Examples:

        .. code-block:: robotframework

            # Add empty column
            Add table column    ${table}

            # Add empty column with name
            Add table column    ${table}    name=Home Address

            # Add new column where every every row has the same value
            Add table column    ${table}    name=TOS    values=${FALSE}

            # Add new column where every row has a unique value
            ${is_first}=    Create list    ${TRUE}    ${FALSE}    ${FALSE}
            Add table column    ${table}    name=IsFirst    values=${is_first}
        """
        self._requires_table(table)
        table.append_column(name, values)

    def add_table_row(self, table: Table, values: Any = None):
        """Append rows to a table.

        :param table:   Table to modify
        :param values:  Value(s) for new row

        The ``values`` can either be a list of values, or a dictionary
        where the keys match current column names. Values for unknown
        keys are discarded.

        It can also be a single value that is set for all columns,
        which is ``None`` by default.

        Example:s

        .. code-block:: robotframework

            # Add empty row
            Add table row    ${table}

            # Add row where every column has the same value
            Add table row    ${table}    Unknown

            # Add values per column
            ${values}=    Create dictionary    Username=Mark    Mail=mark@robocorp.com
            Add table row    ${table}    ${values}
        """
        self._requires_table(table)
        table.append_row(values)

    def get_table_row(
        self, table: Table, row: Index, as_list: bool = False
    ) -> Union[Dict, List]:
        """Get a single row from a table.

        :param table:   Table to read
        :param row:     Row to read
        :param as_list: Return list instead of dictionary

        Examples:

        .. code-block:: robotframework

            ${first}=    Get table row    ${orders}
            Log     Handling order: ${first}[Order ID]

            ${row}=      Get table row    ${data}    -1    as_list=${TRUE}
            FOR    ${value}    IN    @{row}
                Log    Data point: ${value}
            END
        """
        self._requires_table(table)
        values = table.get_row(row, as_list=as_list)
        notebook_print(text=values)
        return values

    def get_table_column(self, table: Table, column: Column) -> List:
        """Get all values for a single column in a table.

        :param table:   Table to read
        :param column:  Column to read

        Example:

        .. code-block:: robotframework

            ${emails}=    Get table column    ${users}    E-Mail Address
            FOR    ${email}    IN    @{emails}
                Send promotion    ${email}
            END
        """
        self._requires_table(table)
        col = table.get_column(column, as_list=True)
        return col

    def set_table_row(self, table: Table, row: Index, values: Any):
        """Assign values to a row in the table.

        :param table:   Table to modify
        :param row:     Row to modify
        :param values:  Value(s) to set

        The ``values`` can either be a list of values, or a dictionary
        where the keys match current column names. Values for unknown
        keys are discarded.

        It can also be a single value that is set for all columns.

        Examples:

        .. code-block:: robotframework

            ${columns}=  Create list     One  Two  Three
            ${table}=    Create table    columns=${columns}

            ${values}=   Create list     1  2  3
            Set table row    ${table}    0    ${values}

            ${values}=   Create dictionary    One=1  Two=2  Three=3
            Set table row    ${table}    1    ${values}

            Set table row    ${table}    2    ${NONE}
        """
        self._requires_table(table)
        table.set_row(row, values)

    def set_table_column(self, table: Table, column: Column, values: Any):
        """Assign values to entire column in the table.

        :param table:   Table to modify
        :param column:  Column to modify
        :param values:  Value(s) to set

        The ``values`` can either be a list of values, one for each row, or
        one single value that is set for all rows.

        Examples:

        .. code-block:: robotframework

            # Set different value for each row (sizes must match)
            ${ids}=    Create list    1  2  3  4  5
            Set table column    ${users}    userId    ${ids}

            # Set the same value for all rows
            Set table column    ${users}    email     ${NONE}
        """
        self._requires_table(table)
        table.set_column(column, values)

    def pop_table_row(
        self, table: Table, row: Optional[Index] = None, as_list: bool = False
    ) -> Union[Dict, List]:
        """Remove row from table and return it.

        :param table:   Table to modify
        :param row:     Row index, pops first row if none given
        :param as_list: Return list instead of dictionary

        Examples:

        .. code-block:: robotframework

            ${first}=    Pop table row    ${orders}
            Log     Handling order: ${first}[Order ID]

            ${row}=      Pop table row    ${data}    -1    as_list=${TRUE}
            FOR    ${value}    IN    @{row}
                Log    Data point: ${value}
            END
        """
        self._requires_table(table)
        row = if_none(row, table.index[0])

        values = table.get_row(row, as_list=as_list)
        table.delete_rows(row)
        return values

    def pop_table_column(
        self, table: Table, column: Optional[Column] = None
    ) -> Union[Dict, List]:
        """Remove column from table and return it.

        :param table:   Table to modify
        :param column:  Column to remove

        Examples:

        .. code-block:: robotframework

            # Remove column from table and discard it
            Pop table column    ${users}   userId

            # Remove column from table and iterate over it
            ${ids}=    Pop table column    ${users}    userId
            FOR    ${id}    IN    @{ids}
                Log    User id: ${id}
            END
        """
        self._requires_table(table)
        column: Column = if_none(column, table.columns[0])

        values = self.get_table_column(table, column)
        table.delete_columns(column)
        return values

    def get_table_slice(
        self, table: Table, start: Optional[Index] = None, end: Optional[Index] = None
    ) -> Union[Table, List[List]]:
        """Return a new Table from a range of given Table rows.

        :param table:   Table to read from
        :param start:   Start index (inclusive)
        :param start:   End index (exclusive)

        If ``start`` is not defined, starts from the first row.
        If ``end`` is not defined, stops at the last row.

        Examples:

        .. code-block:: robotframework

            # Get all rows except first five
            ${slice}=    Get table slice    ${table}    start=5

            # Get rows at indexes 5, 6, 7, 8, and 9
            ${slice}=    Get table slice    ${table}    start=5    end=10

            # Get all rows except last five
            ${slice}=    Get table slice    ${table}    end=-5
        """
        self._requires_table(table)
        return table.get_slice(start, end)

    def set_row_as_column_names(self, table: Table, row: Index):
        """Set existing row as names for columns.

        :param table: Table to modify
        :param row:   Row to use as column names

        Examples:

        .. code-block:: robotframework

            ${table}=    Read table from CSV    data.csv
            Set row as column names    ${table}    0
        """
        values = self.pop_table_row(table, row, as_list=True)
        table.columns = values

    def table_head(
        self, table: Table, count: int = 5, as_list: bool = False
    ) -> Union[Table, List[List]]:
        """Return first ``count`` rows from a table.

        :param table:   Table to read from
        :param count:   Number of lines to read
        :param as_list: Return list instead of Table

        Examples:

        .. code-block:: robotframework

            # Get the first 10 employees
            ${employees}=    Read worksheet as table    employees.xlsx
            ${first}=        Table head    ${employees}    10
        """
        self._requires_table(table)
        return table.head(count, as_list)

    def table_tail(
        self, table: Table, count: int = 5, as_list: bool = False
    ) -> Union[Table, List[List]]:
        """Return last ``count`` rows from a table.

        :param table:   Table to read from
        :param count:   Number of lines to read
        :param as_list: Return list instead of Table

        Examples:

        .. code-block:: robotframework

            # Get the last 10 orders
            ${orders}=    Read worksheet as table    orders.xlsx
            ${latest}=    Table tail    ${orders}    10
        """
        self._requires_table(table)
        return table.tail(count, as_list)

    def get_table_cell(self, table: Table, row: Index, column: Column) -> Any:
        """Get a cell value from a table.

        :param table:   Table to read from
        :param row:     Row of cell
        :param column:  Column of cell

        Examples:

        .. code-block:: robotframework

            # Get the value in the first row and first column
            Get table cell    ${table}    0    0

            # Get the value in the last row and first column
            Get table cell    ${table}   -1    0

            # Get the value in the third row and column "Name"
            Get table cell    ${table}    2    Name
        """
        self._requires_table(table)
        return table.get_cell(row, column)

    def set_table_cell(self, table: Table, row: Index, column: Column, value: Any):
        """Set a cell value in a table.

        :param table:   Table to modify to
        :param row:     Row of cell
        :param column:  Column of cell
        :param value:   Value to set

        Examples:

        .. code-block:: robotframework

            # Set the value in the first row and first column to "First"
            Set table cell    ${table}    0    0       First

            # Set the value in the last row and first column to "Last"
            Set table cell    ${table}   -1    0       Last

            # Set the value in the third row and column "Name" to "Unknown"
            Set table cell    ${table}    2    Name    Unknown
        """
        self._requires_table(table)
        table.set_cell(row, column, value)

    def find_table_rows(self, table: Table, column: Column, operator: str, value: Any):
        """Find all rows in a table which match a condition for a
        given column.

        :param table:    Table to find from
        :param column:   Name of column to search
        :param operator: Comparison operator
        :param value:    Value to compare against

        Supported operators:

        ============ ========================================
        Operator     Description
        ============ ========================================
        >            Cell value is larger than
        <            Cell value is smaller than
        >=           Cell value is larger or equal than
        <=           Cell value is smaller or equal than
        ==           Cell value is equal to
        !=           Cell value is not equal to
        is           Cell value is the same object
        not is       Cell value is not the same object
        contains     Cell value contains given value
        not contains Cell value does not contain given value
        in           Cell value is in given value
        not in       Cell value is not in given value
        ============ ========================================

        Returns the matches as a new Table instance.

        Examples:

        .. code-block:: robotframework

            # Find all rows where price is over 200
            @{rows}=    Find table rows    Price  >  ${200}

            # Find all rows where the status does not contain "removed"
            @{rows}=    Find table rows    Status    not contains    removed
        """
        self._requires_table(table)

        condition = to_condition(operator, value)

        matches = []
        for index in table.index:
            cell = table.get_cell(index, column)
            if condition(cell):
                matches.append(index)

        return table.get_table(matches)

    def sort_table_by_column(
        self, table: Table, column: Column, ascending: bool = False
    ):
        """Sort a table in-place according to ``column``.

        :param table:       Table to sort
        :param column:      Column to sort with
        :param ascending:   Table sort order

        Example:

        .. code-block:: robotframework

            ${orders}=    Read worksheet as table    orders.xlsx
            Sort table by column    ${orders}    order_date
        """
        self._requires_table(table)
        table.sort_by_column(column, ascending=ascending)

    def group_table_by_column(self, table: Table, column: Column) -> List[Table]:
        """Group a table by ``column`` and return a list of grouped Tables.

        :param table:   Table to use for grouping
        :param column:  Column which is used as grouping criteria

        Example:

        .. code-block:: robotframework

            ${orders}=    Read worksheet as table    orders.xlsx
            @{groups}=    Group table by column    ${orders}    customer
            FOR    ${group}    IN    @{groups}
                # Process all orders for the customer at once
                Process order    ${group}
            END
        """
        self._requires_table(table)
        groups = table.group_by_column(column)
        self.logger.info("Found %s groups", len(groups))
        return groups

    def filter_table_by_column(
        self, table: Table, column: Column, operator: str, value: Any
    ):
        """Remove all rows where column values don't match the
        given condition.

        :param table:     Table to filter
        :param column:    Column to filter with
        :param operator:  Filtering operator, e.g. >, <, ==, contains
        :param value:     Value to compare column to (using operator)

        See the keyword ``Find table rows`` for all supported operators
        and their descriptions.

        The filtering will be done in-place.

        Examples:

        .. code-block:: robotframework

            # Only accept prices that are non-zero
            Filter table by column    ${table}   price  !=  ${0}

            # Remove uwnanted product types
            @{types}=    Create list    Unknown    Removed
            Filter table by column    ${table}   product_type  not in  ${types}
        """
        self._requires_table(table)

        condition = to_condition(operator, value)

        before = len(table)
        table.filter_by_column(column, condition)
        after = len(table)

        self.logger.info("Filtered %d rows", after - before)

    def filter_empty_rows(self, table: Table):
        """Remove all rows from a table which have only ``None`` values.

        :param table:   Table to filter

        The filtering will be done in-place.

        Example:

        .. code-block:: robotframework

            ${table}=    Read worksheet as table    orders.xlsx
            Filter empty rows    ${table}
        """
        self._requires_table(table)

        empty = []
        for idx, row in table.iter_lists():
            if all(value is None for value in row):
                empty.append(idx)

        table.delete_rows(empty)

    def trim_empty_rows(self, table: Table):
        """Remove all rows from the *end* of a table
        which have only ``None`` as values.

        :param table:    Table to filter

        The filtering will be done in-place.

        Example:

        .. code-block:: robotframework

            ${table}=    Read worksheet as table    orders.xlsx
            Trim empty rows    ${table}
        """
        self._requires_table(table)

        empty = []
        for idx in reversed(table.index):
            row = table[idx]
            if any(value is not None for value in row):
                break
            empty.append(idx)

        table.delete_rows(empty)

    def trim_column_names(self, table: Table):
        """Remove all extraneous whitespace from column names.

        :param table:    Table to filter

        The filtering will be done in-place.

        Example:

        .. code-block:: robotframework

            ${table}=    Read table from CSV    data.csv
            Log    ${table.columns}  # "One", "Two ", "  Three "
            Trim column names     ${table}
            Log    ${table-columns}  # "One", "Two", "Three"
        """
        self._requires_table(table)
        table.columns = [
            column.strip() if isinstance(column, str) else column
            for column in table.columns
        ]

    @keyword("Read table from CSV")
    def read_table_from_csv(
        self,
        path: str,
        header: Optional[bool] = None,
        columns: Optional[List[str]] = None,
        dialect: Optional[Dialect] = None,
        delimiters: Optional[str] = None,
        column_unknown: str = "Unknown",
        encoding: Optional[str] = None,
    ) -> Table:
        """Read a CSV file as a table.

        :param path:            Path to CSV file
        :param header:          CSV file includes header
        :param columns:         Names of columns in resulting table
        :param dialect:         Format of CSV file
        :param delimiters:      String of possible delimiters
        :param column_unknown:  Column name for unknown fields
        :param encoding:        Text encoding for input file,
                                uses system encoding by default

        By default attempts to deduce the CSV format and headers
        from a sample of the input file. If it's unable to determine
        the format automatically, the dialect and header will
        have to be defined manually.

        Valid ``dialect`` values are ``excel``, ``excel-tab``, and ``unix``,
        and ``header`` is boolean argument (``True``/``False``). Optionally a
        set of valid ``delimiters`` can be given as a string.

        The ``columns`` argument can be used to override the names of columns
        in the resulting table. The amount of columns must match the input
        data.

        If the source data has a header and rows have more fields than
        the header defines, the remaining values are put into the column
        given by ``column_unknown``. By default it has the value "Unknown".

        Examples:

        .. code-block:: robotframework

            # Source dialect is deduced automatically
            ${table}=    Read table from CSV    export.csv
            Log   Found columns: ${table.columns}

            # Source dialect is known and given explicitly
            ${table}=    Read table from CSV    export-excel.csv    dialect=excel
            Log   Found columns: ${table.columns}
        """
        sniffer = csv.Sniffer()
        with open(path, newline="", encoding=encoding) as fd:
            sample = fd.read(1024)

        if dialect is None:
            dialect_name = sniffer.sniff(sample, delimiters)
        elif isinstance(dialect, Dialect):
            dialect_name = dialect.value
        else:
            dialect_name = Dialect(dialect).value

        if header is None:
            header = sniffer.has_header(sample)

        with open(path, newline="") as fd:
            if header:
                reader = csv.DictReader(
                    fd, dialect=dialect_name, restkey=str(column_unknown)
                )
            else:
                reader = csv.reader(fd, dialect=dialect_name)
            rows = list(reader)

        table = Table(rows, columns)
        notebook_table(self.table_head(table, 10))

        if header and column_unknown in table.columns:
            self.logger.warning(
                "CSV file (%s) had fields not defined in header, "
                "which can be the result of a wrong dialect",
                path,
            )

        return table

    @keyword("Write table to CSV")
    def write_table_to_csv(
        self,
        table: Table,
        path: str,
        header: bool = True,
        dialect: Dialect = Dialect.Excel,
        encoding: Optional[str] = None,
    ):
        """Write a table as a CSV file.

        :param table:    Table to write
        :param path:     Path to write to
        :param header:   Write columns as header to CSV file
        :param dialect:  The format of output CSV
        :param encoding: Text encoding for output file,
                         uses system encoding by default

        Valid ``dialect`` values are ``Excel``, ``ExcelTab``, and ``Unix``.

        Example:

        .. code-block:: robotframework

            ${sheet}=    Read worksheet as table    orders.xlsx    header=${TRUE}
            Write table to CSV    ${sheet}    output.csv
        """
        self._requires_table(table)

        if isinstance(dialect, str):
            dialect = Dialect(dialect)

        with open(path, mode="w", newline="", encoding=encoding) as fd:
            writer = csv.DictWriter(fd, fieldnames=table.columns, dialect=dialect.value)

            if header:
                writer.writeheader()

            for row in table.iter_dicts(with_index=False):
                writer.writerow(row)
