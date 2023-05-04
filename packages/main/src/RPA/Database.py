import importlib
import logging

from typing import Any, Dict, List, Optional, Tuple, Union

from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

from RPA.RobotLogListener import RobotLogListener
from RPA.Tables import Table

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser

try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


MYSQL_CONNECTORS = ["MySQLdb", "pymysql", "mysql.connector"]


class Configuration:
    """Class to handle configuration from config files
    and class init"""

    def __init__(self):
        self.configuration = {}
        self.module_name = None

    def parse_arguments(
        self,
        module_name,
        database,
        username,
        password,
        host,
        port,
        charset,
        config_file: str,
    ):
        config = ConfigParser.ConfigParser()
        config.read([config_file])

        self.configuration = {}
        if "default" in config.keys():
            for key in config["default"]:
                self.configuration[key] = config.get("default", key)
        self.module_name = module_name or (
            config.get("default", "module_name")
            if config.has_option("default", "module_name")
            else None
        )
        self.configuration["database"] = database or (
            config.get("default", "database")
            if config.has_option("default", "database")
            else None
        )
        self.configuration["username"] = username or (
            config.get("default", "username")
            if config.has_option("default", "username")
            else None
        )
        self.configuration["password"] = password or (
            config.get("default", "password")
            if config.has_option("default", "password")
            else None
        )
        self.configuration["host"] = host or (
            config.get("default", "host")
            if config.has_option("default", "host")
            else None
        )
        self.configuration["port"] = port or (
            int(config.get("default", "port"))
            if config.has_option("default", "port")
            else None
        )
        self.configuration["charset"] = charset or (
            config.get("default", "charset")
            if config.has_option("default", "charset")
            else None
        )
        return self.module_name, self.configuration

    def get(self, param, default=None):
        # Missing values are still present in configuration as nulls.
        value = self.configuration.get(param)
        return value if value is not None else default

    def set_val(self, param, value):
        self.configuration[param] = value

    def all_but_empty(self):
        new_dict = {}
        for key, value in dict(self.configuration).items():
            if value is not None:
                new_dict[key] = value
        return new_dict

    def set_default_port(self, port):
        if (
            "port" not in self.configuration.keys()
            or self.configuration["port"] is None
        ):
            self.configuration["port"] = int(port)

    def get_connection_parameters_as_string(self, conf=None):
        configuration = conf or self.configuration
        parameters = ",".join(
            "{}={}".format(str(k), str(v)) for k, v in configuration.items()
        )
        return "Connecting using : %s.connect(%s)" % (self.module_name, parameters)


