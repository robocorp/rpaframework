import importlib
import logging
import sys

from RPA.Tables import Table

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser


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
            if config.has_option("default", "host")
            else None
        )
        self.configuration["charset"] = charset or (
            config.get("default", "charset")
            if config.has_option("default", "charset")
            else None
        )
        return self.module_name, self.configuration

    def get(self, param, default=None):
        return (
            self.configuration[param] if param in self.configuration.keys() else default
        )

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
    """Library handling different database operations."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._dbconnection = None
        self.db_api_module_name = None
        self.config = Configuration()

    # pylint: disable=R0915
    def connect_to_database(  # noqa: C901
        self,
        module_name: str = None,
        database: str = None,
        username: str = None,
        password: str = None,
        host: str = None,
        port: str = None,
        charset: str = None,
        config_file: str = "db.cfg",
    ):
        """Connect to database using DB API 2.0 module.

        Example:
        | Connect To Database | pymysql | database | username | password | host | port |
        | Connect To Database | ${CURDIR}${/}resources${/}dbconfig.cfg |

        :param module_name (str): database module to use
        :param database (str): name of the database
        :param username (str): of the user accessing the database
        :param password (str): of the user accessing the database
        :param host (str): SQL server address
        :param port (str): SQL server port
        :param charset (str): for example, "utf-8", defaults to None
        :param config_file (str): location of configuration file, defaults to "db.cfg"
        """
        self.config.parse_arguments(
            module_name, database, username, password, host, port, charset, config_file
        )
        if self.config.module_name in ("excel", "excelrw"):
            self.db_api_module_name = "pyodbc"
            dbmodule = importlib.import_module("pyodbc")
        else:
            self.db_api_module_name = self.config.module_name
            dbmodule = importlib.import_module(self.config.module_name)
        if module_name in ["MySQLdb", "pymysql"]:
            self.config.set_default_port(3306)
            self.logger.info(self.config.get_connection_parameters_as_string())
            self._dbconnection = dbmodule.connect(
                db=self.config.get("database"),
                user=self.config.get("username"),
                passwd=self.config.get("password"),
                host=self.config.get("host"),
                port=self.config.get("port"),
                charset=self.config.get("charset"),
            )
        elif module_name == "psycopg2":
            self.config.set_default_port(5432)
            self.logger.info(self.config.get_connection_parameters_as_string())
            self._dbconnection = dbmodule.connect(
                database=self.config.get("database"),
                user=self.config.get("username"),
                password=self.config.get("password"),
                host=self.config.get("host"),
                port=self.config.get("port"),
            )
        elif module_name in ("pyodbc", "pypyodbc"):
            self.config.set_default_port(1433)
            self.config.set_val(
                "connect_string",
                "DRIVER={SQL Server};SERVER=%s,%s;DATABASE=%s;UID=%s;PWD=%s"
                % (
                    self.config.get("host"),
                    self.config.get("port"),
                    self.config.get("database"),
                    self.config.get("username"),
                    self.config.get("password"),
                ),
            )
            self.logger.info(self.config.get_connection_parameters_as_string())
            self._dbconnection = dbmodule.connect(self.config.get("connect_string"))
        elif module_name == "excel":
            self.config.set_val(
                "connect_string",
                "DRIVER={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};"
                'DBQ=%s;ReadOnly=1;Extended Properties="Excel 8.0;HDR=YES";)'
                % self.config.get("database"),
            )
            self.logger.info(self.config.get_connection_parameters_as_string())
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
            self.logger.info(self.config.get_connection_parameters_as_string())
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
                    self.config.get("usernamme"),
                    self.config.get("password"),
                ),
            )
            self.logger.info(self.config.get_connection_parameters_as_string())
            self._dbconnection = dbmodule.connect(
                self.config.get("connect_string"),
                "",
                "",
            )
        elif module_name == "cx_Oracle":
            self.config.set_default_port(1521)
            oracle_dsn = dbmodule.makedsn(
                host=self.config.get("host"),
                port=self.config.get("port"),
                service_name=self.config.get("database"),
            )
            self.config.set_val("oracle_dsn", oracle_dsn)
            self.logger.info(self.config.get_connection_parameters_as_string())
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
            self.logger.info(self.config.get_connection_parameters_as_string())
            self._dbconnection = teradata_udaExec.connect(
                method="odbc",
                system=self.config.get("host"),
                database=self.config.get("database"),
                username=self.config.get("username"),
                password=self.config.get("password"),
                host=self.config.get("host"),
                port=self.config.get("port"),
            )
        else:
            conf = self.config.all_but_empty()
            self.logger.info(self.config.get_connection_parameters_as_string(conf))
            self._dbconnection = dbmodule.connect(**conf)

    def call_stored_procedure(
        self, name: str, params: list = None, sanstran: bool = False
    ):
        """Call stored procedure with name and params.

        Example:
        | @{params} | Create List | FirstParam | SecondParam | ThirdParam |
        | @{results} | Call Stored Procedure | mystpr | ${params} |

        :param name (str): procedure name
        :param params (list): parameters for the procedure as a list, defaults to None
        :param sanstran (bool): run command without an explicit transaction commit or
        :param rollback, defaults to False
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

    def description(self, table: str):
        """Get description of the SQL table

        Example:
        | Connect To Database | pymysql | mydb | user | pass | 127.0.0.1 |
        | ${db_description} | Description | mytable |

        :param table (str): name of the SQL table
        """
        try:
            result = self.query("DESCRIBE %s" % table, as_table=True)
        except Exception as e:
            raise AssertionError(
                "Operation not supported for '%s' type database"
                % self.db_api_module_name
            ) from e
        return result.to_list()

    def disconnect_from_database(self):
        """Close connection to SQL database

        Example:
        | Connect To Database | pymysql | mydb | user | pass | 127.0.0.1 |
        | ${result} | Query | Select firstname, lastname FROM table |
        | Disconnect From Database |
        """
        if self._dbconnection:
            self._dbconnection.close()

    # pylint: disable=R0912
    def execute_sql_script(self, filename: str, sanstran: bool = False):  # noqa: C901
        """Execute content of SQL script as SQL commands.

        Example:
        | Execute SQL Script | script.sql |

        :param filename (str): filepath to SQL script to execute
        :param sanstran (bool): run command without an explicit transaction commit or
        :param rollback, defaults to False
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

    def query(
        self,
        statement: str,
        assertion: str = None,
        sanstran: bool = False,
        as_table: bool = True,
    ):
        """Make a SQL query.

        Example:
        | @{res} | Query | Select firstname, lastname FROM table |
        | FOR | ${row} | IN | @{RES} |
        | Log | ${row} |
        | END |
        | @{res} | Query | Select * FROM table | row_count > ${EXPECTED} |
        | @{res} | Query | Select * FROM table | 'arvo' in columns |
        | @{res} | Query | Select * FROM table | columns == ['id', 'arvo'] |

        :param statement (str): SQL statement to execute
        :param assertion (str): assert on query result, row_count or columns.
        :param Works only for SELECT statements Defaults to None.
        :param sanstran (bool): run command without an explicit transaction commit or
        :param rollback, defaults to False
        :param as_table (bool): if result should be instance of ``Table``, defaults to
        :param `True`. `False` means that return type would be `list`
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

    def set_auto_commit(self, autocommit: bool = True):
        """Set database auto commit mode.

        Example:
        | Set Auto Commit | # auto commit is set on |
        | Set Auto Commit | False | # auto commit is turned off |

        :param autocommit (bool): should there be auto commit, defaults to True
        """
        self._dbconnection.autocommit = autocommit

    def get_rows(
        self,
        table: str,
        columns: str = None,
        conditions: str = None,
        as_table: bool = True,
    ):
        """Get rows from table. Columns and conditions can be
        set to filter result.

        Example:
        | @{res} | Get Rows | tablename | arvo |
        | @{res} | Get Rows | tablename | arvo | columns=id,name |
        | @{res} | Get Rows | tablename | columns=id | conditions=column1='newvalue' |
        | @{res} | Get Rows | tablename | conditions=column2='updatedvalue' |

        :param table (str): name of the SQL table
        :param columns (str): name of columns to return, defaults to `None`
        :param means that all columns are returned
        :param conditions (str): limiting result by WHERE clause, defaults to `None`
        :param as_table (bool): if result should be instance of ``Table``, defaults to `True`
        :param `False` means that return type would be `list`
        """
        columns = columns or "*"
        where_cond = f" WHERE {conditions}" if conditions else ""
        return self.query(
            "SELECT %s FROM %s%s" % (columns, table, where_cond), as_table=as_table
        )

    def get_number_of_rows(self, table: str, conditions: str = None):
        """Get number of rows in a table. Conditions can be given
        as arguments for WHERE clause.

        Example:
        | ${count} | Get Number Of Rows | tablename |
        | ${count} | Get Number Of Rows | tablename | column1=5 and column2='x' |

        :param table (str): name of the SQL table
        :param conditions (str): restrictions for selections, defaults to None
        """
        where_cond = f" WHERE {conditions}" if conditions else ""
        result = self.query(
            "SELECT COUNT(*) FROM %s%s" % (table, where_cond), as_table=False
        )
        return result[0][0]
