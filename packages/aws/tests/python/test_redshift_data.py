from time import sleep
import boto3
import pytest
import os
from moto import mock_redshift
from moto.moto_api import state_manager
import importlib


def custom_lazy_load(
    module_name,
    element,
    boto3_name=None,
    backend=None,
    warn_repurpose=False,
    use_instead=None,
):
    def f(*args, **kwargs):
        if warn_repurpose:
            import warnings

            warnings.warn(
                f"Module {element} has been deprecated, and will be repurposed in a later release. "
                "Please see https://github.com/spulec/moto/issues/4526 for more information."
            )
        if use_instead:
            import warnings

            used, recommended = use_instead
            warnings.warn(
                f"Module {used} has been deprecated, and will be removed in a later release. Please use {recommended} instead. "
                "See https://github.com/spulec/moto/issues/4526 for more information."
            )
        module = importlib.import_module(module_name)
        return getattr(module, element)(*args, **kwargs)

    setattr(f, "name", module_name.replace(".", ""))
    setattr(f, "element", element)
    setattr(f, "boto3_name", boto3_name or f.name)
    setattr(f, "backend", backend or f"{f.name}_backends")
    return f


mock_redshiftdata = custom_lazy_load(
    "custom_redshiftdata", "mock_redshiftdata", boto3_name="redshift-data"
)

# Moto mocks only ever return one result set, so SQL does not need to be
# defined properly.
TEST_SQL = """
    select * from dev
"""
DEFAULT_REGION = "eu-west-1"
TEST_CLUSTER = "virtual-test-1"
TEST_USER = "testadmin"
TEST_PASSWORD = "Password1"


@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = DEFAULT_REGION


@pytest.fixture(scope="function")
def redshift(aws_credentials):
    with mock_redshift():
        yield boto3.client("redshift", region_name=DEFAULT_REGION)


@mock_redshift
@mock_redshiftdata
def test_execute_statement(redshift):
    redshift.create_cluster(
        ClusterIdentifier=TEST_CLUSTER,
        NodeType="dc1.large",
        MasterUsername=TEST_USER,
        MasterUserPassword=TEST_PASSWORD,
        LoadSampleData="True",
    )
    # Need to confirm model name and how to call this.
    state_manager.set_transition(
        model_name="redshift-data::statement",
        transition={"progression": "time", "seconds": 4},
    )

    from RPA.Cloud.AWS import AWS

    aws = AWS()
    aws.init_redshift_data_client(
        cluster_identifier=TEST_CLUSTER,
        database="dev",
        database_user=TEST_USER,
    )
    # data = boto3.client("redshift-data", region_name=DEFAULT_REGION)
    # test_resp = data.execute_statement(
    #     Sql=SELECT_ALL_TABLES_SQL,
    #     ClusterIdentifier=TEST_CLUSTER,
    #     DbUser=TEST_USER,
    #     Database="dev",
    # )
    # print("\n\nRESPONSE:")
    # print(test_resp)

    # test_descrip = data.describe_statement(
    #     Id=test_resp["Id"],
    # )
    # print("\n\nDESCRIPTION 1:")
    # print(test_descrip)
    # test_descrip = data.describe_statement(
    #     Id=test_resp["Id"],
    # )
    # print("\n\nDESCRIPTION 2:")
    # print(test_descrip["Status"])
    # test_descrip = data.describe_statement(
    #     Id=test_resp["Id"],
    # )
    # print("\n\nDESCRIPTION 3:")
    # print(test_descrip["Status"])
    # test_descrip = data.describe_statement(
    #     Id=test_resp["Id"],
    # )
    # print("\n\nDESCRIPTION 4:")
    # print(test_descrip["Status"])
    # sleep(5)
    # test_descrip = data.describe_statement(
    #     Id=test_resp["Id"],
    # )
    # print("\n\nDESCRIPTION 5:")
    # print(test_descrip["Status"])

    # test_results = data.get_statement_result(Id=test_resp["Id"])
    # print("\n\nRESULTS:")
    # print(test_results)

    tables = aws.execute_redshift_statement(TEST_SQL)
    print("RETURNED TABLE:")
    print(tables)
    assert tables[0]["City"] == "Vancouver"

    # response = aws.execute_redshift_statement(
    #     INSERT_SQL,
    #     aws.create_redshift_statement_parameters(id="123", name="TestName"),
    # )
    # assert response == 1
