import logging
import math
import traceback
from typing import List, Dict, Optional, Tuple, Union
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from robot.api.deco import keyword, library

import requests

# pylint: disable=no-name-in-module
from hubspot import HubSpot as HubSpotApi
from hubspot.crm.objects.models import (
    PublicObjectSearchRequest as ObjectSearchRequest,
    FilterGroup,
    Filter,
    SimplePublicObject,
    SimplePublicObjectWithAssociations,
    BatchReadInputSimplePublicObjectId,
    SimplePublicObjectId,
)
from hubspot.crm.schemas.models import ObjectSchema
from hubspot.crm.pipelines.models import (
    Pipeline,
)
from hubspot.crm.associations.models import (
    BatchInputPublicObjectId,
    PublicObjectId,
    AssociatedId,
)
from hubspot.crm.owners.models import PublicOwner
from hubspot.crm.schemas.exceptions import ApiException as SchemaApiException
from hubspot.crm.pipelines.exceptions import ApiException as PipelineApiException


class HubSpotAuthenticationError(Exception):
    "Error when authenticated HubSpot instance does not exist."


class HubSpotObjectTypeError(Exception):
    "Error when the object type provided does not exist."


class HubSpotSearchParseError(Exception):
    "Error when the natural word search engine cannot parse the provided words."


class HubSpotNoPipelineError(Exception):
    "Error when there is no pipeline associated with an object."


class HubSpotRateLimitError(Exception):
    "Error when the API's rate limits are exceeded."


class HubSpotBatchResponseError(Exception):
    "Error when the entire batch response is nothing but errors."


class ExtendedFilter(Filter):
    """Extends the ``Filter`` class provided by ``hubspot-api-client``
    to include the following additional attributes supported by
    the REST API:

    * ``values``
    * ``high_value``

    It also overloads the implementation of ``value`` to support the
    existence of the other attributes.
    """

    openapi_types = {
        "value": "str",
        "values": "list",
        "high_value": "str",
        "property_name": "str",
        "operator": "str",
    }

    attribute_map = {
        "value": "value",
        "values": "values",
        "high_value": "highValue",
        "property_name": "propertyName",
        "operator": "operator",
    }

    def __init__(
        self,
        value=None,
        values=None,
        high_value=None,
        property_name=None,
        operator=None,
        local_vars_configuration=None,
    ):
        if value and values:
            raise ValueError(
                "You cannot construct a Filter with both ``value`` and ``values``."
            )
        super().__init__(value, property_name, operator, local_vars_configuration)
        self._values = None
        self._high_value = None
        if values is not None:
            self.values = values
        if high_value is not None:
            self.high_value = high_value

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, values):
        self._values = values
        if values is not None:
            self.value = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        if value is not None:
            self.values = None

    @property
    def high_value(self):
        return self._high_value

    @high_value.setter
    def high_value(self, high_value):
        self._high_value = high_value
        if high_value is not None:
            self.values = None
            if self._value is None:
                self._value = 0

    def __eq__(self, other):
        if not isinstance(other, ExtendedFilter):
            return False

        return self.to_dict() == other.to_dict()

    def __ne__(self, other):
        if not isinstance(other, ExtendedFilter):
            return True

        return self.to_dict() != other.to_dict()


class SearchLexer:
    """A class for analyzing a natural search list for ``RPA.Hubspot``"""

    def __init__(
        self, search_terms: List[str] = None, logger: logging.Logger = None
    ) -> None:
        self._search_terms = search_terms
        if not logger:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def _split(self, words: List, oper: str):
        self.logger.debug(f"Words to split on operator '{oper}': {words}")
        size = len(words)
        first_index_list = [i + 1 for i, v in enumerate(words) if v == oper]
        second_index_list = [i for i, v in enumerate(words) if v == oper]
        self.logger.debug(f"Index list is: {first_index_list}")
        split_result = [
            words[i:j]
            for i, j in zip(
                [0] + first_index_list,
                second_index_list + ([size] if second_index_list[-1] != size else []),
            )
        ]
        self.logger.debug(f"Split result: {split_result}")
        return split_result

    def _process_and(self, words: List):
        if words.count("AND") > 3:
            raise HubSpotSearchParseError(
                "No more than 3 logical 'AND' operators "
                + "can be used between each 'OR' operator."
            )
        search_filters = []
        if "AND" in words:
            word_filters = self._split(words, "AND")
            self.logger.debug(f"Found these groups of words as Filters: {word_filters}")
            for word_filter in word_filters:
                search_filters.append(self._process_filter(word_filter))
        else:
            self.logger.debug(f"Found this group of words as Filter: {words}")
            search_filters.append(self._process_filter(words))
        return search_filters

    def _process_filter(self, words: List):
        self.logger.debug(f"Attempting to turn {words} into Filter object.")
        if len(words) not in (2, 3):
            raise HubSpotSearchParseError(
                "The provided words cannot be parsed as a search object. "
                + f"The words {words} could not be parsed."
            )
        if words[1] in ("HAS_PROPERTY", "NOT_HAS_PROPERTY"):
            search_filter = ExtendedFilter(property_name=words[0], operator=words[1])
        elif words[1] in ("IN", "NOT_IN"):
            search_filter = ExtendedFilter(
                property_name=words[0], operator=words[1], values=words[2]
            )
        elif words[1] == "BETWEEN":
            search_filter = ExtendedFilter(
                property_name=words[0],
                operator=words[1],
                value=words[2][0],
                high_value=words[2][1],
            )
        else:
            search_filter = ExtendedFilter(
                property_name=words[0], operator=words[1], value=words[2]
            )
        self.logger.debug(f"Resulting Filter object: {search_filter}")
        return search_filter

    def create_search_object(self, words: List[str] = None):
        if not words:
            if self._search_terms:
                words = self._search_terms
            else:
                raise ValueError(
                    "Words must not be null if class was not "
                    + "initialized with search_terms."
                )

        if words.count("OR") > 3:
            raise HubSpotSearchParseError(
                "No more than 3 logical 'OR' operators can be used."
            )
        filter_groups = []
        if "OR" in words:
            word_groups = self._split(words, "OR")
            self.logger.debug(
                f"Found these groups of words as FilterGroups: {word_groups}"
            )
            for word_group in word_groups:
                filter_groups.append(FilterGroup(self._process_and(word_group)))
        else:
            self.logger.debug(f"Found this group of words as FilterGroup: {words}")
            filter_groups.append(FilterGroup(self._process_and(words)))
        return ObjectSearchRequest(filter_groups)


