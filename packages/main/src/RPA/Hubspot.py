import logging
from os import access
from typing import List, Dict
from exchangelib import Contact
import requests

from pprint import pprint

from hubspot import HubSpot as HubSpotApi
from hubspot.utils.objects import fetch_all
from hubspot.crm.contacts import PublicObjectSearchRequest as ContactSearchRequest
from hubspot.crm.companies import PublicObjectSearchRequest as CompanySearchRequest


class HubSpotAuthenticationError(Exception):
    "Error when authenticated HubSpot instance does not exist."


class HubSpot:

    ROBOT_LIBRARY_SCOPE = "Global"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.hs = None

    def _require_authentication(self) -> None:
        if self.hs is None:
            raise HubSpotAuthenticationError("Authentication was not completed.")

    def auth_with_token(self, access_token: str) -> None:
        """Authorize to HubSpot with Private App access token.

        :param access_token: The access token created for the Private App
        in your HubSpot account.
        """
        self.hs = HubSpotApi(access_token=access_token)

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

    def search_for_contacts(
        self,
        search: List[dict] = None,
        string_query: str = "",
        properties: List[str] = None,
    ) -> Dict:
        """Returns a list of contacts based on the provided `search` criteria.
        For example, to search for contacts with the first name of "Alice",
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

        You can can additional properties for the objects by defining
        them with `properties`. If a requested property does not exist,
        it will be ignored.

        :param search: the search object to use as search criteria.
        :param string_query: a string query can be provided instead of a
        search object which is used as a text-based search in all default
        searchable properties in Hubspot.
        :param properties: a list of strings representing return properties
        to be included in the returned data.
        :return: A list of contacts.
        """
        # TODO: Consider combining all searches into one keyword with a
        # search type parameter so it would work like
        #   Search for  contacts  search_criteria`

        # TODO: Consider creating separate keywords for search and query so that
        # search can be performed with natural language in RFW.
        self._require_authentication()
        if search:
            search_request = ContactSearchRequest(
                filter_groups=search, properties=properties
            )
        elif string_query:
            search_request = ContactSearchRequest(
                query=string_query, properties=properties
            )
        else:
            raise ValueError("Search or string_query must have a value.")

        return self.hs.crm.contacts.search_api.do_search(
            public_object_search_request=search_request
        )

    def search_for_companies(
        self,
        search: List[dict] = None,
        string_query: str = "",
        properties: List[str] = None,
    ) -> Dict:
        """Returns a list of companies based on the provided `search` criteria.
        See keyword `Search For Contacts` for complete description of how
        to create the search object.

        :param search: the search object to use as search criteria.
        :param string_query: a string query can be provided instead of a
        search object which is used as a text-based search in all default
        searchable properties in Hubspot.
        :param properties: a list of strings representing return properties
        to be included in the returned data.
        :return: A list of companies.
        """

        # TODO: Consider creating separate keywords for search and query so that
        # search can be performed with natural language in RFW.
        self._require_authentication()
        if search:
            search_request = CompanySearchRequest(
                filter_groups=search, properties=properties
            )
        elif string_query:
            search_request = CompanySearchRequest(
                query=string_query, properties=properties
            )
        else:
            raise ValueError("Search or string_query must have a value.")

        return self.hs.crm.companies.search_api.do_search(
            public_object_search_request=search_request
        )
