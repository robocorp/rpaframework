from ast import keyword
import logging
import re
from os import access
from typing import List, Dict
from exchangelib import Contact

from pprint import pprint

from robot.api.deco import keyword, library

from hubspot import HubSpot as HubSpotApi
from hubspot.utils.objects import fetch_all
from hubspot.crm.objects import PublicObjectSearchRequest as ObjectSearchRequest


class HubSpotAuthenticationError(Exception):
    "Error when authenticated HubSpot instance does not exist."


class HubSpotObjectTypeError(Exception):
    "Error when the object type provided does not exist."


@library(scope="Global", doc_format="REST")
class HubSpot:
    """`HubSpot` is a library for accessing HubSpot using REST API."""

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

    def auth_with_token(self, access_token: str) -> None:
        """Authorize to HubSpot with Private App access token.

        :param access_token: The access token created for the Private App
        in your HubSpot account.
        """
        self.hs = HubSpotApi(access_token=access_token)

    @keyword
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

    def _search_objects(
        self,
        object_type: str,
        search: List[dict] = None,
        string_query: str = "",
        properties: List[str] = None,
    ) -> Dict:
        self._require_authentication()
        if search:
            search_request = ObjectSearchRequest(
                filter_groups=search, properties=properties
            )
        elif string_query:
            search_request = ObjectSearchRequest(
                query=string_query, properties=properties
            )
        else:
            raise ValueError("Search or string_query must have a value.")

        return fetch_all(
            self.hs.crm.objects.search_api.do_search(
                object_type, public_object_search_request=search_request
            )
        )

    def _get_all_schemas(self) -> List[Dict]:
        self._require_authentication()
        if self.schemas is None:
            self.schemas = self.hs.crm.schemas.core_api.get_all()
        return self.schemas

    def _get_custom_object_schema(self, name: str) -> Dict:
        self._require_authentication()
        for s in self._get_all_schemas():
            if (
                s["name"] == name.lower()
                or s["labels"]["singular"].lower() == name.lower()
                or s["labels"]["plural"].lower() == name.lower()
            ):
                return s

    def _get_custom_object_id(self, name: str) -> str:
        self._require_authentication()
        schema = self._get_custom_object_schema(self._validate_object_type(name))
        return schema["objectTypeId"]

    def _singularize_object(self, name: str) -> str:
        if self.singular_map is None:
            self.singular_map = self.BUILTIN_SINGULAR_MAP
            schemas = self._get_all_schemas()
            labels = [s["labels"] for s in schemas]
            self.singular_map.update({l["plural"]: l["singular"] for l in labels})
            self.singular_map.update(
                {s["objectTypeId"]: s["objectTypeId"] for s in schemas}
            )
        return self.singular_map[self._validate_object_type(name)]

    def _pluralize_object(self, name: str) -> str:
        if self.plural_map is None:
            self.plural_map = self.BUILTIN_PLURAL_MAP
            schemas = self._get_all_schemas()
            labels = [s["labels"] for s in schemas]
            self.plural_map.update({l["singular"]: l["plural"] for l in labels})
            self.plural_map.update(
                {s["objectTypeId"]: s["objectTypeId"] for s in schemas}
            )
        return self.plural_map[self._validate_object_type(name)]

    def _validate_object_type(self, name: str) -> str:
        """Validates the provided `name` against the built in list of
        object types and the list of custom object type schemas. Returns
        the validated custom object ID or name in lower case.
        Raises `HubSpotObjectTypeError` if `name` cannot be validated.
        """
        valid_names = list(self.BUILTIN_SINGULAR_MAP.keys())
        valid_names.extend([s["objectTypeId"] for s in self._get_all_schemas()])
        valid_names.extend([s["name"] for s in self._get_all_schemas()])
        if name.lower() in valid_names:
            return name.lower()
        else:
            raise HubSpotObjectTypeError(f"Object type {name} does not exist.")

    @keyword
    def search_for_objects(
        self,
        object_type: str,
        search: List[dict] = None,
        string_query: str = "",
        properties: List[str] = None,
    ) -> Dict:
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

        Search criteria must be pased as a list of dictionaries. For
        example, to search for contacts with the first name of "Alice",
        you would construct the `search` criteria like so:

        .. code-block:: python

            alice_search = {
                "filterGroups": [
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
            }

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

            combination_search = {
                "filterGroups": [
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
            }

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

        # TODO: Consider creating separate keywords for search and query so that
        # search can be performed with natural language in RFW, like:
        #   Search For Objects    contacts    firstname    EQ    Alice
        self._require_authentication()

        return self._search_objects(
            self._pluralize_object(self._validate_object_type(object_type)),
            search,
            string_query,
            properties,
        )

    def list_associations(
        self, object_type: str, object_id: str, to_object_type: str
    ) -> List[Dict]:
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

        return fetch_all(
            self.hs.crm.objects.associations_api.get_all(
                self._validate_object_type(self._singularize_object(object_type)),
                object_id,
                self._validate_object_type(self._singularize_object(to_object_type)),
            )
        )

    def get_object(
        self,
        object_type: str,
        object_id: str,
        id_property: str = None,
        properties: List[str] = None,
        associations: List[str] = None,
    ) -> Dict:
        """Reads a single object of `object_type` from HubSpot with the
        provided `object_id`. The objects can be found using an
        alternate ID by providing the name of that HubSpot property
        which contains the unique identifier to `id_property`.

        A list of property names can be provided to `properties`
        and they will be included in the returned object. Nonexistent
        properties are ignored.

        A list of object types can be provided to `associations` and all
        object IDs associated to the returned object of that type will
        be returned as well.

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

        # TODO: The object API may not be able to handle the properties and associations kwargs.
        return self.hs.crm.objects.basic_api.get_by_id(
            self._validate_object_type(object_type),
            object_id,
            properties=properties,
            associations=associations,
        )
