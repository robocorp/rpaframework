import logging
from DatabaseLibrary import DatabaseLibrary

from RPA.Tables import Table


class Database(DatabaseLibrary):
    """Library handling different database operations.

    Extends `robotframework-databaselibrary`_.

.. _robotframework-databaselibrary:
    https://github.com/franz-see/Robotframework-Database-Library
    """

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        DatabaseLibrary.__init__(self, *args, **kwargs)

    def database_query_result_as_table(self, query_string):
        """Make database query and return result as `RPA.Table`.

        :param query_string: SQL query string
        :return: query result as `RPA.Table`
        """
        return Table(self.query(query_string, returnAsDict=True))
