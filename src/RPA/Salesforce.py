from functools import wraps
import json
import logging
import requests

from simple_salesforce import Salesforce as SimpleSalesforce
from simple_salesforce import SFType

from RPA.Tables import Table


def sf_instance_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if args[0].sf is None:
            raise SalesforceAuthenticationError("Authentication is not completed")
        return f(*args, **kwargs)

    return wrapper


class SalesforceAuthenticationError(Exception):
    "Error when authenticated Salesforce instance does not exist."


class SalesforceDataNotAnDictionary(Exception):
    "Error when parameter is not dictionary as expected."


class Salesforce:
    """Library for accessing Salesforce using REST API.
    """

    account = {"Name": None, "Id": None}

    def __init__(self, sandbox=False):
        self.logger = logging.getLogger(__name__)
        self.sf = None
        self.domain = "test" if sandbox else "login"
        self.session = None
        self.pricebook_name = None
        self.dataloader_success = []
        self.dataloader_errors = []

    @property
    def session_id(self):
        return self.sf.session_id if self.sf else None

    @property
    def instance(self):
        return self.sf.sf_instance if self.sf else None

    def auth_with_token(self, username, password, api_token):
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
        self.logger.debug(f"Salesforce session id: {self.session_id}")

    @sf_instance_required
    def salesforce_query(self, sql_string):
        """Perform SQL query.

        :param sql_string: SQL clause to perform
        :return: result of the SQL query
        """
        return self.sf.query(sql_string)

    def salesforce_query_result_as_table(self, sql_string):
        """Perform SQL query and return result as `RPA.Table`.

        :param sql_string: SQL clause to perform
        :return: result of the SQL query as Table
        """

        results = self.salesforce_query(sql_string)
        table = Table(results["records"])
        table.delete_columns(["attributes"])
        return table

    def set_account(self, account_name="", account_id=""):
        """Set account name and id by giving either parameter.

        Can be used together with keywords:
            - get_opportunity_id
            - create_new_opportunity

        :param account_name: string, defaults to ""
        :param account_id: string, defaults to ""
        :return: True if account was found from Salesforce, else False
        """
        result = self.salesforce_query(
            f"SELECT Id, Name FROM Account "
            f"WHERE Name = '{account_name}' or Id = '{account_id}'"
        )
        if result["totalSize"] == 1:
            self.account["Id"] = result["records"][0]["Id"]
            self.account["Name"] = result["records"][0]["Name"]
            self.logger.debug(f"Found account: {self.account}")
            return True
        else:
            self.account = {"Name": None, "Id": None}
            return False

    def get_pricebook_entries(self):
        """Get all pricebook entries.

        :return: query result
        """
        return self.salesforce_query("SELECT Id, Name FROM Pricebook2")

    def get_opportunity_id(self, opportunity_name):
        """Get ID of an Opportunity linked to set account.

        :param opportunity_name: opportunity to query
        :return: Id of the opportunity or False
        """
        sql_query = (
            f"SELECT Id, AccountId FROM Opportunity WHERE Name = '%s'"
            % opportunity_name
        )

        if self.account["Id"] is not None:
            sql_query += " AND AccountId = '%s'" % self.account["Id"]

        result = self.salesforce_query(sql_query)
        if result["totalSize"] == 1:
            return result["records"][0]["Id"]
        return False

    def get_pricebook_id(self, pricebook_name):
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

    def get_products_in_pricelist(self, pricebook_name):
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
            print(f"Name               : {product_name}")
            print(f"UnitPrice          : {product_unitprice}")
            print(f"Pricebook entry id : {pricebook_entry_id}")
        return products

    def set_pricebook(self, pricebook_name):
        """Sets Pricebook to be used in Salesforce operations.

        :param pricebook_name: pricelist to use
        """
        self.pricebook_name = pricebook_name

    @sf_instance_required
    def add_product_into_opportunity(
        self,
        product_name,
        quantity,
        opportunity_id=False,
        pricebook_name=False,
        custom_total_price=False,
    ):
        """Add Salesforce Product into Opportunity.

        :param product_name: type of the product in the Pricelist
        :param quantity: number of products to add
        :param opportunity_id: identifier of Opportunity, defaults to False
        :param pricebook_name: name of the pricelist, defaults to False
        :param custom_total_price: price that overrides quantity and product price,
            defaults to False
        :return: True is operation is successful or False
        """
        if opportunity_id is False:
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

    @sf_instance_required
    def create_new_opportunity(
        self, close_date, opportunity_name, stage_name="Closed Won", account_name=False
    ):
        """Create Salesforce Opportunity object.

        :param close_date: closing date for the Opportunity, format 'YYYY-MM-DD'
        :param opportunity_name: as string
        :param stage_name: needs to be one of the defined stages,
            defaults to "Closed Won"
        :param account_name: by default uses previously set account, defaults to False
        :return: created opportunity or False
        """
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
        self.logger.debug(f"create new opportunity: {result}")
        return result.get("id") or False

    def read_dictionary_from_file(self, mapping_file):
        """Read dictionary from file.

        :param mapping_file: path to the file
        :return: file content as dictionary
        """
        mapping = None
        with open(mapping_file, "r") as mf:
            mapping = json.loads(mf.read())
        return mapping

    def _get_input_iterable(self, input_object):
        input_iterable = dict()
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

    @sf_instance_required
    def execute_dataloader_insert(self, input_object, mapping_object, object_type):
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

    def get_dataloader_success_table(self):
        "Return Dataloader success entries as `RPA.Table`"
        return Table(self.dataloader_success)

    def get_dataloader_error_table(self):
        "Return Dataloader error entries as `RPA.Table`"
        return Table(self.dataloader_errors)

    @sf_instance_required
    def get_salesforce_object_by_id(self, object_type, object_id):
        """Get Salesforce object by id and type.

        :param object_type: Salesforce object type
        :param object_id: Salesforce object id
        :return: dictionary of object attributes
        """
        sfobject = SFType(object_type, self.session_id, self.instance)
        return sfobject.get(object_id)

    @sf_instance_required
    def create_salesforce_object(self, object_type, object_data):
        """Create Salesforce object by type and data.

        :param object_type: Salesforce object type
        :param object_data: Salesforce object data
        :raises SalesforceDataNotAnDictionary: when `object_data` is not dictionary
        :return: resulting object as dictionary
        """
        if not isinstance(object_data, dict):
            raise SalesforceDataNotAnDictionary(object_data)
        salesforce_object = SFType(object_type, self.session_id, self.instance)
        result = salesforce_object.create(object_data)
        return dict(result)

    @sf_instance_required
    def update_salesforce_object(self, object_type, object_id, object_data):
        """Update Salesfoce object by type, id and data.

        :param object_type: Salesforce object type
        :param object_id: Salesforce object id
        :param object_data: Salesforce object data
        :raises SalesforceDataNotAnDictionary: when `object_data` is not dictionary
        :return: True if successful
        """
        if not isinstance(object_data, dict):
            raise SalesforceDataNotAnDictionary(object_data)
        salesforce_object = SFType(object_type, self.session_id, self.instance)
        result_code = salesforce_object.update(object_id, object_data)
        return result_code == 204

    @sf_instance_required
    def upsert_salesforce_object(self, object_type, object_id, object_data):
        """Upsert Salesfoce object by type, id and data.

        :param object_type: Salesforce object type
        :param object_id: Salesforce object id
        :param object_data: Salesforce object data
        :raises SalesforceDataNotAnDictionary: when `object_data` is not dictionary
        :return: True if successful
        """
        if not isinstance(object_data, dict):
            raise SalesforceDataNotAnDictionary(object_data)
        salesforce_object = SFType(object_type, self.session_id, self.instance)
        result_code = salesforce_object.upsert(object_id, object_data)
        return result_code == 204

    @sf_instance_required
    def delete_salesforce_object(self, object_type, object_id):
        """Delete Salesfoce object by type and id.

        :param object_type: Salesforce object type
        :param object_id: Salesforce object id
        :return: True if successful
        """
        salesforce_object = SFType(object_type, self.session_id, self.instance)
        result_code = salesforce_object.delete(object_id)
        return result_code == 204

    @sf_instance_required
    def get_salesforce_object_metadata(self, object_type):
        """Get Salesfoce object metadata by type.

        :param object_type: Salesforce object type
        :return: object metadata as dictionary
        """
        salesforce_object = SFType(object_type, self.session_id, self.instance)
        return dict(salesforce_object.metadata())

    @sf_instance_required
    def describe_salesforce_object(self, object_type):
        """Get Salesfoce object description by type.

        :param object_type: Salesforce object type
        :return: object description as dictionary
        """
        salesforce_object = SFType(object_type, self.session_id, self.instance)
        return dict(salesforce_object.describe())
