import logging
import traceback
from typing import List, Dict, Optional, Tuple, Union
from retry import retry

from pprint import pprint

from robot.api.deco import keyword, library

import requests
from hubspot import HubSpot as HubSpotApi
from hubspot.crm.objects.models import (
    PublicObjectSearchRequest as ObjectSearchRequest,
    FilterGroup,
    Filter,
    SimplePublicObject,
    SimplePublicObjectWithAssociations,
    AssociatedId,
)
from hubspot.crm.schemas.models import ObjectSchema
from hubspot.crm.pipelines.models import (
    Pipeline,
    PipelineStage,
)
from hubspot.crm.owners.models import PublicOwner
from hubspot.crm.objects.exceptions import ApiException as ObjectApiException
from hubspot.crm.schemas.exceptions import ApiException as SchemaApiException
from hubspot.crm.pipelines.exceptions import ApiException as PipelineApiException
from hubspot.crm.owners.exceptions import ApiException as OwnersApiException


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


@library(scope="Global", doc_format="REST")
class Hubspot:
    """`Hubspot` is a library for accessing HubSpot using REST API.

    Current features of this library focus on retrieving object data
    from HubSpot via API.

    **Using Date Times**

    When using date times with the Hubspot API, you must provide
    them as Unix-style epoch timestamps (with milliseconds), which can be obtained
    using the `DateTime` library's `Convert Date` with the
    argument `result_format=epoch`. The resulting timestamp string
    will be a float, but the API only accepts integers, so you must
    multiply the resulting timestamp by 1,000 and then round  it to
    the nearest integar to include in API calls (i.e., the resulting
    integer sent to the API must have 13 digits as of March 18, 2022).
    """

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

    @property
    @retry(HubSpotRateLimitError, tries=5, delay=0.1, jitter=(0.1, 0.2), backoff=2)
    def schemas(self) -> List[ObjectSchema]:
        self._require_authentication()
        if len(self._schemas) == 0:
            try:
                self.schemas = self.hs.crm.schemas.core_api.get_all()
            except SchemaApiException as e:
                if e.status == 429:
                    self.logger.debug("Rate limit exceeded, retry should occur.")
                    raise HubSpotRateLimitError from e
                else:
                    raise e
        return self._schemas

    @schemas.setter
    def schemas(self, results):
        if hasattr(results, "results"):
            results = results.results
        if isinstance(results, list) and isinstance(results[0], ObjectSchema):
            self._schemas = results
        else:
            raise TypeError(
                "Invalid values for `results`, must be list of `ObjectSchema`."
            )

    def _get_custom_object_schema(self, name: str) -> Dict:
        self._require_authentication()
        for s in self.schemas:
            if (
                s.name == name.lower()
                or s.labels.singular.lower() == name.lower()
                or s.labels.plural.lower() == name.lower()
            ):
                return s

    def _get_custom_object_id(self, name: str) -> str:
        self._require_authentication()
        schema = self._get_custom_object_schema(self._validate_object_type(name))
        return schema.object_type_id

    def _singularize_object(self, name: str) -> str:
        if len(self._singular_map) == 0:
            self._singular_map = self.BUILTIN_SINGULAR_MAP
            labels = [s.labels for s in self.schemas]
            self._singular_map.update({l.plural: l.singular for l in labels})
            self._singular_map.update(
                {s.object_type_id: s.object_type_id for s in self.schemas}
            )
        return self._singular_map[self._validate_object_type(name)]

    def _pluralize_object(self, name: str) -> str:
        if len(self._plural_map) == 0:
            self._plural_map = self.BUILTIN_PLURAL_MAP
            labels = [s.labels for s in self.schemas]
            self._plural_map.update({l.singular: l.plural for l in labels})
            self._plural_map.update(
                {s.object_type_id: s.object_type_id for s in self.schemas}
            )
        return self._plural_map[self._validate_object_type(name)]

    def _validate_object_type(self, name: str) -> str:
        """Validates the provided `name` against the built in list of
        object types and the list of custom object type schemas. Returns
        the validated custom object ID or name in lower case.
        Raises `HubSpotObjectTypeError` if `name` cannot be validated.
        """
        valid_names = list(self.BUILTIN_SINGULAR_MAP.keys())
        valid_names.extend([s.object_type_id for s in self.schemas])
        valid_names.extend([s.name for s in self.schemas])
        valid_names.extend([s.labels.plural.lower() for s in self.schemas])
        if name.lower() in valid_names:
            return name.lower()
        else:
            raise HubSpotObjectTypeError(
                f"Object type {name} does not exist. Current accepted names are:\n{valid_names}."
            )

    def _create_search_object(self, words: List):
        def _split(words: List, oper: str):
            self.logger.debug(f"Words to split on operator '{oper}': {words}")
            size = len(words)
            first_index_list = [i + 1 for i, v in enumerate(words) if v == oper]
            second_index_list = [i for i, v in enumerate(words) if v == oper]
            self.logger.debug(f"Index list is: {first_index_list}")
            split_result = [
                words[i:j]
                for i, j in zip(
                    [0] + first_index_list,
                    second_index_list
                    + ([size] if second_index_list[-1] != size else []),
                )
            ]
            self.logger.debug(f"Split result: {split_result}")
            return split_result

        def _process_and(words: List):
            if words.count("AND") > 3:
                raise HubSpotSearchParseError(
                    "No more than 3 logical 'AND' operators can be used between each 'OR' operator."
                )
            search_filters = []
            if "AND" in words:
                word_filters = _split(words, "AND")
                self.logger.debug(
                    f"Found these groups of words as Filters: {word_filters}"
                )
                for word_filter in word_filters:
                    search_filters.append(_process_filter(word_filter))
            else:
                self.logger.debug(f"Found this group of words as Filter: {words}")
                search_filters.append(_process_filter(words))
            return search_filters

        def _process_filter(words: List):
            self.logger.debug(f"Attempting to turn {words} into Filter object.")
            if len(words) not in (2, 3):
                raise HubSpotSearchParseError(
                    f"The provided words cannot be parsed as a search object. The words {words} could not be parsed."
                )
            if words[1] not in ("HAS_PROPERTY", "NOT_HAS_PROPERTY"):
                search_filter = Filter(
                    property_name=words[0], operator=words[1], value=words[2]
                )
            else:
                search_filter = Filter(property_name=words[0], operator=words[1])
            self.logger.debug(f"Resulting Filter object: {search_filter}")
            return search_filter

        if words.count("OR") > 3:
            raise HubSpotSearchParseError(
                "No more than 3 logical 'OR' operators can be used."
            )
        filter_groups = []
        if "OR" in words:
            word_groups = _split(words, "OR")
            self.logger.debug(
                f"Found these groups of words as FilterGroups: {word_groups}"
            )
            for word_group in word_groups:
                filter_groups.append(FilterGroup(_process_and(word_group)))
        else:
            self.logger.debug(f"Found this group of words as FilterGroup: {words}")
            filter_groups.append(FilterGroup(_process_and(words)))
        return ObjectSearchRequest(filter_groups)

    @retry(HubSpotRateLimitError, tries=5, delay=0.1, jitter=(0.1, 0.2), backoff=2)
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
        try:
            response = self.hs.crm.objects.search_api.do_search(
                object_type, public_object_search_request=search_object
            )
        except ObjectApiException as e:
            if e.status == 429:
                self.logger.debug("Rate limit exceeded, retry should occur.")
                raise HubSpotRateLimitError from e
            else:
                raise e
        self.logger.debug(f"First response received:\n{response}")
        results = []
        results.extend(response.results)
        if response.paging:
            search_object.after = response.paging.next.after
            while len(results) < max_results or max_results <= 0:
                self.logger.debug(f"Current cursor is: {search_object.after}")
                try:
                    page = self.hs.crm.objects.search_api.do_search(
                        object_type, public_object_search_request=search_object
                    )
                except ObjectApiException as e:
                    if e.status == 429:
                        self.logger.debug("Rate limit exceeded, retry should occur.")
                        raise HubSpotRateLimitError from e
                    else:
                        raise e
                results.extend(page.results)
                if page.paging is None:
                    break
                search_object.after = page.paging.next.after
        self.logger.debug(f"Total results found: {len(results)}")
        return results

    @keyword
    def auth_with_token(self, access_token: str) -> None:
        """Authorize to HubSpot with Private App access token.

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
                    )
                else:
                    raise e
            self.logger.info("Authentication to Hubspot CRM API with token successful.")
        else:
            self.logger.info("Already authenticated with access token.")

    @keyword
    def auth_with_api_key(self, api_key: str) -> None:
        """Authorize to HubSpot with an account-wide API key.

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
                    )
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
        properties: Optional[List[str]] = None,
        max_results: int = 1000,
    ) -> List[SimplePublicObject]:
        """Returns a list of objects of the specified `type` based on the
        provided `search` criteria. The following types are supported:
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

        Returns no more than `max_results` which defaults to 1,000 records.
        Provide 0 for all results.

        Search criteria must be pased as a list of dictionaries. For
        example, to search for contacts with the first name of "Alice",
        you would construct the `search` criteria like so:

        .. code-block:: python

            alice_search = [
                {
                    "filters": [
                        {
                            "propertyName": "firstname",
                            "operator": "EQ",
                            "value": "Alice",
                        }
                    ]
                }
            ]

        To include multiple filter criteria, you can group filters within
        `filterGroups`:
         - When multiple `filters` are present within a `filterGroup`, they'll
         be combined using a logical AND operator.
         - When multiple `filterGroups` are included in the request body,
         they'll be combined using a logical OR operator.
        You can include a maximum of three filterGroups with up to three
        filters in each group.

        For example, the request below searches for all contacts with a
        first name of "Alice" and a last name that is not "Smith", OR has
        a value for the property `enum1`.

        .. code-block:: python

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

        You can use the following operators in a filter:

        +---------------------+----------------------------------------------------+
        | OPERATOR            | DESCRIPTION                                        |
        +=====================+====================================================+
        | LT                  | Less than                                          |
        | LTE                 | Less than or equal to                              |
        | GT                  | Greater than                                       |
        | GTE                 | Greater than or equal to                           |
        | EQ                  | Equal to                                           |
        | NEQ                 | Not equal to                                       |
        | HAS_PROPERTY        | Has a value for the specified property.            |
        | NOT_HAS_PROPERTY    | Doesn't have a value for the specified property.   |
        | CONTAINS_TOKEN      | Contains a token.                                  |
        | NOT_CONTAINS_TOKEN  | Doesn't contain a token.                           |
        +---------------------+----------------------------------------------------+

        You can retrieve additional properties for the objects by defining
        them with `properties`. If a requested property does not exist,
        it will be ignored.

        Associated objects can be used as search criteria by using the
        pseudo-property `associations.{object_type}`.

        :param search: the search object to use as search criteria.
        :param string_query: a string query can be provided instead of a
        search object which is used as a text-based search in all default
        searchable properties in Hubspot.
        :param properties: a list of strings representing return properties
        to be included in the returned data.
        :return: A list of found hubspot objects.
        """
        self._require_authentication()

        if string_query:
            search_object = ObjectSearchRequest(query=string_query)
        elif natural_search:
            search_object = self._create_search_object(natural_search)
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
        search_object.properties = properties
        return self._search_objects(
            self._pluralize_object(self._validate_object_type(object_type)),
            search_object,
            max_results=max_results,
        )

    @keyword
    @retry(HubSpotRateLimitError, tries=5, delay=0.1, jitter=(0.1, 0.2), backoff=2)
    def list_associations(
        self, object_type: str, object_id: str, to_object_type: str
    ) -> List[AssociatedId]:
        """List associations of an object by type, you must define the `object_type`
        with its `object_id`. You must also provide the associated objects with
        `to_object_type`. The API will return a list of dictionaries with
        the associated object `id` and association `type` (e.g., `contact_to_company`).

        :param object_type: The type of object for the object ID provided, e.g. `contact`.
        :param object_id: The HubSpot ID for the object of type `object_type`.
        :param to_object_type: The type of object associations to return.
        :return: A list of dictionaries representing the associated objects.
        """

        self._require_authentication()
        results = []
        after = None
        while True:
            try:
                page = self.hs.crm.objects.associations_api.get_all(
                    self._validate_object_type(self._singularize_object(object_type)),
                    object_id,
                    self._validate_object_type(
                        self._singularize_object(to_object_type)
                    ),
                    after=after,
                    limit=500,
                )
            except ObjectApiException as e:
                if e.status == 429:
                    self.logger.debug("Rate limit exceeded, retry should occur.")
                    raise HubSpotRateLimitError from e
                else:
                    raise e
            results.extend(page.results)
            if page.paging is None:
                break
            after = page.paging.next.after
        return results

    @keyword
    @retry(HubSpotRateLimitError, tries=5, delay=0.1, jitter=(0.1, 0.2), backoff=2)
    def get_object(
        self,
        object_type: str,
        object_id: str,
        id_property: Optional[str] = None,
        properties: Optional[Union[str, List[str]]] = None,
        associations: Optional[Union[str, List[str]]] = None,
    ) -> Union[SimplePublicObject, SimplePublicObjectWithAssociations]:
        """Reads a single object of `object_type` from HubSpot with the
        provided `object_id`. The objects can be found using an
        alternate ID by providing the name of that HubSpot property
        which contains the unique identifier to `id_property`. The `object_type`
        parameter automatically looks up custom object IDs based on the
        provided name.

        A list of property names can be provided to `properties`
        and they will be included in the returned object. Nonexistent
        properties are ignored.

        A list of object types can be provided to `associations` and all
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
        :return: A dictionary representing the requested object.
        """

        self._require_authentication()

        try:
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
        except ObjectApiException as e:
            if e.status == 429:
                self.logger.debug("Rate limit exceeded, retry should occur.")
                raise HubSpotRateLimitError from e
            else:
                raise e

    @property
    def pipelines(self) -> Dict[str, List[Pipeline]]:
        return self._pipelines

    @retry(HubSpotRateLimitError, tries=5, delay=0.1, jitter=(0.1, 0.2), backoff=2)
    def _set_pipelines(self, object_type: str, archived: bool = False):
        self._require_authentication()
        valid_object_type = self._validate_object_type(object_type)
        try:
            self._pipelines[valid_object_type] = (
                self.hs.crm.pipelines.pipelines_api.get_all(
                    valid_object_type, archived=archived
                )
            ).results
        except PipelineApiException as e:
            if e.status == 429:
                self.logger.debug("Rate limit exceeded, retry should occur.")
                raise HubSpotRateLimitError from e
            else:
                raise e

    def _get_cached_pipeline(self, object_type, pipeline_id):
        return next(
            (
                p
                for p in self.pipelines.get(object_type, [])
                if p.id == pipeline_id or p.label == pipeline_id
            ),
            None,
        )

    @retry(HubSpotRateLimitError, tries=5, delay=0.1, jitter=(0.1, 0.2), backoff=2)
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
            except PipelineApiException as e:
                if e.status == 429:
                    self.logger.debug("Rate limit exceeded, retry should occur.")
                    raise HubSpotRateLimitError from e
                else:
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
        provided `object_type`. By default only active, unarchived pipelines
        are returned.

        This keyword caches results for future use, to refresh results from
        Hupspot, set `use_cache` to `False`.
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
        """Returns the `object_type` pipeline identified by `pipeline_id`.
        The provided `pipeline_id` can be provided as the label (case sensitive)
        or API ID code.

        The `Pipeline` object returned includes a `stages` property, which
        is a list of `PipelineStage` objects. The `stages` of the pipeline represent
        the discreet steps an object travels through within the pipeline.
        The order of the steps is determined by the `display_order` property.
        These properties can be accessessed with dot notation and generator
        comprehension; however, these are advanced Python concepts, so
        it is generally easier to use the keyword `Get Pipeline Stages` to
        get an ordered dictionary of the stages from first to last.

        ** Examples **

        ** Robot Framework **

        .. code-block:: robotframework

            ${pipeline}=    Get pipeline    DEALS   default
            ${step_one}=    Evaluate   ${{next((s.label for s in $pipeline.stages if s.display_order == 0))}}


        This keyword caches results for future use, to refresh results from
        Hupspot, set `use_cache` to `False`.
        """
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
        requested pipeline. Only pipelines for `object_type` are searched
        using the `pipeline_id` as the label or Hubspot API identifier code.

        By default, the keys of the returned dictionary represent the labels
        of the stages, in order from first to last stage. You can have the
        keyword return the numerical API ID as the key instead by setting
        `label_as_key` to `False`.

        Each item's value is a dictionary with three keys: `id`, `label`
        and `metadata`. The `id` is the numerical API ID associated with
        the stage and `label` is the name of that stage. The
        `metadata` is a dictionary of metadata associated with that stage
        (e.g., `isClosed` and `probability` for "deals" pipelines) that
        is unique per pipeline.

        This keyword caches results for future use, to refresh results from
        Hupspot, set `use_cache` to `False`.
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
        `label_as_key` to False.

        If the object type does not have an applied pipeline, the keyword
        will fail.

        This keyword caches results for future use, to refresh results from
        Hupspot, set `use_cache` to `False`.
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
                f"The {object_type} object type with ID '{object_id}' is not in a pipeline."
            )

    @keyword
    def get_user(self, user_id: str = "", user_email: str = "") -> Dict:
        """Returns a dictionary with the keys `id` and `email` based on the
        provided `user_id` or `user_email`. If both are provided, this
        keyword will prefer the `user_id`
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
            f"Response is:\nStatus: {response.status_code} {response.reason}\nContent: {response.json()}"
        )
        return response.json()

    @keyword
    @retry(HubSpotRateLimitError, tries=5, delay=0.1, jitter=(0.1, 0.2), backoff=2)
    def get_owner_by_id(
        self, owner_id: str = "", owner_email: str = "", user_id: str = ""
    ) -> PublicOwner:
        """Returns an owner object with details about a Hubspot user denoted
        as an owner of another Hubspot object, such as a contact or company.
        You may provide the identifier as `owner_id`, `user_id`, or `owner_email`.
        The `owner_id` will correspond to fields from the CRM API while the `user_id`
        will correspond to the user provisioning API (see keyword `Get User`).

        The owner object has the following properties (accessible via
        dot notation):
         - `id`
         - `email`
         - `first_name`
         - `last_name`
         - `user_id`
         - `created_at`
         - `updated_at`
         - `archived`

        If more than one of these IDs are provided, the keyword prefers
        the `owner_id`, then `owner_email`, then the `user_id`.
        """
        self._require_authentication()
        try:
            if owner_id:
                return self.hs.crm.owners.owners_api.get_by_id(
                    owner_id, id_property="id"
                )
            elif owner_email:
                return self.hs.crm.owners.owners_api.get_by_id(
                    owner_email, id_property="email"
                )
            elif user_id:
                return self.hs.crm.owners.owners_api.get_by_id(
                    user_id, id_property="userId"
                )
        except OwnersApiException as e:
            if e.status == 429:
                self.logger.debug("Rate limit exceeded, retry should occur.")
                raise HubSpotRateLimitError from e
            else:
                raise e

    @keyword
    def get_owner_of_object(
        self,
        object: Union[SimplePublicObject, SimplePublicObjectWithAssociations, Dict],
        owner_property: str = None,
    ) -> PublicOwner:
        """Looks up the owner of a given Hubspot object, the provided object
        should be from this library or it should be a dictionary with an
        `hubspot_owner_id` key. If the object has no owner, this keyword
        returns None. See keyword `Get Owner By ID` for information about
        the returned object.

        You can use an alternate property as the owner ID property by providing
        it with argument `owner_property`. If that property does not exist
        this keyword will try the default `hubspot_owner_id` property, instead.
        """
        self._require_authentication()
        try:
            if owner_property:
                owner_id = getattr(
                    object.properties,
                    owner_property,
                    object.properties.get(
                        owner_property, object.properties["hubspot_owner_id"]
                    ),
                )
            else:
                owner_id = getattr(
                    object.properties,
                    "hubspot_owner_id",
                    object.properties["hubspot_owner_id"],
                )
        except AttributeError:
            self.logger.debug(
                "AttributeError caught while attempting to retrieve owner information from object."
                + f"\nObject details: {object}."
                + f"\nError details:\n{traceback.format_exc()}"
            )
            return None

        return self.get_owner_by_id(owner_id)
