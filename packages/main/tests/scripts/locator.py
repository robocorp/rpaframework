import re
import sys

WINDOWS_LOCATOR_STRATEGIES = {
    "name": "name",
    "class_name": "class_name",
    "class": "class_name",
    "control_type": "control_type",
    "type": "control_type",
    "automation_id": "automation_id",
    "id": "automation_id",
    "partial name": "partial name",
    "regexp": "regexp",
}
locator = " ".join(sys.argv[1:])
regex = rf"({':|'.join(WINDOWS_LOCATOR_STRATEGIES.keys())})(\S+)|(and|or)"
parts = re.finditer(regex, locator, re.IGNORECASE)

locators = []
match_type = "all"

for part in parts:
    match = part.group()
    if match.lower() == "or":
        match_type = "any"
    elif match.lower() == "and":
        pass
    else:
        strategy, value = match.split(":")
        locators.append([WINDOWS_LOCATOR_STRATEGIES[strategy], value])

if not locators:
    print("Did not find any locators")
else:
    print(f"Got match_type={match_type}, locators={locators}")
