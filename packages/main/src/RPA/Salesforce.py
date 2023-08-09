import json
import logging
import sys
from collections import OrderedDict
from typing import Any, Union, Dict

import requests
from simple_salesforce import Salesforce as SimpleSalesforce
from simple_salesforce import SFType

from RPA.Tables import Table, Tables


class SalesforceAuthenticationError(Exception):
    "Error when authenticated Salesforce instance does not exist."


class SalesforceDataNotAnDictionary(Exception):
    "Error when parameter is not dictionary as expected."


class SalesforceDomainChangeError(Exception):
    "Error when changing domains while a session is active."


class Salesforce:
    """`Salesforce` is a library for accessing Salesforce using REST API.
    The library extends `simple-salesforce library`_.

    More information available at `Salesforce REST API Developer Guide`_.

    .. _Salesforce REST API Developer Guide:
        https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_what_is_rest_api.htm

    .. _simple-salesforce library:
        https://github.com/simple-salesforce/simple-salesforce

    **Dataloader**

    The keyword `execute_dataloader_import` can be used to mimic
    `Salesforce Dataloader`_ import behaviour.

    `input_object` can be given in different formats. Below is an example where
    input is in `RPA.Table` format in **method a** and list format in **method b**.

    .. _Salesforce Dataloader:
        https://developer.salesforce.com/docs/atlas.en-us.dataLoader.meta/dataLoader/data_loader.htm

    .. code-block:: robotframework

        *** Settings ***
        Library     RPA.Salesforce
        Library     RPA.Database
        Task Setup  Authorize Salesforce

        *** Tasks ***
        # Method a
        ${orders}=        Database Query Result As Table
        ...               SELECT * FROM incoming_orders
        ${status}=        Execute Dataloader Insert
        ...               ${orders}  ${mapping_dict}  Tilaus__c
        # Method b
        ${status}=        Execute Dataloader Insert
        ...               ${WORKDIR}${/}orders.json  ${mapping_dict}  Tilaus__c


    Example file **orders.json**

    .. code-block:: json

        [
            {
                "asiakas": "0015I000002jBLIQA2"
            },
            {
                "asiakas": "0015I000002jBLDQA2"
            },
        ]

    `mapping_object` describes how the input data fields are mapped into Salesforce
    object attributes. In the example, the mapping defines that `asiakas` attribute in the
    input object is mapped into `Tilaaja__c` attribute of `Tilaus__c` custom Salesforce object.

    .. code-block:: json

        {
            "Tilaus__c": {
                "asiakas": "Tilaaja__c"
            },
        }

    Object type could be, for example, `Tilaus__c`.

    **Salesforce object operations**

    Following operations can be used to manage Salesforce objects:

    * Get Salesforce Object By Id
    * Create Salesforce Object
    * Update Salesforce Object
    * Upsert Salesforce Object
    * Delete Salesforce Object
    * Get Salesforce Object Metadata
    * Describe Salesforce Object

    There are two ways to set the Salesforce domain. You can set the domain at time of
    library import or using the `Set Domain` keyword.

    There are several ways to declare a domain at time of library import:

    .. code-block:: robotframework

        *** Settings ***
        Library     RPA.Salesforce    sandbox=${TRUE}

    Or using the domain to your Salesforce My domain:

    .. code-block:: robotframework

        *** Settings ***
        Library     RPA.Salesforce    domain="robocorp"

    The domain can also be set using the keyword `Set Domain`:

    .. code-block:: robotframework

        *** Settings ***
        Library     RPA.Salesforce

        *** Tasks ***
        # Sets the domain for a sandbox environment
        Set Domain    sandbox

        # Sets the domain to a Salseforce My domain
        Set Domain    robocorp

        # Sets to domain to the default of 'login'
        Set Domain

    **Examples**

    **Robot Framework**

    .. code-block:: robotframework

        *** Settings ***
        Library     RPA.Salesforce
        Task Setup  Authorize Salesforce

        *** Variables ***
        ${ACCOUNT_NOKIA}    0015I000002jBLDQA2

        *** Tasks ***
        Change account details in Salesforce
            &{account}=      Get Salesforce Object By Id   Account  ${ACCOUNT_NOKIA}
            &{update_obj}=   Create Dictionary   Name=Nokia Ltd  BillingStreet=Nokia bulevard 1
            ${result}=       Update Salesforce Object  Account  ${ACCOUNT_NOKIA}  ${update_obj}

        *** Keywords ***
        Authorize Salesforce
            ${secrets}=     Get Secret   salesforce
            Auth With Token
            ...        username=${secrets}[USERNAME]
            ...        password=${secrets}[PASSWORD]
            ...        api_token=${secrets}[API_TOKEN]

    **Python**

    .. code-block:: python

        import pprint
        from RPA.Salesforce import Salesforce
        from RPA.Robocorp.Vault import FileSecrets

        pp = pprint.PrettyPrinter(indent=4)
        filesecrets = FileSecrets("secrets.json")
        secrets = filesecrets.get_secret("salesforce")

        sf = Salesforce()
        sf.auth_with_token(
            username=secrets["USERNAME"],
            password=secrets["PASSWORD"],
            api_token=secrets["API_TOKEN"],
        )
        nokia_account_id = "0015I000002jBLDQA2"
        account = sf.get_salesforce_object_by_id("Account", nokia_account_id)
        pp.pprint(account)
        billing_information = {
            "BillingStreet": "Nokia Bulevard 1",
            "BillingCity": "Espoo",
            "BillingPostalCode": "01210",
            "BillingCountry": "Finland",
        }
        result = sf.update_salesforce_object("Account", nokia_account_id, billing_information)
        print(f"Update result: {result}")

    """  # noqa: E501

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_DOC_FORMAT = "REST"

    account = {"Name": None, "Id": None}

    def __init__(self, sandbox: bool = False, domain: str = "login") -> None:
        self.logger = logging.getLogger(__name__)
        self.sf = None
        self.set_domain("sandbox" if sandbox else domain)
        self.session = None
        self.pricebook_name = None
        self.dataloader_success = []
        self.dataloader_errors = []

    def _require_authentication(self) -> None:
        if self.sf is None:
            raise SalesforceAuthenticationError("Authentication is not completed")

    def _require_no_session(self) -> None:
        if self.session_id or self.instance:
            raise SalesforceDomainChangeError(
                "Domains cannot be changed while a session is active"
            )

    @property
    def session_id(self):
        return self.sf.session_id if self.sf else None

    @property
    def instance(self):
        return self.sf.sf_instance if self.sf else None

    def set_domain(self, domain: str = "login") -> None:
        """Used to set the domain the `Auth With Token` keyword will use. To set
        the domain to 'test' or if using a sandbox environment use "sandbox" as the
        domain. If you have a Salsesforce My domain you may also input that name. If
        the `domain` argument is not used the default domain is "login".

        :param domain: "sandbox" or the name of the Salesforce My domain;
         if no argument provided defaults to "login"
        """
        self._require_no_session()
        self.domain = "test" if domain.lower() == "sandbox" else domain

    def get_domain(self) -> str:
        """Used to determine the current domain that has been set

        :returns: string of the currently set domain
        """
        return self.domain

    def auth_with_token(self, username: str, password: str, api_token: str) -> None:
        """Authorize to Salesforce with security token, username
        and password creating instance.

        :param username: Salesforce API username
        :param password: Salesforce API password
        :param api_token: Salesforce API security token
        """
        self.session = requests.Session()
        self.sf = SimpleSalesforce(
            username=username,
            password=password,
            security_token=api_token,
            domain=self.domain,
            session=self.session,
        )
        self.logger.debug("Salesforce session id: %s", self.session_id)

    def auth_with_connected_app(
        self,
        username: str,
        password: str,
        api_token: str,
        consumer_key: str,
        consumer_secret: str,
        embed_api_token: bool = False,
    ) -> None:
        """Authorize to Salesforce with security token, username,
        password, connected app key, and connected app secret
        creating instance.

        :param username: Salesforce API username
        :param password: Salesforce API password
        :param api_token: Salesforce API security token
        :param consumer_key: Salesforce connected app client ID
        :param consumer_secret: Salesforce connected app client secret
        :param embed_api_token: Embed API token to password (default: False)

        **Python**

        .. code-block:: python

            from RPA.Salesforce import Salesforce
            from RPA.Robocorp.Vault import Vault

            SF = Salesforce(domain="robocorp-testing-stuff.develop.my")
            VAULT = Vault()

            secrets = VAULT.get_secret("salesforce")
            SF.auth_with_connected_app(
                username=secrets["USERNAME"],
                password=secrets["PASSWORD"],
                api_token=secrets["API_TOKEN"],
                consumer_key=secrets["CONSUMER_KEY"],
                consumer_secret=secrets["CONSUMER_SECRET"],
            )

        **Robot Framework**

        .. code-block:: robotframework

            *** Settings ***
            Library  RPA.Salesforce   domain=robocop-testing-stuff.develop.my
            Library  RPA.Robocorp.Vault

            *** Tasks ***
            Authenticate to Salesforce using connected app
                ${secrets}=  Get Secret  salesforce

                Auth with connected app
                ...  username=${secrets}[USERNAME]
                ...  password=${secrets}[PASSWORD]
                ...  api_token=${secrets}[API_TOKEN]
                ...  consumer_key=${secrets}[CONSUMER_KEY]
                ...  consumer_secret=${secrets}[CONSUMER_SECRET]
        """
        self.session = requests.Session()
        request_data = {
            "username": username,
            "password": f"{password}{api_token}" if embed_api_token else password,
            "client_id": consumer_key,
            "client_secret": consumer_secret,
            "grant_type": "password",
        }
        response = requests.post(
            f"https://{self.domain}.salesforce.com/services/oauth2/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=request_data,
        )
        try:
            response.raise_for_status()
            result = response.json()

            if result.get("access_token"):
                self.sf = SimpleSalesforce(
                    instance_url=result["instance_url"],
                    session_id=result["access_token"],
                    domain=self.domain,
                    session=self.session,
                )
                self.logger.debug("Salesforce session id: %s", self.session_id)
            else:
                error_message = (
                    "Could not get access token\n"
                    f"Details: {response.status_code} {response.text}"
                )
                raise SalesforceAuthenticationError(error_message)
        except requests.exceptions.HTTPError as err:
            error_message = (
                f"{str(err)}\nDetails: {response.status_code} {response.text}"
            )
            raise SalesforceAuthenticationError(error_message) from err

    def execute_apex(
        self, apex: str, apex_data: Dict = None, apex_method: str = "POST", **kwargs
    ):
        """Execute APEX operation.

        The APEX classes can be added via Salesforce Developer console
        (from menu: File > New > Apex Class).

        Permissions for the APEX classes can be set via Salesforce Setup
        (Apex Classes -> Security).

        :param apex: endpoint of the APEX operation
        :param apex_data: data to be sent to the APEX operation
        :param apex_method: operation method
        :param kwargs: additional arguments to be passed to the APEX request
        :return: result of the APEX operation

        **Python**

        .. code-block:: python

            from RPA.Salesforce import Salesforce

            SF = Salesforce(domain="robocorp-testing-stuff.develop.my")
            # authenticate to Salesforce
            SF.execute_apex(apex="MyClass", apex_data={"data": "value"})
            result = SF.execute_apex(
                apex="getAccount/?id=0017R00002xmXB1QAM",
                apex_method="GET")

        **Robot Framework**

        .. code-block:: robotframework

            *** Settings ***
            Library  RPA.Salesforce   domain=robocop-testing-stuff.develop.my

            *** Tasks ***
            Executing APEX operations
                # Authenticate to Salesforce

                &{apex_data}=  Create Dictionary  data=value
                ${result}=     Execute APEX  MyClass  apex_data=${apex_data}
                ${result}=     Execute APEX
                ...  apex=getAccount/?id=0017R00002xmXB1QAM
                ...  apex_method=GET
        """
        return self.sf.apexecute(apex, method=apex_method, data=apex_data, **kwargs)

    def _get_values(self, node, prefix=None, data=None):
        if data is None:
            data = []
        if prefix is None:
            prefix = []

        if isinstance(node, OrderedDict):
            for k, v in node.items():
                if k != "attributes":
                    prefix.append(k)
                    self._get_values(v, prefix, data)
                    prefix = prefix[:-1]
        else:
            data.append((sys.intern(".".join(prefix)), node))

        return data

    def _generate_table_from_SFDC_API_query(
        self, result: dict, start: int = 0, limit: int = 0
    ) -> Table:
        records = (
            result["records"][start:]
            if limit == 0
            else result["records"][start : start + limit]
        )
        if len(records) == 0:
            return Tables().create_table()

        cols = [col for col, _ in self._get_values(records[0])]
        table = Tables().create_table(columns=cols)

        for row in records:
            values = self._get_values(row)
            table.append_row(row=dict(values))

        return table

    def salesforce_query(
        self, sql_string: str, as_table: bool = False
    ) -> Union[dict, Table]:
        """Perform SQL query and return result as `dict` or `Table`.

        :param sql_string: SQL clause to perform.
        :param as_table: Set to `True` if the result should be of `RPA.Tables.Table`
            type. (dictionary is returned by default)
        :returns: Result of the SQL query.
        """
        self._require_authentication()
        result: dict = self.sf.query_all(sql_string)
        if not as_table:
            return result

        return self._generate_table_from_SFDC_API_query(result)

    def salesforce_query_result_as_table(self, sql_string: str) -> Table:
        """Shorthand for ``Salesforce Query    ${sql_string}    as_table=${True}``.

        :param sql_string: SQL clause to perform.
        :returns: Result of the SQL query as `RPA.Tables.Table`.
        """
        return self.salesforce_query(sql_string, as_table=True)

    def set_account(self, account_name: str = "", account_id: str = "") -> bool:
        """Set account name and id by giving either parameter.

        Can be used together with keywords:
            - get_opportunity_id
            - create_new_opportunity

        :param account_name: string, defaults to ""
        :param account_id: string, defaults to ""
        :return: True if account was found from Salesforce, else False
        """
        result = self.salesforce_query(
            f"SELECT Id, Name FROM Account WHERE Name = '{account_name}' "
            f"or Id = '{account_id}'"
        )
        if result["totalSize"] == 1:
            self.account["Id"] = result["records"][0]["Id"]
            self.account["Name"] = result["records"][0]["Name"]
            self.logger.debug("Found account: %s", self.account)
            return True
        else:
            self.account = {"Name": None, "Id": None}
            return False

    def get_pricebook_entries(self) -> dict:
        """Get all pricebook entries.

        :return: query result
        """
        return self.salesforce_query("SELECT Id, Name FROM Pricebook2")

    def get_opportunity_id(self, opportunity_name: str) -> Any:
        """Get ID of an Opportunity linked to set account.

        :param opportunity_name: opportunity to query
        :return: Id of the opportunity or False
        """
        sql_query = (
            f"SELECT Id, AccountId FROM Opportunity WHERE Name = '{opportunity_name}'"
        )

        if self.account["Id"] is not None:
            sql_query += " AND AccountId = '%s'" % self.account["Id"]

        result = self.salesforce_query(sql_query)
        if result["totalSize"] == 1:
            return result["records"][0]["Id"]
        return False

    def get_pricebook_id(self, pricebook_name: str) -> Any:
        """Get ID of a pricelist.

        Returns False if unique Id is not found.

        :param pricebook_name: pricelist to query
        :return: Id of the pricelist or False
        """
        result = self.salesforce_query(
            f"SELECT Id FROM Pricebook2 WHERE Name = '{pricebook_name}'"
        )
        if result["totalSize"] == 1:
            return result["records"][0]["Id"]
        return False

    def get_products_in_pricelist(self, pricebook_name: str) -> dict:
        """Get all products in a pricelist.

        :param pricebook_name: pricelist to query
        :return: products in dictionary
        """
        result = self.salesforce_query(
            f"SELECT PriceBook2.Name, Product2.Id, Product2.Name, UnitPrice, Name "
            f"FROM PricebookEntry WHERE PriceBook2.Name = '{pricebook_name}'"
        )
        products = {}
        for item in result["records"]:
            product_name = item["Product2"]["Name"]
            pricebook_entry_id = item["attributes"]["url"].split("/")[-1]
            product_unitprice = item["UnitPrice"]
            products[product_name] = {
                "pricebook_entry_id": pricebook_entry_id,
                "unit_price": product_unitprice,
            }
        return products

    def set_pricebook(self, pricebook_name: str) -> None:
        """Sets Pricebook to be used in Salesforce operations.

        :param pricebook_name: pricelist to use
        """
        self.pricebook_name = pricebook_name

    def add_product_into_opportunity(
        self,
        product_name: str,
        quantity: int,
        opportunity_id: str = None,
        pricebook_name: str = None,
        custom_total_price: float = None,
    ) -> bool:
        """Add Salesforce Product into Opportunity.

        :param product_name: type of the product in the Pricelist
        :param quantity: number of products to add
        :param opportunity_id: identifier of Opportunity, default None
        :param pricebook_name: name of the pricelist, default None
        :param custom_total_price: price that overrides quantity and product price,
            default None
        :return: True is operation is successful or False
        """
        self._require_authentication()
        if opportunity_id is None:
            return False
        if pricebook_name:
            products = self.get_products_in_pricelist(pricebook_name)
        else:
            products = self.get_products_in_pricelist(self.pricebook_name)
        sfobject = SFType("OpportunityLineItem", self.session_id, self.instance)
        if product_name in products.keys():
            data_object = {
                "OpportunityId": opportunity_id,
                "PricebookEntryId": products[product_name]["pricebook_entry_id"],
                "Quantity": int(quantity),
                "TotalPrice": int(quantity) * products[product_name]["unit_price"],
            }
            if custom_total_price:
                data_object["TotalPrice"] = float(custom_total_price)
            result = sfobject.create(data_object)
            if result and bool(result["success"]):
                return True
        return False

    def create_new_opportunity(
        self,
        close_date: str,
        opportunity_name: str,
        stage_name: str = "Closed Won",
        account_name: str = None,
    ) -> Any:
        """Create Salesforce Opportunity object.

        :param close_date: closing date for the Opportunity, format 'YYYY-MM-DD'
        :param opportunity_name: as string
        :param stage_name: needs to be one of the defined stages,
            defaults to "Closed Won"
        :param account_name: by default uses previously set account, defaults to None
        :return: created opportunity or False
        """
        self._require_authentication()
        # "2020-04-03"
        if account_name:
            self.set_account(account_name=account_name)
        if self.account["Id"] is None:
            return False

        sfobject = SFType("Opportunity", self.session_id, self.instance)
        result = sfobject.create(
            {
                "CloseDate": close_date,
                "Name": opportunity_name,
                "StageName": stage_name,
                "Type": "Initial Subscription",
                "AccountId": self.account["Id"],
            }
        )
        self.logger.debug("create new opportunity: %s", result)
        return result.get("id") or False

    def read_dictionary_from_file(self, mapping_file: str) -> dict:
        """Read dictionary from file.

        :param mapping_file: path to the file
        :return: file content as dictionary
        """
        mapping = None
        with open(mapping_file, "r", encoding="utf-8") as mf:
            mapping = json.loads(mf.read())
        return mapping

    def _get_input_iterable(self, input_object):
        input_iterable = {}
        if isinstance(input_object, dict):
            input_iterable = input_object.items
        elif isinstance(input_object, Table):
            input_iterable = input_object.iter_dicts
        elif isinstance(input_object, list):
            input_table = Table(input_object)
            input_iterable = input_table.iter_dicts
        else:
            input_dict = self.read_dictionary_from_file(input_object)
            if isinstance(input_dict, list):
                input_table = Table(input_dict)
                input_iterable = input_table.iter_dicts
            else:
                input_iterable = input_dict
        return input_iterable

    def execute_dataloader_insert(
        self, input_object: Any, mapping_object: Any, object_type: str
    ) -> bool:
        """Keyword mimics Salesforce Dataloader 'insert' behaviour by taking
        in a `input_object`representing dictionary of data to input into Salesforce,
        a `mapping_object` representing dictionary mapping the input keys into
        Salesforce keys, an `object_type` representing Salesforce object which
        Datahandler will handle with `operation` type.

        Stores operation successes into `Salesforce.dataloader_success` array.
        Stores operation errors into `Salesforce.dataloader_errors`.

        These can be retrieved with keywords `get_dataloader_success_table` and
        `get_dataloader_error_table` which return corresponding data as
        `RPA.Table`.

        :param input_object: filepath or list of dictionaries
        :param mapping_object: filepath or dictionary
        :param object_type: Salesforce object type
        :return: True if operation is successful
        """
        self._require_authentication()
        if not isinstance(mapping_object, (dict, Table)):
            mapping_dict = self.read_dictionary_from_file(mapping_object)
        else:
            mapping_dict = mapping_object

        input_iterable = self._get_input_iterable(input_object)
        sfobject = SFType(object_type, self.session_id, self.instance)
        self.dataloader_success = []
        self.dataloader_errors = []
        for item in input_iterable():
            data_object = {}
            for key, value in mapping_dict[object_type].items():
                data_object[value] = item[key]
            result = sfobject.create(data_object)
            if result["success"]:
                data_status = {"result_id": result["id"]}
                self.dataloader_success.append({**data_status, **item})
            else:
                data_status = {"message": "failed"}
                self.dataloader_errors.append({**data_status, **item})
        return True

    def get_dataloader_success_table(self) -> Table:
        "Return Dataloader success entries as `RPA.Table`"
        return Table(self.dataloader_success)

    def get_dataloader_error_table(self) -> Table:
        "Return Dataloader error entries as `RPA.Table`"
        return Table(self.dataloader_errors)

    def get_salesforce_object_by_id(self, object_type: str, object_id: str) -> dict:
        """Get Salesforce object by id and type.

        :param object_type: Salesforce object type
        :param object_id: Salesforce object id
        :return: dictionary of object attributes
        """
        self._require_authentication()
        sfobject = SFType(object_type, self.session_id, self.instance)
        return sfobject.get(object_id)

    def create_salesforce_object(self, object_type: str, object_data: Any) -> dict:
        """Create Salesforce object by type and data.

        :param object_type: Salesforce object type
        :param object_data: Salesforce object data
        :raises SalesforceDataNotAnDictionary: when `object_data` is not dictionary
        :return: resulting object as dictionary
        """
        self._require_authentication()
        if not isinstance(object_data, dict):
            raise SalesforceDataNotAnDictionary(object_data)
        salesforce_object = SFType(object_type, self.session_id, self.instance)
        result = salesforce_object.create(object_data)
        return dict(result)

    def update_salesforce_object(
        self, object_type: str, object_id: str, object_data: Any
    ) -> bool:
        """Update Salesfoce object by type, id and data.

        :param object_type: Salesforce object type
        :param object_id: Salesforce object id
        :param object_data: Salesforce object data
        :raises SalesforceDataNotAnDictionary: when `object_data` is not dictionary
        :return: True if successful
        """
        self._require_authentication()
        if not isinstance(object_data, dict):
            raise SalesforceDataNotAnDictionary(object_data)
        salesforce_object = SFType(object_type, self.session_id, self.instance)
        result_code = salesforce_object.update(object_id, object_data)
        return result_code == 204

    def upsert_salesforce_object(
        self, object_type: str, object_id: str, object_data: Any
    ) -> bool:
        """Upsert Salesfoce object by type, id and data.

        :param object_type: Salesforce object type
        :param object_id: Salesforce object id
        :param object_data: Salesforce object data
        :raises SalesforceDataNotAnDictionary: when `object_data` is not dictionary
        :return: True if successful
        """
        self._require_authentication()
        if not isinstance(object_data, dict):
            raise SalesforceDataNotAnDictionary(object_data)
        salesforce_object = SFType(object_type, self.session_id, self.instance)
        result_code = salesforce_object.upsert(object_id, object_data)
        return result_code == 204

    def delete_salesforce_object(self, object_type: str, object_id: str) -> bool:
        """Delete Salesfoce object by type and id.

        :param object_type: Salesforce object type
        :param object_id: Salesforce object id
        :return: True if successful
        """
        self._require_authentication()
        salesforce_object = SFType(object_type, self.session_id, self.instance)
        result_code = salesforce_object.delete(object_id)
        return result_code == 204

    def get_salesforce_object_metadata(self, object_type: str) -> dict:
        """Get Salesfoce object metadata by type.

        :param object_type: Salesforce object type
        :return: object metadata as dictionary
        """
        self._require_authentication()
        salesforce_object = SFType(object_type, self.session_id, self.instance)
        return dict(salesforce_object.metadata())

    def describe_salesforce_object(self, object_type: str) -> dict:
        """Get Salesfoce object description by type.

        :param object_type: Salesforce object type
        :return: object description as dictionary
        """
        self._require_authentication()
        salesforce_object = SFType(object_type, self.session_id, self.instance)
        return dict(salesforce_object.describe())