class Database:
    """`Database` is a library for handling different database operations.

    All database operations are supported. Keywords `Query` and `Get Rows`
    return values by default in `RPA.Table` format.

    Library is compatible with any Database API Specification 2.0 module.

    **Workaround for inserting large JSON data for Call Stored Procedure**

    Workaround is to use instead `Query` keyword. At the moment there is
    no known fix for the `Call Stored Procedure` keyword as it fails if
    JSON string is more than 8000 characters long.

    **Robot Framework**

    .. code-block:: robotframework

        ${data}=    Load JSON from file    random_data.json
        ${json}=    Convert JSON to String    ${data}
        # Single quotes around ${json} string are necessary
        Query    exec InsertJsonDataToSampleTable '${json}'

    References:

    - Database API Specification 2.0 - http://www.python.org/dev/peps/pep-0249/
    - Lists of DB API 2.0 - http://wiki.python.org/moin/DatabaseInterfaces
    - Python Database Programming - http://wiki.python.org/moin/DatabaseProgramming/

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library         RPA.Database

        *** Tasks ***
        Get Orders From Database
            Connect To Database  pymysql  tester  user  password  127.0.0.1
            @{orders}            Query    Select * FROM incoming_orders
            FOR   ${order}  IN  @{orders}
                Handle Order  ${order}
            END

    **Python**

    .. code-block:: python

        from RPA.Database import Database
        from RPA.Robocorp.Vault import FileSecrets

        filesecrets = FileSecrets("secrets.json")
        secrets = filesecrets.get_secret("databasesecrets")

        db = Database()
        db.connect_to_database('pymysql',
                            secrets["DATABASE"],
                            secrets["USERNAME"],
                            secrets["PASSWORD"],
                            '127.0.0.1'
                            )
        orders = db.query("SELECT * FROM incoming_orders")
        for order in orders:
            print(order)
    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._dbconnection = None
        self.db_api_module_name = None
        self.config = Configuration()
        listener = RobotLogListener()
        listener.register_protected_keywords(["connect_to_database"])

    # pylint: disable=R0915, too-many-branches
    def connect_to_database(  # noqa: C901
        self,
        module_name: Optional[str] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        charset: Optional[str] = None,
        config_file: Optional[str] = "db.cfg",
        autocommit: Optional[bool] = False,
    ) -> None:
        """Connect to database using DB API 2.0 module.

        **Note.** The SSL support had been added for `mysql`
        module in `rpaframework==17.7.0`. The extra configuration
        parameters can be given via configuration file. Extra
        parameters are:

        - ssl_ca
        - ssl_cert
        - ssl_key
        - client_flags

        Example configuration file:

        .. code-block:: ini

            [default]
            host=hostname.mysql.database.azure.com
            port=3306
            username=username@hostname
            database=databasename
            client_flags=SSL,FOUND_ROWS
            ssl_ca=DigiCertGlobalRootG2.crt.pem

        :param module_name: database module to use
        :param database: name of the database
        :param username: of the user accessing the database
        :param password: of the user accessing the database
        :param host: SQL server address
        :param port: SQL server port
        :param charset: for example, "utf-8", defaults to None
        :param config_file: location of configuration file, defaults to "db.cfg"
        :param autocommit: set autocommit value for connect

        Example:

        .. code-block:: robotframework

            Connect To Database  pymysql  database  username  password  host  port
            Connect To Database  ${CURDIR}${/}resources${/}dbconfig.cfg

            ${secrets}=    Get Secret    azuredb
            Connect To Database
            ...    mysql.connector
            ...    password=${secrets}[password]
            ...    config_file=${CURDIR}${/}azure.cfg

        """
        # TODO. take autocommit into use for all database modules
        self.config.parse_arguments(
            module_name, database, username, password, host, port, charset, config_file
        )
        if self.config.module_name in ("excel", "excelrw"):
            self.db_api_module_name = "pyodbc"
            dbmodule = importlib.import_module("pyodbc")
        else:
            self.db_api_module_name = self.config.module_name
            dbmodule = importlib.import_module(self.config.module_name)
        if module_name in MYSQL_CONNECTORS:
            self.config.set_default_port(3306)
            parameters = {
                "db": self.config.get("database"),
                "user": self.config.get("username"),
                "passwd": self.config.get("password"),
                "host": self.config.get("host"),
                "port": self.config.get("port"),
            }
            self._add_to_parameters_íf_not_none(parameters, "charset")
            self._add_to_parameters_íf_not_none(parameters, "ssl_ca")
            self._add_to_parameters_íf_not_none(parameters, "ssl_cert")
            self._add_to_parameters_íf_not_none(parameters, "ssl_key")
            self._set_mysql_client_flags(module_name, parameters)
            self._dbconnection = dbmodule.connect(**parameters)
        elif module_name.startswith("psycopg"):
            self.config.set_default_port(5432)
            self._dbconnection = dbmodule.connect(
                database=self.config.get("database"),
                user=self.config.get("username"),
                password=self.config.get("password"),
                host=self.config.get("host"),
                port=self.config.get("port"),
            )
            if autocommit:
                self._dbconnection.autocommit = True
        elif module_name in ("pyodbc", "pypyodbc"):
            self.config.set_default_port(1433)
            server = self.config.get("host", "")
            if server:
                server += f",{self.config.get('port')}"
            db = self.config.get("database", "")
            usr = self.config.get("username", "")
            pwd = self.config.get("password", "")
            self.config.set_val(
                "connect_string",
                f"DRIVER={{SQL Server}};SERVER={server};DATABASE={db};"
                f"UID={usr};PWD={pwd};",
            )
            self._dbconnection = dbmodule.connect(self.config.get("connect_string"))
        elif module_name == "excel":
            self.config.set_val(
                "connect_string",
                "DRIVER={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};"
                'DBQ=%s;ReadOnly=1;Extended Properties="Excel 8.0;HDR=YES";)'
                % self.config.get("database"),
            )
            self._dbconnection = dbmodule.connect(
                self.config.get("connect_string"),
                autocommit=True,
            )
        elif module_name == "excelrw":
            self.config.set_val(
                "connect_string",
                "DRIVER={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};"
                'DBQ=%s;ReadOnly=0;Extended Properties="Excel 8.0;HDR=YES";)'
                % self.config.get("database"),
            )
            self._dbconnection = dbmodule.connect(
                self.config.get("connect_string"),
                autocommit=True,
            )
        elif module_name in ("ibm_db", "ibm_db_dbi"):
            self.config.set_default_port(50000)
            self.config.set_val(
                "connect_string",
                "DATABASE=%s;HOSTNAME=%s;PORT=%s;PROTOCOL=TCPIP;UID=%s;PWD=%s;"
                % (
                    self.config.get("database"),
                    self.config.get("host"),
                    self.config.get("port"),
                    self.config.get("username"),
                    self.config.get("password"),
                ),
            )
            self._dbconnection = dbmodule.connect(
                self.config.get("connect_string"),
                "",
                "",
            )
        elif module_name in ("cx_Oracle", "oracledb"):
            self.config.set_default_port(1521)
            oracle_dsn = dbmodule.makedsn(
                host=self.config.get("host"),
                port=self.config.get("port"),
                service_name=self.config.get("database"),
            )
            self.config.set_val("oracle_dsn", oracle_dsn)
            self._dbconnection = dbmodule.connect(
                user=self.config.get("username"),
                password=self.config.get("password"),
                dsn=self.config.get("oracle_dsn"),
            )
        elif module_name == "teradata":
            self.config.set_default_port(1025)
            teradata_udaExec = dbmodule.UdaExec(
                appName="RobotFramework", version="1.0", logConsole=False
            )
            self._dbconnection = teradata_udaExec.connect(
                method="odbc",
                system=self.config.get("host"),
                database=self.config.get("database"),
                username=self.config.get("username"),
                password=self.config.get("password"),
                host=self.config.get("host"),
                port=self.config.get("port"),
            )
        elif module_name == "pymssql":
            self.config.set_default_port(1433)
            self._dbconnection = dbmodule.connect(
                server=self.config.get("host"),
                user=self.config.get("username"),
                password=self.config.get("password"),
                database=self.config.get("database"),
                port=self.config.get("port"),
                host=self.config.get("host", "."),
                autocommit=autocommit,
            )
        else:
            conf = self.config.all_but_empty()
            self._dbconnection = dbmodule.connect(**conf)
            if module_name == "sqlite3":
                self._dbconnection.isolation_level = None if autocommit else "IMMEDIATE"

    def _add_to_parameters_íf_not_none(self, parameters, config_key):
        config_value = self.config.get(config_key)
        if config_value:
            parameters[config_key] = config_value

    def _call_stored_procedure(self, name, params):
        modules_without_as_dict = MYSQL_CONNECTORS + [
            "cx_Oracle",
            "oracledb",
            "psycopg2",
        ]
        if self.db_api_module_name in modules_without_as_dict:
            cur = self._dbconnection.cursor()
        else:
            cur = self._dbconnection.cursor(as_dict=False)
        cur.callproc(name, params)
        return cur

    @staticmethod
    def _get_result_set_rows(cur):
        _rows = []
        # Get column names
        _columns = [column[0] for column in (cur.description or [])]
        for row in cur:
            _rows.append(row)
        return _rows, _columns

    def call_stored_procedure(
        self,
        name: str,
        params: Optional[List[str]] = None,
        sanstran: Optional[bool] = False,
        as_table: Optional[bool] = True,
        multiple: Optional[bool] = False,
    ) -> Union[Table, List[str]]:
        """Call stored procedure with name and params.

        :param name: procedure name
        :param params: parameters for the procedure as a list, defaults to None
        :param sanstran: Run the query without an implicit transaction commit or
            rollback if such additional action was detected. (turned off by default)
        :param as_table: If the result should be an instance of `Table`, otherwise a
            `list` will be returned. (defaults to `True`)
        :param multiple: Return results for one result set (default `False`) or multiple
            results from all result sets (set this parameter to `True`)
        :returns: list of results

        Example:

        .. code-block:: robotframework

            @{params}     Create List   FirstParam   SecondParam   ThirdParam
            @{results}    Call Stored Procedure   mystpr  ${params}

        """
        params = params or []
        cur = None
        rows = []
        columns = []
        result = []

        try:
            cur = self._call_stored_procedure(name, params)
            more_results = True
            while more_results is not None:
                _rows, _columns = self._get_result_set_rows(cur)
                if multiple:
                    if as_table:
                        result.append(Table(_rows, _columns))
                    else:
                        rows.append(_rows)
                        columns.append(_columns)
                else:
                    rows = _rows
                    columns = _columns
                    break
                more_results = cur.nextset()
        except Exception as exc:
            # Implicitly rollback when error occurs.
            self.logger.error(exc)
            if cur and not sanstran:
                self._dbconnection.rollback()
            raise
        else:
            if not sanstran:
                self._dbconnection.commit()
            if as_table and len(result) > 0:
                pass
            elif as_table:
                result = Table(rows, columns)
            else:
                result = rows
            return result

    def description(self, table: str) -> list:
        """Get description of the SQL table

        :param table: name of the SQL table
        :returns: database descripton as a list

        Example:

        .. code-block:: robotframework

            Connect To Database    pymysql  mydb  user  pass  127.0.0.1
            ${db_description}      Description  mytable

        """
        try:
            result = self.query("DESCRIBE %s" % table, as_table=True)
        except Exception as e:
            raise AssertionError(
                "Operation not supported for '%s' type database"
                % self.db_api_module_name
            ) from e
        return result.to_list()

    def disconnect_from_database(self) -> None:
        """Close connection to SQL database

        Example:

        .. code-block:: robotframework

            Connect To Database    pymysql  mydb  user  pass  127.0.0.1
            ${result}              Query   Select firstname, lastname FROM table
            Disconnect From Database

        """
        if self._dbconnection:
            self._dbconnection.close()

    # pylint: disable=R0912
    def execute_sql_script(  # noqa: C901
        self,
        filename: str,
        sanstran: Optional[bool] = False,
        encoding: Optional[str] = "utf-8",
    ) -> None:  # noqa: C901
        """Execute content of SQL script as SQL commands.

        :param filename: filepath to SQL script to execute
        :param sanstran: Run the query without an implicit transaction commit or
            rollback if such additional action was detected. (turned off by default)
        :param encoding: character encoding of file (utf-8 by default)

        Example:

        .. code-block:: robotframework

            Execute SQL Script   script.sql

        """
        with open(filename, encoding=encoding) as script_file:
            sql_script = script_file.readlines()

        cur = None
        try:
            cur = self._dbconnection.cursor()
            sqlStatement = ""
            for line in sql_script:
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
        except Exception as exc:
            # Implicitly rollback when error occurs.
            self.logger.error(exc)
            if cur and not sanstran:
                self._dbconnection.rollback()
            raise
        else:
            if not sanstran:
                self._dbconnection.commit()

    def query(
        self,
        statement: str,
        assertion: Optional[str] = None,
        sanstran: Optional[bool] = False,
        as_table: Optional[bool] = True,
        returning: Optional[bool] = None,
        data: Union[Dict, Tuple, None] = None,
    ) -> Union[List, Dict, Table, Any]:
        """Execute a SQL query and optionally return the execution result.

        Security Warning: In order to safely include untrusted data in SQL queries
        it is advisable to use parameterized queries. For more information about
        formatting for specific databases, please see https://bobby-tables.com/python

        :param statement: SQL statement to execute.
        :param assertion: Assert on query result, row_count or columns.
            Works only for `SELECT` statements. (defaults to `None`)
        :param sanstran: Run the query without an implicit transaction commit or
            rollback if such additional action was detected and this is set to `True`.
            (turned off by default, meaning that *commit* is performed on successful
            queries and *rollback* on failing ones automatically)
        :param as_table: If the result should be an instance of `Table`, otherwise a
            `list` will be returned. (defaults to `True`)
        :param returning: Set this to `True` if you want to have rows explicitly
            returned (instead of the query result), `False` otherwise. (by default a
            heuristic detects if it should return or not)
        :param data: The data to use if the SQL statement is parameterized
        :returns: Fetched rows when `returning` is `True` or if the heuristic decides
            that the statement should return (raw rows or as `Table` if `as_table` is
            `True`), otherwise the object produced by the execution is returned.

        **Examples**

        **Robot Framework**

        .. code-block:: robotframework

            *** Settings ***
            Library    RPA.Database

            *** Tasks ***
            Select Values From Table
                @{rows} =    Query   SELECT id,value FROM table
                FOR  ${row}  IN  @{rows}
                    Log   ${row}
                END
                @{res} =    Query   Select * FROM table   row_count > ${EXPECTED}
                @{res} =    Query   Select * FROM table   'value' in columns
                @{res} =    Query   Select * FROM table   columns == ['id', 'value']
                @{res} =    Query   Select * FROM table WHERE value = ?  data=("${d}", )
                # Calling Stored Procedure with Query keyword requires that parameter
                # 'returning' is set to 'True'
                @{res} =    Query   Exec stored_procedure  returning=True

        **Python**

        .. code-block:: python

            from RPA.Database import Database

            lib = Database()

            def insert_and_return_names():
                lib.connect_to_database("sqlite3", "sqlite.db")
                lib.query("DROP TABLE IF EXISTS orders;")
                lib.query("CREATE TABLE orders(id INTEGER PRIMARY KEY, name TEXT);")
                data1 = "my-1st-order"
                data2 = "my-2nd-order"
                lib.query(
                    'INSERT INTO orders(id, name) VALUES(1, ?), (2, ?);',
                    data=(data1, data2)
                )
                rows = lib.query(
                    'SELECT * FROM orders'
                )
                print([row["name"] for row in rows])  # ['my-1st-order', 'my-2nd-order']
        """
        cursor = None
        try:
            self.logger.info("Executing query: %s", statement)
            cursor = self._dbconnection.cursor()
            result = self.__execute_sql(cursor, statement, data)
            should_return = (returning is True) or (
                returning is None and self._is_returnable_statement(statement)
            )
            if should_return:
                rows = [tuple(row) for row in cursor.fetchall()]
                columns = [col[0] for col in (cursor.description or [])]
                self._result_assertion(rows, columns, assertion)
                if as_table:
                    result = Table(rows, columns)
                else:
                    result = rows
        except Exception as exc:
            # Implicitly rollback when error occurs.
            self.logger.error(exc)
            if cursor and not sanstran:
                self._dbconnection.rollback()
            raise
        else:
            if not sanstran:
                self._dbconnection.commit()
            return result

    def _is_returnable_statement(self, statement: str) -> bool:
        lower_parts = statement.lower().split()

        starts_with = lower_parts[0]
        if starts_with in ["select", "describe", "show", "explain"]:
            return True

        if "returning" in lower_parts:
            return True

        return False

    @staticmethod
    def _result_assertion(rows: List[Tuple[Any]], columns: List[str], assertion: str):
        if not assertion:
            return

        # pylint: disable=unused-variable
        row_count = len(rows)  # noqa: F841
        available_locals = {
            "row_count": row_count,
            "columns": columns,
        }
        # pylint: disable=W0123
        valid = eval(assertion, {"__builtins__": None}, available_locals)

        if not valid:
            raise AssertionError(
                "Query assertion %s failed. Facts: %s" % (assertion, available_locals)
            )

    def __execute_sql(
        self,
        cursor,
        sqlStatement,
        data: Union[Dict, Tuple, None] = None,
    ):
        if data is None:
            return cursor.execute(sqlStatement)
        return cursor.execute(sqlStatement, data)

    def set_auto_commit(self, autocommit: bool = True) -> None:
        """Set database auto commit mode.

        :param autocommit: boolean value for auto commit, defaults to True

        Example:

        .. code-block:: robotframework

            Set Auto Commit             # auto commit is set on
            Set Auto Commit   False     # auto commit is turned off

        """
        self._dbconnection.autocommit = autocommit

    def get_rows(
        self,
        table,
        columns: Optional[str] = None,
        conditions: Optional[str] = None,
        as_table: Optional[bool] = True,
    ) -> Union[List, Dict, Table, Any]:
        """Get rows from table. Columns and conditions can be
        set to filter result.

        :param table: name of the SQL table
        :param columns: name of columns to return, defaults to `None`
         means that all columns are returned
        :param conditions: limiting result by WHERE clause, defaults to `None`
        :param as_table: if result should be instance of ``Table``, defaults to `True`
         `False` means that return type would be `list`
        :returns: table or list based on param as_table arguement

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

    def get_number_of_rows(self, table: str, conditions: Optional[str] = None) -> int:
        """Get number of rows in a table. Conditions can be given
        as arguments for WHERE clause.

        :param table: name of the SQL table
        :param conditions: restrictions for selections, defaults to None
        :returns: number or rows

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

    def _set_mysql_client_flags(self, module_name, parameters):
        client_flags = self.config.get("client_flags")
        if module_name == "MySQLdb":
            raise NotImplementedError(
                "Setting client_flags for MySQLdb module is not supported"
            )
        if client_flags:
            flag_attributes_by_module = {
                "pymysql": {"property": "CLIENT", "param": "client_flag"},
                "mysql.connector": {
                    "property": "ClientFlag",
                    "param": "client_flags",
                },
            }
            try:
                flag_property = flag_attributes_by_module[module_name]["property"]
                connection_param = flag_attributes_by_module[module_name]["param"]
                constants = importlib.import_module(f"{module_name}.constants")
                client_flag_obj = getattr(constants, flag_property)
                flags_to_set = []
                for flag in client_flags.split(","):
                    try:
                        flags_to_set.append(getattr(client_flag_obj, flag))
                    except AttributeError:
                        self.logger.warning(
                            f"Could not set a client flag '{flag}', "
                            f"'{flag_property}' "
                            f"property for module '{module_name}'"
                        )

                if flags_to_set:
                    # pymysql supports only 1 value for 'client_flag'
                    # taking 1st from the list
                    parameters[connection_param] = (
                        int(flags_to_set[0])
                        if module_name in ["pymysql"]
                        else flags_to_set
                    )
            except Exception as err:
                self.logger.error(str(err))
                # noqa: E501
                raise AttributeError(
                    f"Could not set client flags '{flag_property}' "
                    f"property for module '{module_name}'"
                ) from err
