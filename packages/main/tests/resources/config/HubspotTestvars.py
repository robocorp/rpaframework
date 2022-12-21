import os


# Token for access.
ACCESS_TOKEN = os.getenv("HUBSPOT_TOKEN", "not-set")

# Contact/object lookup tests.
FIRST_NAME = "Cosmin"
LAST_NAME = "Poieană"
FIRST_NAME_2 = "Cosmin"
CONTACT_EMAILS = ["cosmin@robocorp.com", "cmin764@gmail.com"]
CONTACT_ID = "7397"

# Get One Object test
OBJECT_ID = 7397
COMPANY_ID = 7946543029

# Batch tests
OBJECT_IDS = [7397, 10559]
EXPECTED_ASSOCIATION_MAP = {"7397": "7946543029", "10559": "7946467247"}
EXPECTED_EMAILS = ["cosmin@robocorp.com", "cmin764@gmail.com"]

# Get Custom Object with Custom ID property test
CUSTOM_OBJ_ID = "a736d282-8ef6-4af3-9c10-996c827a78f4"
ID_PROPERTY = "organization_id"
CUSTOM_OBJECT_TYPE = "Organization"

# Pipeline tests.
PIPELINE_LABEL = "Self-Service Pipeline"
EXPECTED_STAGE_ORDER = (
    "Starter",
    "Flex",
    "Pro",
    "Closed lost",
)
TEST_DEAL = 8262422658
EXPECTED_STAGE = "Contract Signed - Active"

# User provisioning tests.
USER_ID = "27198978"
USER_EMAIL = "cosmin@robocorp.com"

# Owner lookup tests.
OWNER_ID = "129210975"
OWNER_EMAIL = "chris@robocorp.com"
COMPANY_ID_WITH_OWNER = "9848040731"
EXPECTED_COMPANY_OWNER = "149929641"

CUSTOM_OWNER_PROPERTY = "customer_success_contact"
COMPANY_ID_WITH_CUSTOM_OWNER = "7946565950"
EXPECTED_CUSTOM_OWNER = "149929641"
