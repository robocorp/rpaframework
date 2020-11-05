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
    """Library for accessing Netsuite."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "ROBOT"

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
        """Connect to Netsuite with key/secret/token credentials

        Arguments are not logged into Robot Framework log.

        The arguments can also be supplied through environment variables:

        | = Variable =           | = Argument =    |
        | ``NS_ACCOUNT``         | account         |
        | ``NS_CONSUMER_KEY``    | consumer_key    |
        | ``NS_CONSUMER_SECRET`` | consumer_secret |
        | ``NS_TOKEN_KEY``       | token_key       |
        | ``NS_TOKEN_SECRET``    | token_secret    |
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
        """Login to Netsuite with email/password credentials.

        Arguments are not logged into Robot Framework log.

        The arguments can also be supplied through environment variables:

        | = Variable =    | = Argument = |
        | ``NS_ACCOUNT``  | account      |
        | ``NS_EMAIL``    | email        |
        | ``NS_PASSWORD`` | password     |
        | ``NS_ROLE``     | role         |
        | ``NS_APPID``    | appid        |
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
        """Get all records of given type, with given internalId and/or externalId.

        Both ``internal_id`` and ``external_id`` are optional.
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
        """Get all records of given type."""
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
        """Search Netsuite for given value from a type.

        Default default search operator is `contains`.

        Returns a paginated search object.
        Optionally the amount of results per page can be adjusted with
        ``page_size``.
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
        """Search Netsuite for type results.

        Returns a paginated search object.
        Optionally the amount of results per page can be adjusted with
        ``page_size``.
        """
        paginated_search = PaginatedSearch(
            client=self.client, type_name=type_name, pageSize=page_size
        )
        return paginated_search

    @ns_instance_required
    def get_accounts(self, count: int = 100, account_type: str = None) -> list:
        """Get Accounts of any type, or limited to specified type.

        Results are limited to the given ``count``.
        """
        all_accounts = list(
            itertools.islice(self.client.accounts.get_all_generator(), count)
        )
        if account_type is None:
            return all_accounts
        return [a for a in all_accounts if a["acctType"] == account_type]

    @ns_instance_required
    def get_currency(self, currency_id: str) -> object:
        """Get a Netsuite Currency by its ID."""
        return self.client.currencies.get(internalId=currency_id)

    @ns_instance_required
    def get_currencies(self) -> list:
        """Get all Netsuite Currencies."""
        return self.client.currencies.get_all()

    @ns_instance_required
    def get_locations(self) -> list:
        """Get all Netsuite Locations."""
        return self.client.locations.get_all()

    @ns_instance_required
    def get_departments(self) -> list:
        """Get all Netsuite Departments."""
        return self.client.departments.get_all()

    @ns_instance_required
    def get_classifications(self) -> list:
        """Get all Netsuite Classifications."""
        return self.client.classifications.get_all()

    @ns_instance_required
    def get_vendors(self, count: int = 10) -> list:
        """Get list of vendors, up to maximum of given ``count``."""
        return list(itertools.islice(self.client.vendors.get_all_generator(), count))

    @ns_instance_required
    def get_vendor_bills(self, count: int = 10) -> list:
        """Get list of vendor bills, up to maximum of given ``count``."""
        return list(
            itertools.islice(self.client.vendor_bills.get_all_generator(), count)
        )
