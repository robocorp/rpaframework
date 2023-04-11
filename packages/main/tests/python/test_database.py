import functools
import sqlite3

try:
    from contextlib import nullcontext
except ImportError:
    from contextlib import suppress as nullcontext

import pytest
from RPA.Database import Database

from . import RESOURCES_DIR, RESULTS_DIR, temp_filename


DB_PATH = str(RESULTS_DIR / "database.db")
RETURNING_REASON = "On some systems SQLite fails to recognize the RETURNING properly"


def _get_library(**kwargs):
    lib = Database()
    lib.connect_to_database("sqlite3", DB_PATH, **kwargs)
    return lib


@pytest.fixture
def library():
    return _get_library(autocommit=True)


@pytest.fixture
def library_no_commit():
    return _get_library(autocommit=False)


def _ensure_orders(query):
    query("DROP TABLE IF EXISTS orders;")
    query("CREATE TABLE orders(id INTEGER PRIMARY KEY, name TEXT);")
    query('INSERT INTO orders(id, name) VALUES(1, "my-1st-order"),(2, "my-2nd-order");')


@pytest.mark.xfail(reason=RETURNING_REASON)
def test_query(library):
    _ensure_orders(library.query)
    orders_ids = library.query(
        'INSERT INTO orders(id, name) VALUES(3, "my-3rd-order");'
    )
    assert orders_ids[0][0] == 3

    orders = library.query("SELECT * FROM orders")
    order_names = [order["name"] for order in orders]
    assert order_names == ["my-1st-order", "my-2nd-order", "my-3rd-order"]


@pytest.mark.xfail(reason=RETURNING_REASON)
def test_query_parameterized_data(library):
    _ensure_orders(library.query)
    # This test uses a hardcoded string for simplicity, but in a real scenario the untrusted data
    # would be coming from an external source (Excel file, HTTP request, etc.)
    untrusted_data = "my-3rd-order"

    # Each database uses a particular style of formatting. SQLite3 uses '?' for instance.
    # For additional information about specific databases see https://bobby-tables.com/python
    orders_ids = library.query(
        "INSERT INTO orders(id, name) VALUES(3, ?);", data=(untrusted_data,)
    )

    assert orders_ids[0][0] == 3

    orders = library.query("SELECT * FROM orders")
    order_names = [order["name"] for order in orders]
    assert order_names == ["my-1st-order", "my-2nd-order", "my-3rd-order"]


@pytest.mark.parametrize("commit", [True, False])
def test_query_no_transaction(library_no_commit, commit):
    query = functools.partial(library_no_commit.query, sanstran=True)
    _ensure_orders(query)
    # No explicitly committing will loose all pushed records since auto-commit was
    # disabled in both the DB connection and `query` helper.
    if commit:
        query("COMMIT;")
    library_no_commit.disconnect_from_database()

    # No orders should be available in the database if they weren't committed.
    library_no_commit.connect_to_database("sqlite3", DB_PATH, autocommit=False)
    orders = query("SELECT * FROM orders", as_table=False)
    orders_length = 2 if commit else 0
    assert len(orders) == orders_length


@pytest.mark.parametrize(
    "should_fail, no_trans, orders_nr",
    [
        # Nothing fails since the script alone executes just fine.
        (False, False, 2),
        (False, True, 2),
        # It fails due to lastly added invalid statement.
        (True, False, 0),  # transaction enabled, a rollback is issued when it errors
        (True, True, 2),  # transaction disabled, no implicit rollback happens
    ],
)
def test_execute_sql_script(library_no_commit, should_fail, no_trans, orders_nr):
    sql_data = (RESOURCES_DIR / "script.sql").read_text()
    if should_fail:
        sql_data += "\nINVALID STATEMENT;"
        effect = pytest.raises(sqlite3.OperationalError)
    else:
        effect = nullcontext()
    with temp_filename(content=sql_data, suffix=".sql", mode="w") as sql_script:
        with effect:
            library_no_commit.execute_sql_script(sql_script, sanstran=no_trans)
    if no_trans:
        # Commit what was executed from the script. (even partially when it errors)
        # This way we guarantee the rollback functionality during a script execution
        #  that threw an error.
        library_no_commit.query("COMMIT;")

    orders = library_no_commit.query("SELECT * FROM orders")
    assert len(orders) == orders_nr


@pytest.mark.xfail(reason=RETURNING_REASON)
def test_query_explicit_returning(library):
    _ensure_orders(library.query)
    cursor = library.query(
        'INSERT INTO orders(id, name) VALUES(3, "my-3rd-order") RETURNING id;',
        returning=False,
    )
    assert cursor.fetchall()[0][0] == 3
