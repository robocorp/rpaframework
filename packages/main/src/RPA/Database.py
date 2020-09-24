import importlib
import logging
import sys

from RPA.Tables import Table

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser


class Database:
    """Library handling different database operations."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._dbconnection = None
        self.db_api_module_name = None

    # pylint: disable=R0915
    def connect_to_database(  # noqa: C901
        self,
        module_name=None,
        database=None,
        username=None,
        password=None,
        host=None,
        port=None,
        charset=None,
        config_file="db.cfg",
    ):
        """Connect to database using DB API 2.0 module.

        :param module_name: database module to use
        :param database: name of the database
        :param username: of the user accessing the database
        :param password: of the user accessing the database
        :param host: SQL server address
        :param port: SQL server port
        :param charset: for example, "utf-8", defaults to None
        :param config_file: location of configuration file, defaults to "db.cfg"


        Example:

        .. code-block:: robotframework

            Connect To Database  pymysql  database  username  password  host  port
            Connect To Database  ${CURDIR}${/}resources${/}dbconfig.cfg

        """
        config = ConfigParser.ConfigParser()
        configfile = config.read([config_file])

        if configfile:
            module_name = module_name or config.get("default", "module_name")
            database = database or config.get("default", "database")
            username = username or config.get("default", "username")
            password = (
                password if password is not None else config.get("default", "password")
            )
            host = host or config.get("default", "host") or "localhost"
            port = int(port or config.get("default", "port"))

        if module_name in ("excel", "excelrw"):
            self.db_api_module_name = "pyodbc"
            dbmodule = importlib.import_module("pyodbc")
        else:
            self.db_api_module_name = module_name
            dbmodule = importlib.import_module(module_name)
        if module_name in ["MySQLdb", "pymysql"]:
            port = port or 3306
            self.logger.info(
                "Connecting using : %s.connect(db=%s, user=%s, passwd=%s, host=%s"
                ", port=%s, charset=%s) ",
                module_name,
                database,
                username,
                password,
                host,
                port,
                charset,
            )
            self._dbconnection = dbmodule.connect(
                db=database,
                user=username,
                passwd=password,
                host=host,
                port=port,
                charset=charset,
            )
        elif module_name == "psycopg2":
            port = port or 5432
            self.logger.info(
                "Connecting using : %s.connect(database=%s, user=%s, password=%s, "
                "host=%s, port=%s) ",
                module_name,
                database,
                username,
                password,
                host,
                port,
            )
            self._dbconnection = dbmodule.connect(
                database=database,
                user=username,
                password=password,
                host=host,
                port=port,
            )
        elif module_name in ("pyodbc", "pypyodbc"):
            port = port or 1433
            self.logger.info(
                "Connecting using : %s.connect(DRIVER={SQL Server};SERVER=%s,%s;"
                "DATABASE=%s;UID=%s;PWD=%s)",
                module_name,
                host,
                port,
                database,
                username,
                password,
            )
            self._dbconnection = dbmodule.connect(
                "DRIVER={SQL Server};SERVER=%s,%s;DATABASE=%s;UID=%s;PWD=%s"
                % (host, port, database, username, password)
            )
        elif module_name == "excel":
            self.logger.info(
                "Connecting using : %s.connect(DRIVER={Microsoft Excel Driver (*.xls, "
                "*.xlsx, *.xlsm, *.xlsb)};DBQ=%s;ReadOnly=1;Extended Properties="
                '"Excel 8.0;HDR=YES";)',
                module_name,
                database,
            )
            self._dbconnection = dbmodule.connect(
                "DRIVER={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};"
                'DBQ=%s;ReadOnly=1;Extended Properties="Excel 8.0;HDR=YES";)'
                % (database),
                autocommit=True,
            )
        elif module_name == "excelrw":
            self.logger.info(
                "Connecting using : %s.connect(DRIVER={Microsoft Excel Driver (*.xls,"
                "*.xlsx, *.xlsm, *.xlsb)};DBQ=%s;ReadOnly=0;Extended Properties="
                '"Excel 8.0;HDR=YES";)',
                module_name,
                database,
            )
            self._dbconnection = dbmodule.connect(
                "DRIVER={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};"
                'DBQ=%s;ReadOnly=0;Extended Properties="Excel 8.0;HDR=YES";)'
                % (database),
                autocommit=True,
            )
        elif module_name in ("ibm_db", "ibm_db_dbi"):
            port = port or 50000
            self.logger.info(
                "Connecting using : %s.connect(DATABASE=%s;HOSTNAME=%s;PORT=%s;"
                "PROTOCOL=TCPIP;UID=%s;PWD=%s;) ",
                module_name,
                database,
                host,
                port,
                username,
                password,
            )
            self._dbconnection = dbmodule.connect(
                "DATABASE=%s;HOSTNAME=%s;PORT=%s;PROTOCOL=TCPIP;UID=%s;PWD=%s;"
                % (database, host, port, username, password),
                "",
                "",
            )
        elif module_name == "cx_Oracle":
            port = port or 1521
            oracle_dsn = dbmodule.makedsn(host=host, port=port, service_name=database)
            self.logger.info(
                "Connecting using: %s.connect(user=%s, password=%s, dsn=%s) ",
                module_name,
                username,
                password,
                oracle_dsn,
            )
            self._dbconnection = dbmodule.connect(
                user=username, password=password, dsn=oracle_dsn
            )
        elif module_name == "teradata":
            port = port or 1025
            teradata_udaExec = dbmodule.UdaExec(
                appName="RobotFramework", version="1.0", logConsole=False
            )
            self.logger.info(
                "Connecting using : %s.connect(database=%s, user=%s, password=%s, "
                "host=%s, port=%s) ",
                module_name,
                database,
                username,
                password,
                host,
                port,
            )
            self._dbconnection = teradata_udaExec.connect(
                method="odbc",
                system=host,
                database=database,
                username=username,
                password=password,
                host=host,
                port=port,
            )
        else:
            self.logger.info(
                "Connecting using : %s.connect(database=%s, user=%s, password=%s, "
                "host=%s, port=%s) ",
                module_name,
                database,
                username,
                password,
                host,
                port,
            )
            self._dbconnection = dbmodule.connect(
                database=database,
                user=username,
                password=password,
                host=host,
                port=port,
            )

    def call_stored_procedure(self, name, params=None, sanstran=False):
        """Call stored procedure with name and params.

        :param name: procedure name
        :param params: parameters for the procedure as a list, defaults to None
        :param sanstran: run command without an explicit transaction commit or rollback,
         defaults to False

        Example:

        .. code-block:: robotframework

            @{params}     Create List   FirstParam   SecondParam   ThirdParam
            @{results}    Call Stored Procedure   mystpr  ${params}

        """
        params = params or []
        cur = None
        try:
            if self.db_api_module_name == "cx_Oracle":
                cur = self._dbconnection.cursor()
            else:
                cur = self._dbconnection.cursor(as_dict=False)
            PY3K = sys.version_info >= (3, 0)
            if not PY3K:
                procedure = name.encode("ascii", "ignore")
            cur.callproc(procedure, params)
            cur.nextset()
            retVal = list()
            for row in cur:
                retVal.append(row)
            if not sanstran:
                self._dbconnection.commit()
            return retVal
        finally:
            if cur:
                if not sanstran:
                    self._dbconnection.rollback()

    def description(self, table):
        """Get description of the SQL table

        :param table: name of the SQL table

        Example:

        .. code-block:: robotframework

            Connect To Database    pymysql  mydb  user  pass  127.0.0.1
            ${db_description}      Description  mytable

        """
        result = self.query("DESCRIBE %s" % table, as_table=True)
        return result.to_list()

    def disconnect_from_database(self):
        """Close connection to SQL database

        Example:

        .. code-block:: robotframework

            Connect To Database    pymysql  mydb  user  pass  127.0.0.1
            ${result}              Query   Select firstname, lastname FROM table
            Disconnect From Database

        """
        self._dbconnection.close()

    # pylint: disable=R0912
    def execute_sql_script(self, filename, sanstran=False):  # noqa: C901
        """Execute content of SQL script as SQL commands.

        :param filename: filepath to SQL script to execute
        :param sanstran: run command without an explicit transaction commit or rollback,
         defaults to False

        Example:

        .. code-block:: robotframework

            Execute SQL Script   script.sql

        """
        sql_script_file = open(filename)

        cur = None
        try:
            cur = self._dbconnection.cursor()
            sqlStatement = ""
            for line in sql_script_file:
                PY3K = sys.version_info >= (3, 0)
                if not PY3K:
                    # spName = spName.encode('ascii', 'ignore')
                    line = line.strip().decode("utf-8")
                if line.startswith("#") or line.startswith("--"):
                    continue

                sql_fragments = line.split(";")
                if len(sql_fragments) == 1:
                    sqlStatement += line + " "
                else:
                    for sqlFragment in sql_fragments:
                        sqlFragment = sqlFragment.strip()
                        if len(sqlFragment) == 0:
                            continue

                        sqlStatement += sqlFragment + " "

                        self.__execute_sql(cur, sqlStatement)
                        sqlStatement = ""

            sqlStatement = sqlStatement.strip()
            if len(sqlStatement) != 0:
                self.__execute_sql(cur, sqlStatement)

            if not sanstran:
                self._dbconnection.commit()
        finally:
            if cur:
                if not sanstran:
                    self._dbconnection.rollback()

    def query(self, statement, assertion=None, sanstran=False, as_table=True):
        """Make a SQL query.

        :param statement: SQL statement to execute
        :param assertion: assert on query result, row_count or columns.
         Works only for SELECT statements Defaults to None.
        :param sanstran: run command without an explicit transaction commit or rollback,
         defaults to False
        :param as_table: if result should be instance of ``Table``, defaults to `True`
         `False` means that return type would be `list`

        Example:

        .. code-block:: robotframework

            @{res}   Query  Select * FROM table  row_count > ${EXPECTED}
            @{res}   Query  Select * FROM table  'arvo' in columns
            @{res}   Query  Select * FROM table  columns == ['id', 'arvo']

        """
        rows = None
        columns = None
        result = None
        cursor = None

        try:
            cursor = self._dbconnection.cursor()
            self.logger.info("Executing : Query  |  %s ", statement)
            result = self.__execute_sql(cursor, statement)

            if statement.lower().startswith("select") or statement.lower().startswith(
                "describe"
            ):
                rows = cursor.fetchall()
                columns = [c[0] for c in cursor.description]
                # pylint: disable=unused-variable
                row_count = len(rows)  # noqa: F841
                if assertion:
                    available_locals = {
                        "row_count": row_count,
                        "columns": columns,
                        "result": result,
                    }
                    # pylint: disable=W0123
                    valid = eval(assertion, {"__builtins__": None}, available_locals)

                    if not valid:
                        raise AssertionError(
                            "Query assertion %s failed. Facts: %s"
                            % (assertion, available_locals)
                        )
                if as_table:
                    return Table(rows, columns)
                return rows
            else:
                if result is not None:
                    if not sanstran:
                        self._dbconnection.commit()
                if not sanstran:
                    self._dbconnection.commit()
        finally:
            if cursor:
                if not sanstran:
                    self._dbconnection.rollback()
        return result

    def __execute_sql(self, cursor, sqlStatement):
        return cursor.execute(sqlStatement)

    def set_auto_commit(self, autocommit=True):
        """Set database auto commit mode.

        :param autocommit: boolean value for auto commit, defaults to True

        Example:

        .. code-block:: robotframework

            Set Auto Commit             # auto commit is set on
            Set Auto Commit   False     # auto commit is turned off

        """
        self._dbconnection.autocommit = autocommit

    def get_rows(self, table, columns=None, conditions=None, as_table=True):
        """Get rows from table. Columns and conditions can be
        set to filter result.

        :param table: name of the SQL table
        :param columns: name of columns to return, defaults to `None`
         means that all columns are returned
        :param conditions: limiting result by WHERE clause, defaults to `None`
        :param as_table: if result should be instance of ``Table``, defaults to `True`
         `False` means that return type would be `list`

        Example:

        .. code-block:: robotframework

            @{res}   Get Rows  tablename  arvo
            @{res}   Get Rows  tablename  arvo  columns=id,name
            @{res}   Get Rows  tablename  columns=id  conditions=column1='newvalue'
            @{res}   Get Rows  tablename  conditions=column2='updatedvalue'

        """
        columns = columns or "*"
        where_cond = f" WHERE {conditions}" if conditions else ""
        return self.query(
            "SELECT %s FROM %s%s" % (columns, table, where_cond), as_table=as_table
        )

    def get_number_of_rows(self, table, conditions=None):
        """Get number of rows in a table. Conditions can be given
        as arguments for WHERE clause.

        :param table: name of the SQL table
        :param conditions: restrictions for selections, defaults to None

        Example:

        .. code-block:: robotframework

            ${count}   Get Number Of Rows  tablename
            ${count}   Get Number Of Rows  tablename  column1=5 and column2='x'

        """
        where_cond = f" WHERE {conditions}" if conditions else ""
        result = self.query(
            "SELECT COUNT(*) FROM %s%s" % (table, where_cond), as_table=False
        )
        return result[0][0]