@library(scope="Global", doc_format="REST")
class Hubspot:
    """*Hubspot* is a library for accessing HubSpot using REST API. It
    extends `hubspot-api-client <https://pypi.org/project/hubspot-api-client/>`_.

    Current features of this library focus on retrieving CRM object data
    from HubSpot via API. For additional information, see
    `Understanding the CRM <https://developers.hubspot.com/docs/api/crm/understanding-the-crm>`_.

    Using Date Times When Searching
    ===============================

    When using date times with the Hubspot API, you must provide
    them as Unix-style epoch timestamps (with milliseconds), which can be obtained
    using the ``DateTime`` library's ``Convert Date`` with the
    argument ``result_format=epoch``. The resulting timestamp string
    will be a float, but the API only accepts integers, so you must
    multiply the resulting timestamp by 1,000 and then round  it to
    the nearest integar to include in API calls (i.e., the resulting
    integer sent to the API must have 13 digits as of March 18, 2022).

    Example usage:

    .. code-block:: robotframework

        *** Settings ***
        Library     DateTime
        Library     RPA.Hubspot
        Task Setup  Authorize Hubspot

        *** Tasks ***
        Search with date
            ${yesterday}=    Get current date    increment=-24h   result_format=epoch
            ${yesterday_hs_ts}=    Evaluate    round(${yesterday} * 1000)
            ${deals}=    Search for objects    DEALS
            ...    hs_lastmodifieddate    GTE    ${yesterday_hs_ts}

    .. code-block:: python

        from robot.libraries.DateTime import get_current_date, subtract_time_from_date
        from RPA.Hubspot import Hubspot
        from RPA.Robocorp.Vault import Vault

        secrets = Vault().get_secret("hubspot")

        hs = Hubspot(hubspot_apikey=secrets["api_key"])
        yesterday = round(
            subtract_time_from_date(get_current_date(), "24h", result_format="epoch") * 1000
        )
        deals = hs.search_for_objects("DEALS", "hs_lastmodifieddate", "GTE", yesterday)
        print(deals)

    Information Caching
    ===================

    This library loads custom object schemas and pipelines into memory
    the first time when keywords using them are called. These cached versions
    are recalled unless the ``use_cache`` is set to ``False``, where available.

    Custom Object Types
    ===================

    All keywords that request a parameter of ``object_type`` can accept
    custom object type names as long as they are properly configured in
    HubSpot. The system will lookup the custom object ID using the
    provided name against the configured name or one of the configured
    labels (e.g., "singular" and "plural" types of the name).

    HubSpot Object Reference
    ========================

    This section describes the types of objects returned by this Library
    and their associated attributes. These attributes can be accessed via
    dot-notation as described in the `Attribute Access`_ section below.

    Attribute Access
    ----------------

    Keywords return native Python Hubspot objects, rather than common Robot
    Framework types. These types have sets of defined attributes allowing
    for dot-notation access of object properties. Properties (e.g.,
    those configured in Hubspot settings for each object) will be
    accessible in a Python dictionary attached to the ``properties`` attribute
    of the returned object. See the `Attribute Definitions`_ section for
    details of that associated attributes for all types returned by this
    library.

    Example usage retrieving the ``city`` property of a *Company* object:

    .. code-block:: robotframework

        *** Settings ***
        Library         RPA.Hubspot
        Library         RPA.Robocorp.Vault

        Task Setup      Authorize Hubspot

        *** Variables ***
        ${ACCOUNT_NOKIA}    6818764598

        *** Tasks ***
        Obtain city information from Hubspot
            ${account}=    Get object    COMPANY    ${ACCOUNT_NOKIA}
            Log    The city for account number ${ACCOUNT_NOKIA} is ${account.properties}[city]

        *** Keywords ***
        Authorize Hubspot
            ${secrets}=    Get secret    hubspot
            Auth with api key    ${secrets}[API_KEY]

    .. code-block:: python

        from RPA.Hubspot import Hubspot
        from RPA.Robocorp.Vault import RobocorpVault

        vault = RobocorpVault()
        secrets = vault.get_secret("hubspot")

        hs = Hubspot(secrets["API_KEY"])
        nokia_account_id = "6818764598"
        account = hs.get_object("COMPANY", nokia_account_id)
        print(f"The city for account number {nokia_account_id} is {account.properties['city']}")

    Attribute Definitions
    ---------------------

    This library can return various types of objects, whose attributes
    are only accessible via dot-notation. The below reference describes
    the attributes available on these objects.

    SimplePublicObject
    ^^^^^^^^^^^^^^^^^^

    An object in HubSpot. The object itself does not describe what type
    it represents.

    *id* : ``str``
        The HubSpot ID of the object.

    *properties* : ``Dict[str, str]``
        A dictionary representing all returned properties associated
        to this object. Properties must be accessed as via standard
        dictionary subscription, e.g., ``properties["name"]``.

    *created_at* : ``datetime``
        The timestamp when this object was created in HubSpot.

    *updated_at* : ``datetime``
        The last modified timestamp for this object.

    *archived* : ``bool``
        Whether this object is archived.

    *archived_at* : ``datetime``
        The timestamp when this object was archived.

    SimplePublicObjectWithAssociations
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    An object in HubSpot including associations to other objects. The
    object itself does not describe what type it represents.

    *id* : ``str``
        The HubSpot ID of the object.

    *properties* : ``Dict[str, str]``
        A dictionary representing all returned properties associated
        to this object. Properties must be accessed as via standard
        dictionary subscription, e.g., ``properties["name"]``.

    *created_at* : ``datetime``
        The timestamp when this object was created in HubSpot.

    *updated_at* : ``datetime``
        The last modified timestamp for this object.

    *archived* : ``bool``
        Whether this object is archived.

    *archived_at* : ``datetime``
        The timestamp when this object was archived.

    *associations* : ``Dict[str, CollectionResponseAssociatedId]``
        A dictionary whose key will be the requested association type, e.g.,
        ``companies`` and associated value will be a container object
        with all the associations. See `CollectionResponseAssociatedId`_.

    AssociatedId
    ^^^^^^^^^^^^

    The ID of an associated object, as well as the type of association.

    *id* : ``str``
        The ID of the associated HubSpot object.

    *type* : ``str``
        The type of association, e.g., ``deals_to_companies``.

    CollectionResponseAssociatedId
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    A container object for a collection of `AssociatedId`_ objects returned
    by the API.

    *results* : ``List[AssociatedId]``
        The list of `AssociatedId`_ objects returned by the API.

    *paging* : ``Paging``
        Used by this library to assist with retreiving multi-page
        API responses.

    Pipeline
    ^^^^^^^^

    A pipeline represents the steps objects travel through within HubSpot.

    *id* : ``str``
        The HubSpot ID for the pipeline. All accounts start with one
        pipeline with the id ``default``.

    *label* : ``str``
        The human-readabel label for the pipeline.

    *stages* : ``List[PipelineStage]``
        A list of `PipelineStage`_ objects in the order the object would
        follow through the pipeline.

    *created_at* : ``datetime``
        The timestamp when this pipeline was created in HubSpot.

    *updated_at* : ``datetime``
        The last modified timestamp for this pipeline.

    *archived* : ``bool``
        Whether this pipeline is archived.

    *display_order* : ``int``
        The place in the list of pipelines where this pipeline is shown
        in the HubSpot UI.

    PipelineStage
    ^^^^^^^^^^^^^

    A pipeline stage is one of the various stages defined in a `Pipeline`_.

    *id* : ``str``
        The HubSpot ID of the stage.

    *label* : ``str``
        The human-readabel label for the stage.

    *metadata* : ``Dict[str, str]``
        A dictionary of additional data associated with ths stage, such
        as ``probability``.

    *created_at* : ``datetime``
        The timestamp when this stage was created in HubSpot.

    *updated_at* : ``datetime``
        The last modified timestamp for this stage.

    *archived* : ``bool``
        Whether this stage is archived.

    *archived_at* : ``datetime``
        The timestamp when this stage was archived.

    PublicOwner
    ^^^^^^^^^^^

    An owner in HubSpot. Owners of companies and deals are responsible
    for driving a sale to close or similar.

    *id* : ``str``
        The HubSpot ID of the owner.

    *email* : ``str``
        The owner's email address in HubSpot.

    *first_name* : ``str``
        The owner's first name.

    *last_name* : ``str``
        The owner's last name.

    *user_id* : ``int``
        The associated user ID if the owner is a HubSpot user.

    *created_at* : ``datetime``
        The timestamp when this owner was created in HubSpot.

    *updated_at* : ``datetime``
        The last modified timestamp for this owner.

    *archived* : ``bool``
        Whether this owner is archived.

    *teams* : ``List[PublicTeam]``
        A list of teams the owner is in. See `PublicTeam`_.

    PublicTeam
    ^^^^^^^^^^

    A team of owners in HubSpot

    *id* : ``str``
        The HubSpot ID of the Team.

    *name* : ``str``
        The Team's name.

    *membership* : ``str``
        One of ``PRIMARY``, ``SECONDARY``, or ``CHILD``.

    """  # noqa: E501

    BUILTIN_SINGULAR_MAP = {
        "contacts": "contact",
        "companies": "company",
        "deals": "deal",
        "feedback submissions": "feadback submission",
        "line items": "line item",
        "products": "product",
        "tickets": "ticket",
        "quotes": "quote",
        "contact": "contact",
        "company": "company",
        "deal": "deal",
        "feedback submission": "feadback submission",
        "line item": "line item",
        "product": "product",
        "ticket": "ticket",
        "quote": "quote",
    }
    BUILTIN_PLURAL_MAP = {
        "contact": "contacts",
        "company": "companies",
        "deal": "deals",
        "feedback submission": "feadback submissions",
        "line item": "line items",
        "product": "products",
        "ticket": "tickets",
        "quote": "quotes",
        "contacts": "contacts",
        "companies": "companies",
        "deals": "deals",
        "feedback submissions": "feadback submissions",
        "line items": "line items",
        "products": "products",
        "tickets": "tickets",
        "quotes": "quotes",
    }

    def __init__(
        self, hubspot_apikey: str = None, hubspot_access_token: str = None
    ) -> None:
        self.logger = logging.getLogger(__name__)
        if hubspot_apikey:
            self.hs = HubSpotApi(api_key=hubspot_apikey)
        elif hubspot_access_token:
            self.hs = HubSpotApi(access_token=hubspot_access_token)
        else:
            self.hs = None
        self._schemas = []
        self._singular_map = {}
        self._plural_map = {}
        self._pipelines = {}

    def _require_authentication(self) -> None:
        if self.hs is None:
            raise HubSpotAuthenticationError("Authentication was not completed.")

    def _require_token_authentication(self) -> None:
        if self.hs.access_token is None:
            raise HubSpotAuthenticationError(
                "This endpoint requires a private app authorization token to use."
            )

    # pylint: disable=no-self-argument
    def _is_rate_limit_error(error: Exception) -> bool:
        return getattr(error, "status", None) == 429

    # pylint: disable=no-self-argument,no-method-argument
    def _before_sleep_log():
        logger = logging.root
        return before_sleep_log(logger, logging.DEBUG)

    @property
    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=0.1),
        before_sleep=_before_sleep_log(),
    )
    def schemas(self) -> List[ObjectSchema]:
        self._require_authentication()
        if len(self._schemas) == 0:
            self.schemas = self.hs.crm.schemas.core_api.get_all()
        return self._schemas

    @schemas.setter
    def schemas(self, results):
        if hasattr(results, "results"):
            results = results.results
        if isinstance(results, list) and isinstance(results[0], ObjectSchema):
            self._schemas = results
        else:
            raise TypeError(
                "Invalid values for ``results``, must be list of ``ObjectSchema``."
            )

    def _get_custom_object_schema(self, name: str) -> Union[Dict, None]:
        self._require_authentication()
        for s in self.schemas:
            if (
                s.name == name.lower()
                or s.labels.singular.lower() == name.lower()
                or s.labels.plural.lower() == name.lower()
            ):
                return s
            else:
                return None

    def _get_custom_object_id(self, name: str) -> str:
        self._require_authentication()
        schema = self._get_custom_object_schema(self._validate_object_type(name))
        return schema.object_type_id if schema else name

    def _singularize_object(self, name: str) -> str:
        if len(self._singular_map) == 0:
            self._singular_map = self.BUILTIN_SINGULAR_MAP
            labels = [s.labels for s in self.schemas]
            self._singular_map.update(
                {lbl.plural.lower(): lbl.singular.lower() for lbl in labels}
            )
            self._singular_map.update(
                {lbl.singular.lower(): lbl.singular.lower() for lbl in labels}
            )
            self._singular_map.update(
                {s.object_type_id: s.object_type_id for s in self.schemas}
            )
        return self._singular_map[self._validate_object_type(name)]

    def _pluralize_object(self, name: str) -> str:
        if len(self._plural_map) == 0:
            self._plural_map = self.BUILTIN_PLURAL_MAP
            labels = [s.labels for s in self.schemas]
            self._plural_map.update(
                {lbl.singular.lower(): lbl.plural.lower() for lbl in labels}
            )
            self._plural_map.update(
                {lbl.plural.lower(): lbl.plural.lower() for lbl in labels}
            )
            self._plural_map.update(
                {s.object_type_id: s.object_type_id for s in self.schemas}
            )
        return self._plural_map[self._validate_object_type(name)]

    def _validate_object_type(self, name: str) -> str:
        """Validates the provided ``name`` against the built in list of
        object types and the list of custom object type schemas. Returns
        the validated custom object ID or name in lower case.
        Raises ``HubSpotObjectTypeError`` if ``name`` cannot be validated.
        """
        valid_names = list(self.BUILTIN_SINGULAR_MAP.keys())
        valid_names.extend([s.object_type_id for s in self.schemas])
        valid_names.extend([s.name for s in self.schemas])
        valid_names.extend([s.labels.plural.lower() for s in self.schemas])
        if name.lower() in valid_names:
            return name.lower()
        else:
            raise HubSpotObjectTypeError(
                f"Object type {name} does not exist. "
                + f"Current accepted names are:\n{valid_names}."
            )

    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=0.1),
        before_sleep=_before_sleep_log(),
    )
    def _get_next_search_page(
        self,
        object_type: str,
        search_object: ObjectSearchRequest,
        after: int = 0,
    ):
        self.logger.debug(f"Current cursor is: {after}")
        search_object.after = after
        page = self.hs.crm.objects.search_api.do_search(
            object_type, public_object_search_request=search_object
        )
        self.logger.debug(
            f"{len(page.results)} received out of {page.total}. "
            + f"Next cursor is {page.next.after}"
            if hasattr(page, "next")
            else ""
        )
        return page

    def _search_objects(
        self,
        object_type: str,
        search_object: ObjectSearchRequest,
        max_results: int = 1000,
    ) -> List[SimplePublicObject]:
        self._require_authentication()
        if max_results < 100:
            search_object.limit = max_results
        else:
            search_object.limit = 100
        self.logger.debug(f"Search to use is:\n{search_object}")
        results = []
        after = 0
        while len(results) < max_results or max_results <= 0:
            page = self._get_next_search_page(object_type, search_object, after)
            results.extend(page.results)
            if page.paging is None:
                break
            after = page.paging.next.after
        self.logger.debug(f"Total results found: {len(results)}")
        return results

    @keyword
    def auth_with_token(self, access_token: str) -> None:
        """Authorize to HubSpot with Private App access token. This
        keyword verifies the provided credentials by retrieving the
        custom object schema from the API.

        :param access_token: The access token created for the Private App
            in your HubSpot account.

        """
        if self.hs is None or getattr(self.hs, "access_token", "") != access_token:
            self.hs = HubSpotApi(access_token=access_token)
            try:
                self.schemas
            except SchemaApiException as e:
                if e.status == 401:
                    raise HubSpotAuthenticationError(
                        "Authentication was not successful."
                    ) from e
                else:
                    raise e
            self.logger.info("Authentication to Hubspot CRM API with token successful.")
        else:
            self.logger.info("Already authenticated with access token.")

    @keyword
    def auth_with_api_key(self, api_key: str) -> None:
        """Authorize to HubSpot with an account-wide API key. This
        keyword verifies the provided credentials by retrieving the
        custom object schema from the API.

        :param api_key: The API key for the account to autheniticate to.

        """
        if self.hs is None or getattr(self.hs, "api_key", "") != api_key:
            self.hs = HubSpotApi(api_key=api_key)
            try:
                self.schemas
            except SchemaApiException as e:
                if e.status == 401:
                    raise HubSpotAuthenticationError(
                        "Authentication was not successful."
                    ) from e
                else:
                    raise e
            self.logger.info(
                "Authentication to Hubspot CRM API with API key successful."
            )
        else:
            self.logger.info("Already authenticated with API key.")

    @keyword
    def search_for_objects(
        self,
        object_type: str,
        *natural_search,
        search: Optional[List[Dict]] = None,
        string_query: str = "",
        properties: Optional[Union[str, List[str]]] = None,
        max_results: int = 1000,
    ) -> List[SimplePublicObject]:
        """Returns a list of objects of the specified ``type`` based on the
        provided ``search`` criteria. The following types are supported:

        - COMPANIES
        - CONTACTS
        - DEALS
        - FEEDBACK SUBMISSIONS
        - PRODUCTS
        - TICKETS
        - LINE ITEMS
        - QUOTES
        - Custom objects, which can be provided as the name of the
          object or the custom object ID in Hubspot.

        Returns no more than ``max_results`` which defaults to 1,000 records.
        Provide 0 for all results.

        By default, search criteria can be passed as additional unlabeled
        arguments to the keyword. They must be provided in order:
        ``property_name``, ``operator``, ``value``. Boolean operators ``AND`` and
        ``OR`` can be used, but if both are used, groups of criteria combined
        with ``AND`` will be combined first, with each of those groups being
        combined with ``OR`` second. You can only define a maximum of three
        groups of filters combined with ``OR`` and each of those groups can
        have no more than three filters combined with ``AND``.

        You can use the following operators in your search:

        +---------------------+-------------------------------------------+
        | OPERATOR            | DESCRIPTION                               |
        +=====================+===========================================+
        | LT                  | Less than                                 |
        +---------------------+-------------------------------------------+
        | LTE                 | Less than or equal to                     |
        +---------------------+-------------------------------------------+
        | GT                  | Greater than                              |
        +---------------------+-------------------------------------------+
        | GTE                 | Greater than or equal to                  |
        +---------------------+-------------------------------------------+
        | EQ                  | Equal to                                  |
        +---------------------+-------------------------------------------+
        | NEQ                 | Not equal to                              |
        +---------------------+-------------------------------------------+
        | BETWEEN             | Within the specified range                |
        +---------------------+-------------------------------------------+
        | IN                  | Included within the specified list        |
        +---------------------+-------------------------------------------+
        | NOT_IN              | Not included within the specified list    |
        +---------------------+-------------------------------------------+
        | HAS_PROPERTY        | Has a value for the specified property.   |
        |                     | When using this operator, or its opposite |
        |                     | below, you cannot provide a value.        |
        +---------------------+-------------------------------------------+
        | NOT_HAS_PROPERTY    | Doesn't have a value for the specified    |
        |                     | property.                                 |
        +---------------------+-------------------------------------------+
        | CONTAINS_TOKEN      | Contains a token.                         |
        +---------------------+-------------------------------------------+
        | NOT_CONTAINS_TOKEN  | Doesn't contain a token.                  |
        +---------------------+-------------------------------------------+

        Example search:

        .. code-block:: robotframework

            *** Settings ***
            Library         RPA.Hubspot
            Library         RPA.Robocorp.Vault
            Task Setup      Authorize Hubspot

            *** Tasks ***
            Obtain contacts with search
                ${contacts}=    Search for objects    CONTACTS
                ...    firstname    EQ    Alice    AND    lastname    NEQ    Smith
                ...    OR    enum1    HAS_PROPERTY
                ${message}=    Catenate    These contacts will have the first name "Alice" but not the last name "Smith",
                ...    or they will have a value in the proeprty "enum1": ${contacts}
                Log    ${message}

            *** Keywords ***
            Authorize Hubspot
                ${secrets}=    Get secret    hubspot
                Auth with api key    ${secrets}[API_KEY]

        Object Searching
        ================

        Alternatively, search criteria can be passed as a list of
        dictionaries to the label-only parameter ``search``.

        To include multiple filter criteria, you can group filters within
        ``filterGroups``:

        - When multiple ``filters`` are present within a ``filterGroup``, they'll
          be combined using a logical AND operator.
        - When multiple ``filterGroups`` are included in the request body,
          they'll be combined using a logical OR operator.

        You can include a maximum of three filterGroups with up to three
        filters in each group.

        .. code-block:: python

            from RPA.Hubspot import Hubspot
            from RPA.Robocorp.Vault import RobocorpVault

            vault = RobocorpVault()
            secrets = vault.get_secret("hubspot")

            hs = Hubspot(secrets["API_KEY"])

            combination_search = [
                {
                    "filters": [
                        {
                            "propertyName": "firstname",
                            "operator": "EQ",
                            "value": "Alice",
                        },
                        {
                            "propertyName": "lastname",
                            "operator": "NEQ",
                            "value": "Smith",
                        },
                    ]
                },
                {"filters": [{"propertyName": "enum1", "operator": "HAS_PROPERTY"}]},
            ]
            contacts = hs.search_for_objects("CONTACTS", search=combination_search)
            print(
                "These contacts will have the first name 'Alice' but not the "
                + "last name 'Smith', or they will have a value in the "
                + f"property 'enum1': {contacts}"
            )

        ===============================
        Controlling Returned Properties
        ===============================

        You can retrieve additional properties for the objects by defining
        them with ``properties``. Properties must be provided as a single
        property as a string, or a list of properties as a list. If a
        requested property does not exist, it will be ignored.

        ==================
        Using Associations
        ==================

        Associated objects can be used as search criteria by using the
        pseudo-property ``associations.{object_type}``, where ``{object_type}``
        is a valid object type, such as ``contact``, but this is not
        supported when seaching custom objects.

        =======================
        Text-based Search Query
        =======================

        If you want to search all text-based fields with a simple string,
        it can be provided via the optional label-only parameter
        ``string_query``. This cannot be used at the same time with
        ``search_object`` or ``natural_search`` parameters.

        :param natural_search: all additional unlabeled parameters will
            be parsed as a natural language search.
        :param search: the search object to use as search criteria.
        :param string_query: a string query can be provided instead of a
            search object which is used as a text-based search in all default
            searchable properties in Hubspot.
        :param properties: a list of strings representing return properties
            to be included in the returned data.

        :return: A list of found HubSpot objects of type ``SimplePublicObject``.

        """  # noqa: E501
        self._require_authentication()

        if string_query:
            search_object = ObjectSearchRequest(query=string_query)
        elif natural_search:
            search_object = SearchLexer(
                natural_search, self.logger
            ).create_search_object()
        elif search:
            search_object = ObjectSearchRequest(
                [
                    FilterGroup(
                        [
                            Filter(f.get("value"), f["propertyName"], f["operator"])
                            for f in g["filters"]
                        ]
                    )
                    for g in search
                ]
            )
        else:
            search_object = ObjectSearchRequest()
        search_object.properties = (
            [properties] if isinstance(properties, str) else properties
        )
        return self._search_objects(
            self._pluralize_object(self._get_custom_object_id(object_type)),
            search_object,
            max_results=max_results,
        )

    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=0.1),
        before_sleep=_before_sleep_log(),
    )
    def _list_associations(
        self, object_type: str, object_id: str, to_object_type: str
    ) -> List[AssociatedId]:
        self._require_authentication()
        results = []
        after = None
        while True:
            page = self.hs.crm.objects.associations_api.get_all(
                self._validate_object_type(self._singularize_object(object_type)),
                object_id,
                self._validate_object_type(self._singularize_object(to_object_type)),
                after=after,
                limit=500,
            )
            results.extend(page.results)
            if page.paging is None:
                break
            after = page.paging.next.after
        return results

    def _batch_batch_requests(
        self, ids: List[str], max_batch_size: int = 100
    ) -> List[List[str]]:
        """Breaks batch inputs down to a max size for the API, Hubspot
        batch input maxes out at 100 by default.
        """
        output = []
        for i in range(math.ceil(len(ids) / max_batch_size)):
            bottom = i * max_batch_size
            top = (i + 1) * max_batch_size
            current_list = ids[bottom:top]
            output.append(current_list)
        return output

    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=0.1),
        before_sleep=_before_sleep_log(),
    )
    def _list_associations_by_batch(
        self, object_type: str, object_id: List[str], to_object_type: str
    ) -> Dict[str, List[AssociatedId]]:
        self._require_authentication()
        batched_ids = self._batch_batch_requests(object_id)
        collected_responses = {}
        for i, batch in enumerate(batched_ids):
            self.logger.debug(f"Executing batch index {i} of batch requests:\n{batch} ")
            batch_reader = BatchInputPublicObjectId(
                inputs=[PublicObjectId(o) for o in batch]
            )
            response = self.hs.crm.associations.batch_api.read(
                self._singularize_object(self._get_custom_object_id(object_type)),
                self._singularize_object(self._get_custom_object_id(to_object_type)),
                batch_input_public_object_id=batch_reader,
            )
            if getattr(response, "num_errors", None):
                if response.num_errors >= len(object_id):
                    raise HubSpotBatchResponseError(
                        "Batch API failed all items with the following "
                        + f"errors for batch index {i}:\n{response.errors}"
                    )
                elif response.num_errors > 0:
                    self.logger.warning(
                        f"Batch API returned some errors for batch index {i}:\n"
                        + str(response.errors)
                    )
            self.logger.debug(
                f"Full results received for batch index {i}:\n{response.results}"
            )
            # pylint: disable=protected-access
            collected_responses.update({o._from.id: o.to for o in response.results})

        return collected_responses

    @keyword
    def list_associations(
        self, object_type: str, object_id: Union[str, List[str]], to_object_type: str
    ) -> Union[List[AssociatedId], Dict[str, List[AssociatedId]]]:
        """List associations of an object by type, you must define the ``object_type``
        with its ``object_id``. You must also provide the associated objects with
        ``to_object_type``. The API will return a list of dictionaries with
        the associated object ``id`` and association ``type`` (e.g.,
        ``contact_to_company``).

        You may provide a list of object IDs, if you do, the return object is a
        dictionary where the keys are the requested IDs and the value associated
        to each key is a list of associated objects (like a single search).

        :param object_type: The type of object for the object ID
            provided, e.g. ``contact``.
        :param object_id: The HubSpot ID for the object of type ``object_type``.
            If you provide a list of object_ids, they will be searched via the
            batch read API.
        :param to_object_type: The type of object associations to return.

        :return: A list of dictionaries representing the associated objects.
            The associated objects are returned as ``AssociatedId`` objects.

        """

        self._require_authentication()
        if isinstance(object_id, list):
            return self._list_associations_by_batch(
                object_type, object_id, to_object_type
            )
        else:
            return self._list_associations(object_type, object_id, to_object_type)

    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=0.1),
        before_sleep=_before_sleep_log(),
    )
    def _get_object(
        self,
        object_type: str,
        object_id: str,
        id_property: Optional[str] = None,
        properties: Optional[Union[str, List[str]]] = None,
        associations: Optional[Union[str, List[str]]] = None,
    ) -> Union[SimplePublicObject, SimplePublicObjectWithAssociations]:
        self._require_authentication()

        return self.hs.crm.objects.basic_api.get_by_id(
            self._validate_object_type(object_type),
            object_id,
            properties=properties,
            associations=(
                [self._validate_object_type(obj) for obj in associations]
                if associations
                else None
            ),
            id_property=id_property,
        )

    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=0.1),
        before_sleep=_before_sleep_log(),
    )
    def _get_object_by_batch(
        self,
        object_type: str,
        object_id: List[str],
        id_property: Optional[str] = None,
        properties: Optional[Union[str, List[str]]] = None,
    ) -> List[SimplePublicObject]:
        self._require_authentication()
        batched_ids = self._batch_batch_requests(object_id)
        collected_responses = []
        for i, batch in enumerate(batched_ids):
            self.logger.debug(f"Executing batch index {i} of batch requests:\n{batch} ")
            batch_reader = BatchReadInputSimplePublicObjectId(
                properties=properties,
                id_property=id_property,
                inputs=[SimplePublicObjectId(o) for o in batch],
            )
            response = self.hs.crm.objects.batch_api.read(
                self._singularize_object(self._get_custom_object_id(object_type)),
                batch_read_input_simple_public_object_id=batch_reader,
            )
            if getattr(response, "num_errors", None):
                if response.num_errors >= len(object_id):
                    raise HubSpotBatchResponseError(
                        "Batch API failed all items with the following "
                        + f"errors for batch index {i}:\n{response.errors}"
                    )
                elif response.num_errors > 0:
                    self.logger.warning(
                        f"Batch API returned some errors for batch index {i}:\n"
                        + str(response.errors)
                    )
            self.logger.debug(
                f"Full results received for batch index {i}:\n{response.results}"
            )
            collected_responses.extend(response.results)

        return collected_responses

    @keyword
    def get_object(
        self,
        object_type: str,
        object_id: Union[str, List[str]],
        id_property: Optional[str] = None,
        properties: Optional[Union[str, List[str]]] = None,
        associations: Optional[Union[str, List[str]]] = None,
    ) -> Union[
        SimplePublicObject,
        SimplePublicObjectWithAssociations,
        List[SimplePublicObject],
    ]:
        """Reads objects of ``object_type`` from HubSpot with the
        provided ``object_id``. The objects can be found using an
        alternate ID by providing the name of that HubSpot property
        which contains the unique identifier to ``id_property``. The ``object_type``
        parameter automatically looks up custom object IDs based on the
        provided name. If a list of object IDs is provided, the batch
        API will be utilized, but in that case, ``associations`` cannot be
        returned.

        A list of property names can be provided to ``properties``
        and they will be included in the returned object. Nonexistent
        properties are ignored.

        A list of object types can be provided to ``associations`` and all
        object IDs associated to the returned object of that type will
        be returned as well. Object types passed to this parameter are
        also validated against built-in objects and custom object schemas.

        :param object_type: The object type to be returned and that has
            the ID indicated.
        :param object_id: The ID of the object to be returned.
        :param id_property: (Optional) Can be used to allow the API to
            search the object database using an alternate property as the
            unique ID.
        :param properties: (Optional) A list of strings representing
            property names to be included in the returned object.
            Nonexistent properties are ignored.
        :param associations: (Optional) A list of strings representing
            object types to retrieve as associated object IDs.

        :return: The requested object as a ``SimplePublicObject`` or
            ``SimplePublicObjectWithAssociations`` type. If a batch request
            was made, it returns a list of ``SimplePublicObject``.

        """

        self._require_authentication()

        if isinstance(object_id, list):
            return self._get_object_by_batch(
                object_type, object_id, id_property, properties
            )
        else:
            return self._get_object(
                object_type, object_id, id_property, properties, associations
            )

    @property
    def pipelines(self) -> Dict[str, List[Pipeline]]:
        return self._pipelines

    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=0.1),
        before_sleep=_before_sleep_log(),
    )
    def _set_pipelines(self, object_type: str, archived: bool = False):
        self._require_authentication()
        valid_object_type = self._validate_object_type(object_type)
        self._pipelines[valid_object_type] = (
            self.hs.crm.pipelines.pipelines_api.get_all(
                valid_object_type, archived=archived
            )
        ).results

    def _get_cached_pipeline(self, object_type, pipeline_id):
        return next(
            (
                p
                for p in self.pipelines.get(object_type, [])
                if pipeline_id in (p.id, p.label)
            ),
            None,
        )

    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=0.1),
        before_sleep=_before_sleep_log(),
    )
    def _get_set_a_pipeline(self, object_type, pipeline_id, use_cache=True):
        self._require_authentication()
        valid_object_type = self._validate_object_type(object_type)
        if (
            self._get_cached_pipeline(valid_object_type, pipeline_id) is None
            or not use_cache
        ):
            try:
                response = self.hs.crm.pipelines.pipelines_api.get_by_id(
                    valid_object_type, pipeline_id
                )
                if self.pipelines.get(valid_object_type) is not list:
                    self._pipelines[valid_object_type] = []
                self._pipelines[valid_object_type].extend([response])
            except PipelineApiException:
                self._set_pipelines(valid_object_type)
        return self._get_cached_pipeline(valid_object_type, pipeline_id)

    def _get_pipelines(
        self, object_type, pipeline_id=None, archived=False, use_cache=True
    ):
        self._require_authentication()
        valid_object_type = self._validate_object_type(object_type)
        if self.pipelines.get(valid_object_type) is None or not use_cache:
            if pipeline_id is None:
                self._set_pipelines(valid_object_type, archived)
            else:
                self._get_set_a_pipeline(object_type, pipeline_id, use_cache=False)
        return (
            self._get_set_a_pipeline(object_type, pipeline_id, use_cache)
            if pipeline_id
            else self.pipelines[valid_object_type]
        )

    @keyword
    def list_pipelines(
        self, object_type: str, archived: bool = False, use_cache: bool = True
    ) -> List[Pipeline]:
        """Returns a list of all pipelines configured in Hubspot for the
        provided ``object_type``. By default only active, unarchived pipelines
        are returned.

        This keyword caches results for future use, to refresh results from
        Hupspot, set ``use_cache`` to ``False``.

        :param object_type: The object type to be returned and that has
            the ID indicated. Custom objects will be validated against the
            schema.
        :param archived: (Optional) Setting this to ``True`` will return
            archived pipelines as well.
        :param use_cache: (Optional) Setting this to ``False`` will force
            the system to recache the pipelines from Hubspot.

        :return: A list of ``Pipeline`` objects representing the pipelines
            associated with the provided ``object_type``.

        """
        self._require_authentication()

        return self._get_pipelines(
            self._validate_object_type(object_type),
            archived=archived,
            use_cache=use_cache,
        )

    @keyword
    def get_pipeline(
        self, object_type: str, pipeline_id: str, use_cache: bool = True
    ) -> Pipeline:
        """Returns the ``object_type`` pipeline identified by ``pipeline_id``.
        The provided ``pipeline_id`` can be provided as the label (case sensitive)
        or API ID code.

        The ``Pipeline`` object returned includes a ``stages`` property, which
        is a list of ``PipelineStage`` objects. The ``stages`` of the pipeline
        represent the discreet steps an object travels through within the pipeline.
        The order of the steps is determined by the ``display_order`` property.
        These properties can be accessessed with dot notation and generator
        comprehension; however, these are advanced Python concepts, so
        it is generally easier to use the keyword ``Get Pipeline Stages`` to
        get an ordered dictionary of the stages from first to last.

        **Example**

        .. code-block:: robotframework

            *** Tasks ***
            Get Step One
                ${pipeline}=    Get pipeline    DEALS   default
                ${step_one}=    Evaluate
                ... next((s.label for s in $pipeline.stages if s.display_order == 0))

        This keyword caches results for future use, to refresh results from
        Hupspot, set ``use_cache`` to ``False``.

        :param object_type: The object type to be returned and that has
            the ID indicated. Custom objects will be validated against the
            schema.
        :param pipeline_id: The numerical pipeline ID or the pipeline
            label visibal in the HubSpot UI (case sensitive).
        :param use_cache: (Optional) Setting this to ``False`` will force
            the system to recache the pipelines from Hubspot.

        :return: The ``Pipeline`` object requested.

        """  # noqa: E501
        self._require_authentication()

        return self._get_pipelines(
            self._validate_object_type(object_type),
            pipeline_id=pipeline_id,
            use_cache=use_cache,
        )

    @keyword
    def get_pipeline_stages(
        self,
        object_type: str,
        pipeline_id: str,
        label_as_key: bool = True,
        use_cache: bool = True,
    ) -> Dict[str, Dict]:
        """Returns a dictionary representing the stages available in the
        requested pipeline. Only pipelines for ``object_type`` are searched
        using the ``pipeline_id`` as the label or Hubspot API identifier code.

        By default, the keys of the returned dictionary represent the labels
        of the stages, in order from first to last stage. You can have the
        keyword return the numerical API ID as the key instead by setting
        ``label_as_key`` to ``False``.

        Each item's value is a dictionary with three keys: ``id``, ``label``
        and ``metadata``. The ``id`` is the numerical API ID associated with
        the stage and ``label`` is the name of that stage. The
        ``metadata`` is a dictionary of metadata associated with that stage
        (e.g., ``isClosed`` and ``probability`` for "deals" pipelines) that
        is unique per pipeline.

        **Example**

        .. code-block:: robotframework

            *** Settings ***
            Library         RPA.Hubspot
            Library         RPA.Robocorp.Vault

            Task Setup      Authorize Hubspot

            *** Tasks ***
            Use pipeline stages
                ${stages}=    Get pipeline stages    DEALS    Default
                ${closed_won_stage_id}=    Set variable    ${stages}[Closed Won][id]
                ${deals}=    Search for objects    DEALS
                ...    dealstage    EQ    ${closed_won_stage_id}
                Log    Deals that have been won: ${deals}

            *** Keywords ***
            Authorize Hubspot
                ${secrets}=    Get secret    hubspot
                Auth with api key    ${secrets}[API_KEY]

        This keyword caches results for future use, to refresh results from
        Hupspot, set ``use_cache`` to ``False``.

        :param object_type: The object type to be returned and that has
            the ID indicated. Custom objects will be validated against the
            schema.
        :param pipeline_id: The numerical pipeline ID or the pipeline
            label visibal in the HubSpot UI (case sensitive).
        :param label_as_key: (Optional) Defaults to ``True``. Setting this
            to ``False`` will cause the returned dictionary to key off of ``id``
            instead of ``label``.
        :param use_cache: (Optional) Setting this to ``False`` will force
            the system to recache the pipelines from Hubspot.

        :return: A dictionary representing the pipeline stages and associated
            data.

        """
        self._require_authentication()
        stages = self.get_pipeline(object_type, pipeline_id, use_cache).stages
        stages.sort(key=lambda s: (s.display_order, s.label))
        if label_as_key:
            return {
                s.label: {"id": s.id, "label": s.label, "metadata": dict(s.metadata)}
                for s in stages
            }
        else:
            return {
                s.id: {"id": s.id, "label": s.label, "metadata": dict(s.metadata)}
                for s in stages
            }

    @keyword
    def get_current_stage_of_object(
        self,
        object_type: str,
        object_id: str,
        id_property: Optional[str] = None,
        label_as_key: bool = True,
        use_cache: bool = True,
    ) -> Tuple[str, Dict]:
        """Returns the current pipeline stage for the object as a tuple of
        the stage label and that stage's associated metadata as a dictionary.
        If you want the label to be returned as the numerical API ID, set
        ``label_as_key`` to False.

        If the object type does not have an applied pipeline, the keyword
        will fail.

        This keyword caches results for future use, to refresh results from
        Hupspot, set ``use_cache`` to ``False``.

        :param object_type: The object type to be returned and that has
            the ID indicated. Custom objects will be validated against the
            schema.
        :param object_id: The ID of the object to be returned.
        :param id_property: (Optional) Can be used to allow the API to
            search the object database using an alternate property as the
            unique ID.
        :param label_as_key: (Optional) Defaults to ``True``. Setting this
            to ``False`` will cause the returned dictionary to key off of ``id``
            instead of ``label``.
        :param use_cache: (Optional) Setting this to ``False`` will force
            the system to recache the pipelines from Hubspot.

        :return: A tuple where index 0 is the label or ID of the object's
            current stage and index 1 is associated data.

        """
        self._require_authentication()
        hs_object = self.get_object(object_type, object_id, id_property)
        if hs_object.properties.get("pipeline"):
            pipeline_stages = self.get_pipeline_stages(
                object_type,
                hs_object.properties["pipeline"],
                label_as_key=False,
                use_cache=use_cache,
            )
            stage_key = hs_object.properties.get(
                "dealstage", hs_object.properties.get("hs_pipeline_stage")
            )
            stage_label = (
                pipeline_stages[stage_key]["label"]
                if label_as_key
                else pipeline_stages[stage_key]
            )
            return (stage_label, pipeline_stages[stage_key])
        else:
            raise HubSpotNoPipelineError(
                f"The {object_type} object type with ID "
                + f"'{object_id}' is not in a pipeline."
            )

    @keyword
    def get_user(self, user_id: str = "", user_email: str = "") -> Dict:
        """Returns a dictionary with the keys ``id`` and ``email`` based on the
        provided ``user_id`` or ``user_email``. If both are provided, this
        keyword will prefer the ``user_id``.

        .. note:: This keyword searches system users, not the CRM
            owners database.
        """
        self._require_token_authentication()

        if user_id:
            url = f"https://api.hubapi.com/settings/v3/users/{user_id}"
            params = None
        else:
            url = f"https://api.hubapi.com/settings/v3/users/{user_email}"
            params = {"idProperty": "EMAIL"}

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.hs.access_token}",
        }

        response = requests.request("GET", url, headers=headers, params=params)
        response.raise_for_status()
        self.logger.debug(
            f"Response is:\nStatus: {response.status_code} {response.reason}\n"
            + f"Content: {response.json()}"
        )
        return response.json()

    @keyword
    @retry(
        retry=retry_if_exception(_is_rate_limit_error),
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=2, min=0.1),
        before_sleep=_before_sleep_log(),
    )
    def get_owner_by_id(
        self, owner_id: str = "", owner_email: str = "", user_id: str = ""
    ) -> PublicOwner:
        r"""Returns an owner object with details about a HubSpot user denoted
        as an owner of another HubSpot object, such as a contact or company.
        You may provide the identifier as ``owner_id``, ``owner_email``, or
        ``user_id``. The ``owner_id`` will correspond to fields from the
        CRM API while the ``user_id`` will correspond to the user
        provisioning API (see keyword \`Get User\`).

        The owner object has the following attributes (accessible via
        dot notation):

        If more than one of these IDs are provided, the keyword prefers
        the ``owner_id``, then ``owner_email``, then the ``user_id``.

        :param owner_id: The owner's HubSpot ID.
        :param owner_email: The email address registered to the owner.
        :param user_id: The owner's associated HubSpot user ID.

        :return: The requested ``PublicOwner`` object.

        """
        self._require_authentication()
        if owner_id:
            id_property = "id"
        elif owner_email:
            id_property = "email"
        elif user_id:
            id_property = "userId"
        else:
            raise ValueError("All arguments cannot be empty.")
        return self.hs.crm.owners.owners_api.get_by_id(
            owner_id, id_property=id_property
        )

    @keyword
    def get_owner_of_object(
        self,
        hs_object: Union[SimplePublicObject, SimplePublicObjectWithAssociations, Dict],
        owner_property: str = None,
    ) -> PublicOwner:
        r"""Looks up the owner of a given Hubspot object, the provided object
        should be from this library or it should be a dictionary with an
        ``hubspot_owner_id`` key. If the object has no owner, this keyword
        returns None. See keyword \`Get owner by ID\` for information about
        the returned object.

        You can use an alternate property as the owner ID property by providing
        it with argument ``owner_property``. If that property does not exist
        this keyword will try the default ``hubspot_owner_id`` property, instead.

        :param object: A HubSpot object, best if the object was obtained
            via another keyword such as \`Get owner by ID\`
        :param owner_property: An alternate property of the provided
            object to use as the field containing the Owner to be looked up.

        :return: The ``PublicOwner`` of the provided object.

        """
        self._require_authentication()
        try:
            if owner_property:
                owner_id = getattr(
                    hs_object.properties,
                    owner_property,
                    hs_object.properties.get(
                        owner_property, hs_object.properties["hubspot_owner_id"]
                    ),
                )
            else:
                owner_id = getattr(
                    hs_object.properties,
                    "hubspot_owner_id",
                    hs_object.properties["hubspot_owner_id"],
                )
        except AttributeError:
            self.logger.debug(
                "AttributeError caught while attempting to retrieve "
                + "owner information from object."
                + f"\nObject details: {hs_object}."
                + f"\nError details:\n{traceback.format_exc()}"
            )
            return None

        return self.get_owner_by_id(owner_id)
