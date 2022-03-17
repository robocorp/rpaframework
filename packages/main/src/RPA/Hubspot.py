from ast import keyword
import logging
import re
from os import access
from typing import List, Dict, Optional, Union

from pprint import pprint

from robot.api.deco import keyword, library

from hubspot import HubSpot as HubSpotApi
from hubspot.utils.objects import fetch_all
from hubspot.crm.objects import (
    PublicObjectSearchRequest as ObjectSearchRequest,
    FilterGroup,
    Filter,
    SimplePublicObject,
    SimplePublicObjectWithAssociations,
    AssociatedId,
)


class HubSpotAuthenticationError(Exception):
    "Error when authenticated HubSpot instance does not exist."


class HubSpotObjectTypeError(Exception):
    "Error when the object type provided does not exist."


class HubSpotSearchParseError(Exception):
    "Error when the natural word search engine cannot parse the provided words."


@library(scope="Global", doc_format="REST")
class Hubspot:
    """`Hubspot` is a library for accessing HubSpot using REST API.

    Current features of this library focus on retrieving object data
    from HubSpot via API.
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

    def __init__(self, hubspot_apikey: str = None) -> None:
        self.logger = logging.getLogger(__name__)
        if hubspot_apikey:
            self.hs = HubSpotApi(access_token=hubspot_apikey)
        else:
            self.hs = None
        self.schemas = None
        self.singular_map = None
        self.plural_map = None

    def _require_authentication(self) -> None:
        if self.hs is None:
            raise HubSpotAuthenticationError("Authentication was not completed.")

    def _get_all_schemas(self) -> List[Dict]:
        self._require_authentication()
        if self.schemas is None:
            self.schemas = self.hs.crm.schemas.core_api.get_all()
        return self.schemas.results

    def _get_custom_object_schema(self, name: str) -> Dict:
        self._require_authentication()
        for s in self._get_all_schemas():
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
        if self.singular_map is None:
            self.singular_map = self.BUILTIN_SINGULAR_MAP
            schemas = self._get_all_schemas()
            labels = [s.labels for s in schemas]
            self.singular_map.update({l.plural: l.singular for l in labels})
            self.singular_map.update(
                {s.object_type_id: s.object_type_id for s in schemas}
            )
        return self.singular_map[self._validate_object_type(name)]

    def _pluralize_object(self, name: str) -> str:
        if self.plural_map is None:
            self.plural_map = self.BUILTIN_PLURAL_MAP
            schemas = self._get_all_schemas()
            labels = [s.labels for s in schemas]
            self.plural_map.update({l.singular: l.plural for l in labels})
            self.plural_map.update(
                {s.object_type_id: s.object_type_id for s in schemas}
            )
        return self.plural_map[self._validate_object_type(name)]

    def _validate_object_type(self, name: str) -> str:
        """Validates the provided `name` against the built in list of
        object types and the list of custom object type schemas. Returns
        the validated custom object ID or name in lower case.
        Raises `HubSpotObjectTypeError` if `name` cannot be validated.
        """
        valid_names = list(self.BUILTIN_SINGULAR_MAP.keys())
        valid_names.extend([s.object_type_id for s in self._get_all_schemas()])
        valid_names.extend([s.name for s in self._get_all_schemas()])
        if name.lower() in valid_names:
            return name.lower()
        else:
            raise HubSpotObjectTypeError(f"Object type {name} does not exist.")

    def _create_search_object(self, words: List):
        def _split(words: List, oper: str):
            size = len(words)
            index_list = [i + 1 for i, v in enumerate(words) if v == oper]
            return [
                words[i:j]
                for i, j in zip(
                    [0] + index_list,
                    index_list + ([size] if index_list[-1] != size else []),
                )
            ]

        def _process_and(words: List):
            if words.count("AND") > 3:
                raise HubSpotSearchParseError(
                    "No more than 3 logical 'AND' operators can be used between each 'OR' operator."
                )
            search_filters = []
            if "AND" in words:
                word_filters = _split(words, "AND")
                for word_filter in word_filters:
                    search_filters.append(_process_filter(word_filter))
            else:
                search_filters.append(_process_filter(words))
            return search_filters

        def _process_filter(words: List):
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
            return search_filter

        if words.count("OR") > 3:
            raise HubSpotSearchParseError(
                "No more than 3 logical 'OR' operators can be used."
            )
        filter_groups = []
        if "OR" in words:
            word_groups = _split(words, "OR")
            for word_group in word_groups:
                filter_groups.append(FilterGroup(_process_and(word_group)))
        else:
            filter_groups.append(FilterGroup(_process_and(words)))
        return ObjectSearchRequest(filter_groups)

    def _search_objects(
        self,
        object_type: str,
        search_object: ObjectSearchRequest,
        max_results: int = 1000,
    ) -> List[SimplePublicObject]:
        self._require_authentication()
        search_object.limit = 100
        self.logger.debug(f"Search to use is:\n{search_object}")
        response = self.hs.crm.objects.search_api.do_search(
            object_type, public_object_search_request=search_object
        )
        self.logger.debug(f"First response received:\n{response}")
        results = []
        results.extend(response.results)
        if response.paging:
            search_object.after = response.paging.next.after
            while len(results) < max_results or max_results <= 0:
                self.logger.debug(f"Current cursor is: {search_object.after}")
                page = self.hs.crm.objects.search_api.do_search(
                    object_type, public_object_search_request=search_object
                )
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
        self.hs = HubSpotApi(access_token=access_token)

    @keyword
    def auth_with_api_key(self, api_key: str) -> None:
        """Authorize to HubSpot with an account-wide API key.

        :param api_key: The API key for the account to autheniticate to.
        """
        self.hs = HubSpotApi(api_key=api_key)

    def list_contacts(
        self, properties: List[str] = None, associations: List[str] = None
    ) -> List[dict]:
        """Returns a list of available contacts. A list of properties
        and associations can be provided and will be included in the
        returned list.

        :param properties: a list of strings representing properties of
        the HubSpot Contacts to be returned. If such a property does not
        exist, it will be ignored.
        :param associations: a list of object types to retrieve associated
        IDs for. If such an object type does not exist, it will be ignored.
        """
        self._require_authentication()
        return fetch_all(
            self.hs.crm.contacts.basic_api,
            properties=properties,
            associations=associations,
            archived=False,
        )

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
        )

    @keyword
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

    @keyword
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
