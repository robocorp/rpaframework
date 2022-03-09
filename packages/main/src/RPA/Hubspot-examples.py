import logging
from os import access
import requests

from pprint import pprint

from hubspot import HubSpot as HubSpotApi
from hubspot.utils.objects import fetch_all
from hubspot.crm.contacts import PublicObjectSearchRequest as ContactSearchRequest


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
        self, properties: list[str] = None, associations: list[str] = None
    ) -> list[dict]:
        """Returns a list of available contacts. A list of properties
        and associtations can be provided and will be included in the
        returned list.

        :param properties: a list of strings representing properties of
        the HubSpot Contacts. If such a property
        does not exist
        """

        return fetch_all(
            self.hs.crm.contacts.basic_api,
            properties=properties,
            associations=associations,
            archived=False,
        )

    def search_for_contacts(self):
        search_request = ContactSearchRequest(
            filter_groups=[
                {
                    "filters": [
                        {
                            "value": "emailmaria@hubspot.com",
                            "propertyName": "email",
                            "operator": "EQ",
                        }
                    ]
                }
            ],
            limit=0,
            after=0,
        )
        api_response = client.crm.contacts.search_api.do_search(
            public_object_search_request=search_request
        )


hs = HubSpot()
hs.auth_with_token("pat-na1-be671d1a-6024-49fa-a62e-646bce847f2e")
pprint(hs.list_contacts())

# List all contacts (paginated)
import hubspot
from pprint import pprint
from hubspot.crm.contacts import ApiException

client = hubspot.Client.create(api_key="YOUR_HUBSPOT_API_KEY")

try:
    api_response = client.crm.contacts.basic_api.get_page(limit=10, archived=False)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling basic_api->get_page: %s\n" % e)


# Search for specific contacts (via filter JSON in body)
import hubspot
from pprint import pprint
from hubspot.crm.contacts import PublicObjectSearchRequest, ApiException

client = hubspot.Client.create(api_key="YOUR_HUBSPOT_API_KEY")

public_object_search_request = PublicObjectSearchRequest(
    filter_groups=[
        {"filters": [{"value": "string", "propertyName": "string", "operator": "EQ"}]}
    ],
    sorts=["string"],
    query="string",
    properties=["string"],
    limit=0,
    after=0,
)
try:
    api_response = client.crm.contacts.search_api.do_search(
        public_object_search_request=public_object_search_request
    )
    pprint(api_response)
except ApiException as e:
    print("Exception when calling search_api->do_search: %s\n" % e)
