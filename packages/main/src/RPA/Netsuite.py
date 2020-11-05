from functools import wraps
import itertools
import logging

from netsuitesdk import NetSuiteConnection
from netsuitesdk.internal.client import NetSuiteClient
from netsuitesdk.internal.utils import PaginatedSearch
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

from RPA.core.helpers import required_env
from RPA.RobotLogListener import RobotLogListener


try:
    BuiltIn().import_library("RPA.RobotLogListener")
except RobotNotRunningError:
    pass


def ns_instance_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if args[0].client is None:
            raise NetsuiteAuthenticationError("Authentication is not completed")
        return f(*args, **kwargs)

    return wrapper


class NetsuiteAuthenticationError(Exception):
    "Error when authenticated Netsuite instance does not exist."


class Netsuite:
    """`Netsuite` is a library for accessing Netsuite using NetSuite SOAP web service SuiteTalk.
    The library extends the `netsuitesdk library`_.

    More information available at `NetSuite SOAP webservice SuiteTalk`_.

    .. _netsuitesdk library:
        https://github.com/fylein/netsuite-sdk-py

    .. _NetSuite SOAP webservice SuiteTalk:
        http://www.netsuite.com/portal/platform/developer/suitetalk.shtml

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library     RPA.Netsuite
        Library     RPA.Excel.Files
        Library     RPA.Tables
        Task Setup  Authorize Netsuite

        *** Tasks ***
        Get data from Netsuite and Store into Excel files
            ${accounts}=        Get Accounts   account_type=_expense
            ${accounts}=        Create table    ${accounts}
            Create Workbook
            Append Rows To Worksheet  ${accounts}
            Save Workbook       netsuite_accounts.xlsx
            Close Workbook
            ${bills}=           Get Vendor Bills
            ${bills}=           Create table    ${bills}
            Create Workbook
            Append Rows To Worksheet  ${bills}
            Save Workbook       netsuite_bills.xlsx
            Close Workbook


        *** Keywords ***
        Authorize Netsuite
            ${secrets}=     Get Secret   netsuite
            Connect
            ...        account=${secrets}[ACCOUNT]
            ...        consumer_key=${secrets}[CONSUMER_KEY]
            ...        consumer_secret=${secrets}[CONSUMER_KEY]
            ...        token_key=${secrets}[CONSUMER_SECRET]
            ...        token_secret=${secrets}[TOKEN_KEY]

    **Python**

    .. code-block:: python

        from RPA.Netsuite import Netsuite

        ns = Netsuite()
        ns.connect()
        accounts = ns.get_accounts()
        currencies = ns.get_currencies()
    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self) -> None:
        self.client = None
        self.account = None
        self.logger = logging.getLogger(__name__)
        listener = RobotLogListener()
        listener.register_protected_keywords(
            ["RPA.Netsuite.connect", "RPA.Netsuite.login"]
        )

    def connect(
        self,
        account: str = None,
        consumer_key: str = None,
        consumer_secret: str = None,
        token_key: str = None,
        token_secret: str = None,
    ) -> None:
        """Connect to Netsuite with credentials from environment
        variables.

        Parameters are not logged into Robot Framework log.

        :param account: parameter or environment variable `NS_ACCOUNT`
        :param consumer_key:  parameter or environment variable `NS_CONSUMER_KEY`
        :param consumer_secret: parameter or environment variable `NS_CONSUMER_SECRET`
        :param token_key: parameter or environment variable `NS_TOKEN_KEY`
        :param token_secret: parameter or environment variable `NS_TOKEN_SECRET`
        """
        if account is None:
            self.account = required_env("NS_ACCOUNT")
        else:
            self.account = account

        NS_CONSUMER_KEY = required_env("NS_CONSUMER_KEY", consumer_key)
        NS_CONSUMER_SECRET = required_env("NS_CONSUMER_SECRET", consumer_secret)
        NS_TOKEN_KEY = required_env("NS_TOKEN_KEY", token_key)
        NS_TOKEN_SECRET = required_env("NS_TOKEN_SECRET", token_secret)

        self.client = NetSuiteConnection(
            account=self.account,
            consumer_key=NS_CONSUMER_KEY,
            consumer_secret=NS_CONSUMER_SECRET,
            token_key=NS_TOKEN_KEY,
            token_secret=NS_TOKEN_SECRET,
        )

    def login(
        self,
        account: str = None,
        email: str = None,
        password: str = None,
        role: str = None,
        appid: str = None,
    ) -> None:
        """Login to Netsuite with credentials from environment variables

        Parameters are not logged into Robot Framework log.

        :param account: parameter or environment variable `NS_ACCOUNT`
        :param email: parameter or environment variable `NS_EMAIL`
        :param password: parameter or environment variable `NS_PASSWORD`
        :param role: parameter or environment variable `NS_ROLE`
        :param appid: parameter or environment variable `NS_APPID`
        """
        if account is None:
            account = required_env("NS_ACCOUNT", self.account)
        if account is None:
            raise NetsuiteAuthenticationError("Authentication is not completed")
        NS_EMAIL = required_env("NS_EMAIL", email)
        NS_PASSWORD = required_env("NS_PASSWORD", password)
        NS_ROLE = required_env("NS_ROLE", role)
        NS_APPID = required_env("NS_APPID", appid)

        if self.client is None:
            self.client = NetSuiteClient(account=account)
        self.client.login(
            email=NS_EMAIL,
            password=NS_PASSWORD,
            role=NS_ROLE,
            application_id=NS_APPID,
        )

    @ns_instance_required
    def netsuite_get(
        self, record_type: str = None, internal_id: str = None, external_id: str = None
    ) -> list:
        """Get all records of given type and internalId and/or externalId.

        :param record_type: type of Netsuite record to get
        :param internal_id: internalId of the type, default None
        :param external_id: external_id of the type, default None
        :raises ValueError: if record_type is not given
        :return: records as a list or None
        """
        if record_type is None:
            raise ValueError("Parameter 'record_type' is required for kw: netsuite_get")
        if internal_id is None and external_id is None:
            raise ValueError(
                "Parameter 'internal_id' or 'external_id' "
                " is required for kw: netsuite_get"
            )
        kwargs = {"recordType": record_type}
        if internal_id is not None:
            kwargs["internalId"] = internal_id
        if external_id is not None:
            kwargs["externalId"] = external_id

        return self.client.get(**kwargs)

    @ns_instance_required
    def netsuite_get_all(self, record_type: str) -> list:
        """Get all records of given type.

        :param record_type: type of Netsuite record to get
        :raises ValueError: if record_type is not given
        :return: records as a list or None
        """
        if record_type is None:
            raise ValueError(
                "Parameter 'record_type' is required for kw: netsuite_get_all"
            )
        return self.client.getAll(recordType=record_type)

    def netsuite_search(
        self,
        type_name: str,
        search_value: str,
        operator: str = "contains",
        page_size: int = 5,
    ) -> PaginatedSearch:
        """Search Netsuite for value from a type. Default operator is
        `contains`.

        :param type_name: search target type name
        :param search_value: what to search for within type
        :param operator: name of the operation, defaults to "contains"
        :param page_size: result items within one page, defaults to 5
        :return: paginated search object
        """
        # pylint: disable=E1101
        record_type_search_field = self.client.SearchStringField(
            searchValue=search_value, operator=operator
        )
        basic_search = self.client.basic_search_factory(
            type_name, recordType=record_type_search_field
        )
        paginated_search = PaginatedSearch(
            client=self.client,
            type_name=type_name,
            basic_search=basic_search,
            pageSize=page_size,
        )
        return paginated_search

    def netsuite_search_all(
        self, type_name: str, page_size: int = 20
    ) -> PaginatedSearch:
        """Search Netsuite for a type results.

        :param type_name: search target type name
        :param page_size: result items within one page, defaults to 5
        :return: paginated search object
        """
        paginated_search = PaginatedSearch(
            client=self.client, type_name=type_name, pageSize=page_size
        )
        return paginated_search

    @ns_instance_required
    def get_accounts(self, count: int = 100, account_type: str = None) -> list:
        """Get Accounts of any type or specified type.

        :param count: number of Accounts to return, defaults to 100
        :param account_type: if None returns all account types, example. "_expense",
            defaults to None
        :return: accounts
        """
        all_accounts = list(
            itertools.islice(self.client.accounts.get_all_generator(), count)
        )
        if account_type is None:
            return all_accounts
        return [a for a in all_accounts if a["acctType"] == account_type]

    @ns_instance_required
    def get_currency(self, currency_id: str) -> object:
        """Get all a Netsuite Currency by its ID

        :param currency_id: ID of the currency to get
        :return: currency
        """
        return self.client.currencies.get(internalId=currency_id)

    @ns_instance_required
    def get_currencies(self) -> list:
        """Get all Netsuite Currencies

        :return: currencies
        """
        return self.client.currencies.get_all()

    @ns_instance_required
    def get_locations(self) -> list:
        """Get all Netsuite Locations

        :return: locations
        """
        return self.client.locations.get_all()

    @ns_instance_required
    def get_departments(self) -> list:
        """Get all Netsuite Departments

        :return: departments
        """
        return self.client.departments.get_all()

    @ns_instance_required
    def get_classifications(self) -> list:
        """Get all Netsuite Classifications

        :return: classifications
        """
        return self.client.classifications.get_all()

    @ns_instance_required
    def get_vendors(self, count: int = 10) -> list:
        """Get list of vendors

        :param count: number of vendors to return, defaults to 10
        :return: list of vendors
        """
        return list(itertools.islice(self.client.vendors.get_all_generator(), count))

    @ns_instance_required
    def get_vendor_bills(self, count: int = 10) -> list:
        """Get list of vendor bills

        :param count: number of vendor bills to return, defaults to 10
        :return: list of vendor bills
        """
        return list(
            itertools.islice(self.client.vendor_bills.get_all_generator(), count)
        )
